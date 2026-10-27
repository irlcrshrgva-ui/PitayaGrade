import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.finalize_disease_annotations import apply_annotations, finalize
from scripts.reviewed_segmentation import SYMPTOMS


class FinalizeDiseaseAnnotationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        index = 0
        labels = [*SYMPTOMS, 'Healthy']
        for split in ('train', 'val', 'test'):
            for label in labels:
                for _ in range(2):
                    image = self.root / f'{index}.png'
                    value = index + 1
                    picture = Image.new('RGB', (8, 8), (value, 20, 30))
                    picture.save(image)
                    self.rows.append({
                        'id': f'crop-{index}', 'task': 'disease', 'image': image.name,
                        'candidateSplit': split, 'sourceDataset': 'fixture', 'sourceLabel': label,
                        'fileSha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                        'pixelSha256': hashlib.sha256(picture.tobytes()).hexdigest(),
                        'reviewedSourceGroup': f'fruit-{index}', 'imageRole': 'fruit-roi',
                        'roiSourceId': f'source-{index}', 'maskCoordinateSpace': 'upright',
                        'reviewedLabel': None, 'reviewer': None, 'reviewedAt': None,
                        'annotationsComplete': False, 'annotationReviewer': None,
                        'annotationReviewedAt': None, 'regions': None,
                        'cropReviewStatus': 'unverified-model-proposal', 'cropReviewer': None,
                        'cropReviewedAt': None, 'excludedFromTraining': False,
                        'exclusionReason': None,
                    })
                    index += 1
        midpoint = len(self.rows) // 2
        self.assignments = {'schemaVersion': 1, 'assignments': [
            {'reviewerId': 'mask-reviewer-01', 'recordIds': [row['id'] for row in self.rows[:midpoint]]},
            {'reviewerId': 'mask-reviewer-02', 'recordIds': [row['id'] for row in self.rows[midpoint:]]},
        ]}

    def export(self, rows, reviewer):
        values = []
        for original in rows:
            label = original['sourceLabel']
            regions = [] if label == 'Healthy' else [
                {'label': label, 'polygon': [[.1, .1], [.8, .1], [.4, .8]]}]
            values.append({**original, 'image': f'images/{original["candidateSplit"]}/{Path(original["image"]).name}',
                           'reviewedLabel': label, 'reviewer': reviewer,
                           'reviewedAt': '2026-10-25T10:00:00+08:00',
                           'annotationsComplete': True, 'annotationReviewer': reviewer,
                           'annotationReviewedAt': '2026-10-25T10:00:00+08:00', 'regions': regions,
                           'cropReviewStatus': 'human-confirmed', 'cropReviewer': reviewer,
                           'cropReviewedAt': '2026-10-25T10:00:00+08:00',
                           'excludedFromTraining': False, 'exclusionReason': None})
        return values

    def completed_exports(self):
        midpoint = len(self.rows) // 2
        return [('one.json', self.export(self.rows[:midpoint], 'mask-reviewer-01')),
                ('two.json', self.export(self.rows[midpoint:], 'mask-reviewer-02'))]

    def test_merges_exact_assignments_and_keeps_canonical_image_paths(self):
        result = apply_annotations(self.rows, self.assignments, self.completed_exports())
        self.assertTrue(all(row['annotationsComplete'] for row in result))
        self.assertEqual(result[0]['image'], self.rows[0]['image'])
        self.assertEqual(result[-1]['annotationReviewer'], 'mask-reviewer-02')

    def test_rejects_missing_wrong_or_modified_evidence(self):
        with self.assertRaisesRegex(ValueError, 'Missing completed'):
            apply_annotations(self.rows, self.assignments, self.completed_exports()[:1])
        exports = self.completed_exports()
        exports[0][1][0]['fileSha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'protected field'):
            apply_annotations(self.rows, self.assignments, exports)
        exports = self.completed_exports()
        exports[0][1][0]['annotationReviewer'] = 'someone-else'
        with self.assertRaisesRegex(ValueError, 'must be annotated'):
            apply_annotations(self.rows, self.assignments, exports)

    def test_finalizer_writes_validated_manifest_and_audit(self):
        base = self.root / 'base.json'
        assignments = self.root / 'assignments.json'
        one, two = self.root / 'one.json', self.root / 'two.json'
        base.write_text(json.dumps(self.rows), encoding='utf-8')
        assignments.write_text(json.dumps(self.assignments), encoding='utf-8')
        exports = self.completed_exports()
        one.write_text(json.dumps(exports[0][1]), encoding='utf-8')
        two.write_text(json.dumps(exports[1][1]), encoding='utf-8')
        audit = finalize(base, assignments, [one, two], self.root / 'final', self.root)
        self.assertEqual(audit['status'], 'human-annotated-and-validated')
        self.assertEqual(audit['rowCount'], len(self.rows))
        self.assertTrue((self.root / 'final/frozen-disease-annotation-manifest.json').is_file())

    def test_finalizer_records_and_removes_excluded_crop_proposals(self):
        base = self.root / 'base.json'
        assignments = self.root / 'assignments.json'
        one, two = self.root / 'one.json', self.root / 'two.json'
        base.write_text(json.dumps(self.rows), encoding='utf-8')
        assignments.write_text(json.dumps(self.assignments), encoding='utf-8')
        exports = self.completed_exports()
        excluded = exports[0][1][0]
        excluded.update({'reviewedLabel': 'Excluded', 'regions': [],
                         'cropReviewStatus': 'excluded', 'excludedFromTraining': True,
                         'exclusionReason': 'unusable-model-assisted-fruit-crop'})
        one.write_text(json.dumps(exports[0][1]), encoding='utf-8')
        two.write_text(json.dumps(exports[1][1]), encoding='utf-8')
        audit = finalize(base, assignments, [one, two], self.root / 'excluded-final', self.root)
        self.assertEqual(audit['assignedRowCount'], len(self.rows))
        self.assertEqual(audit['rowCount'], len(self.rows) - 1)
        self.assertEqual(audit['excludedCount'], 1)


if __name__ == '__main__':
    unittest.main()
