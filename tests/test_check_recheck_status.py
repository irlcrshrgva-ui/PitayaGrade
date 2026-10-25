import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_recheck_status import inspect_exports


def row(ident, reviewer='AI-assisted-recheck-01'):
    return {
        'id': ident, 'task': 'quality', 'image': f'prepared/{ident}.jpg',
        'candidateSplit': 'train', 'sourceDataset': 'sample', 'sourceLabel': 'Fresh',
        'fileSha256': ident * 4, 'pixelSha256': ident * 4,
        'reviewedLabel': 'Grade A', 'reviewedSourceGroup': f'fruit-{ident}',
        'reviewer': reviewer, 'reviewedAt': '2026-10-25T10:00:00+08:00',
    }


class RecheckStatusTests(unittest.TestCase):
    def setUp(self):
        self.base = [row('a'), row('b')]
        self.index = {'assignments': [
            {'reviewerId': 'recheck-01', 'recordIds': ['a']},
            {'reviewerId': 'recheck-02', 'recordIds': ['b']},
        ]}
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, rows):
        path = self.root / name
        path.write_text(json.dumps(rows), encoding='utf-8')
        return path

    def test_reports_complete_only_for_exact_human_exports(self):
        one = self.write('one.json', [row('a', 'recheck-01')])
        two = self.write('two.json', [row('b', 'recheck-02')])
        result = inspect_exports(self.base, self.index, [one, two])
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['percentComplete'], 100.0)
        self.assertTrue(all(item['complete'] for item in result['assignments']))

    def test_assisted_attribution_is_not_counted_as_human_review(self):
        one = self.write('one.json', [row('a')])
        result = inspect_exports(self.base, self.index, [one])
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['validHumanReviews'], 0)
        self.assertIn('reviewer must be recheck-01', result['assignments'][0]['errors'][0])
        self.assertIsNone(result['assignments'][1]['file'])
        self.assertIn('no export supplied', result['assignments'][1]['errors'])

    def test_partial_export_shows_exact_remaining_count(self):
        self.index['assignments'][0]['recordIds'] = ['a', 'b']
        self.index['assignments'] = self.index['assignments'][:1]
        one = self.write('one.json', [row('a', 'recheck-01')])
        result = inspect_exports(self.base, self.index, [one])
        self.assertEqual(result['validHumanReviews'], 1)
        self.assertEqual(result['remaining'], 1)
        self.assertIn('1 assigned records are missing', result['assignments'][0]['errors'])


if __name__ == '__main__':
    unittest.main()
