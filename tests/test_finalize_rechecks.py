import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from scripts.finalize_rechecks import apply_adjudications, apply_rechecks, finalize


class FinalizeRechecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        index = 0
        for task, labels in (('quality', ['Grade A', 'Grade B', 'Grade C', 'Reject']),
                             ('maturity', ['Mature Dragon Fruit', 'Immature Dragon Fruit'])):
            for split in ('train', 'val', 'test'):
                for label in labels:
                    file = self.root / f'{index}.png'
                    image = Image.new('RGB', (3, 3), (index, 20, 30))
                    image.save(file)
                    reviewer = 'AI-assisted-reviewer-01' if index in (0, 12) else 'reviewer-02'
                    self.rows.append({
                        'id': f'row-{index}', 'task': task, 'image': file.name,
                        'candidateSplit': split, 'sourceDataset': 'fixture', 'sourceLabel': label,
                        'fileSha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                        'pixelSha256': hashlib.sha256(image.tobytes()).hexdigest(),
                        'reviewedLabel': label, 'reviewedSourceGroup': f'fruit-{index}',
                        'reviewer': reviewer, 'reviewedAt': '2026-10-24T10:00:00+08:00'})
                    index += 1
        self.assignments = {'schemaVersion': 1, 'assignments': [
            {'reviewerId': 'recheck-01', 'recordIds': ['row-0']},
            {'reviewerId': 'recheck-02', 'recordIds': ['row-12']},
        ]}

    def export(self, ident, reviewer):
        row = next(dict(item) for item in self.rows if item['id'] == ident)
        row['reviewer'] = reviewer
        row['reviewedAt'] = '2026-10-25T10:00:00+08:00'
        return row

    def test_applies_only_assigned_human_patches(self):
        result = apply_rechecks(self.rows, self.assignments, [
            ('one.json', [self.export('row-0', 'recheck-01')]),
            ('two.json', [self.export('row-12', 'recheck-02')]),
        ])
        self.assertFalse(any(row['reviewer'].startswith('AI-assisted-') for row in result))
        self.assertEqual(next(row for row in result if row['id'] == 'row-1')['reviewer'], 'reviewer-02')

    def test_rejects_missing_wrong_or_modified_exports(self):
        with self.assertRaisesRegex(ValueError, 'Missing completed'):
            apply_rechecks(self.rows, self.assignments,
                           [('one.json', [self.export('row-0', 'recheck-01')])])
        wrong = self.export('row-0', 'wrong-reviewer')
        with self.assertRaisesRegex(ValueError, 'must be saved'):
            apply_rechecks(self.rows, self.assignments, [('one.json', [wrong]),
                ('two.json', [self.export('row-12', 'recheck-02')])])
        changed = self.export('row-0', 'recheck-01')
        changed['image'] = 'changed.png'
        with self.assertRaisesRegex(ValueError, 'protected field'):
            apply_rechecks(self.rows, self.assignments, [('one.json', [changed]),
                ('two.json', [self.export('row-12', 'recheck-02')])])

    def test_adjudication_resolves_only_real_conflicts_with_human_evidence(self):
        rows = [dict(self.rows[0]), dict(self.rows[1])]
        rows[1]['reviewedSourceGroup'] = rows[0]['reviewedSourceGroup']
        rows[1]['reviewedLabel'] = 'Grade B'
        document = {'schemaVersion': 1, 'decisions': [{
            'task': 'quality', 'reviewedSourceGroup': rows[0]['reviewedSourceGroup'],
            'reviewedLabel': 'Grade B', 'adjudicator': 'coordinator-01',
            'adjudicatedAt': '2026-10-27T09:00:00+08:00', 'rationale': 'Visual recheck',
        }]}
        result, audit = apply_adjudications(rows, document)
        self.assertEqual({row['reviewedLabel'] for row in result}, {'Grade B'})
        self.assertEqual({row['reviewer'] for row in result}, {'coordinator-01'})
        self.assertEqual(audit[0]['previousLabels'], ['Grade A', 'Grade B'])
        document['decisions'][0]['adjudicator'] = 'AI-assisted-coordinator'
        with self.assertRaisesRegex(ValueError, 'genuine human'):
            apply_adjudications(rows, document)

    def test_adjudication_requires_every_and_only_conflicting_group(self):
        rows = [dict(self.rows[0]), dict(self.rows[1])]
        rows[1]['reviewedSourceGroup'] = rows[0]['reviewedSourceGroup']
        rows[1]['reviewedLabel'] = 'Grade B'
        with self.assertRaisesRegex(ValueError, 'Missing adjudication'):
            apply_adjudications(rows, {'schemaVersion': 1, 'decisions': []})
        clean = [dict(self.rows[0])]
        with self.assertRaisesRegex(ValueError, 'non-conflicting'):
            apply_adjudications(clean, {'schemaVersion': 1, 'decisions': [{
                'task': 'quality', 'reviewedSourceGroup': clean[0]['reviewedSourceGroup'],
                'reviewedLabel': 'Grade A', 'adjudicator': 'coordinator-01',
                'adjudicatedAt': '2026-10-27T09:00:00+08:00',
            }]})

    def test_finalizer_writes_validated_frozen_evidence(self):
        base = self.root / 'base.json'
        assignments = self.root / 'assignments.json'
        one, two = self.root / 'one.json', self.root / 'two.json'
        base.write_text(json.dumps(self.rows), encoding='utf-8')
        assignments.write_text(json.dumps(self.assignments), encoding='utf-8')
        one.write_text(json.dumps([self.export('row-0', 'recheck-01')]), encoding='utf-8')
        two.write_text(json.dumps([self.export('row-12', 'recheck-02')]), encoding='utf-8')
        audit = finalize(base, assignments, [one, two], self.root / 'final', self.root)
        self.assertEqual(audit['status'], 'human-reviewed-and-validated')
        self.assertEqual(audit['validationErrors'], 0)
        self.assertTrue((self.root / 'final/frozen-training-manifest.json').is_file())
        self.assertTrue((self.root / 'final/frozen-quality-manifest.json').is_file())
        self.assertTrue((self.root / 'final/frozen-maturity-manifest.json').is_file())
        self.assertRegex(audit['frozenQualityManifestSha256'], r'^[0-9a-f]{64}$')


if __name__ == '__main__':
    unittest.main()
