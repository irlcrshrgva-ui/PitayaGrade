import csv
import tempfile
import unittest
from pathlib import Path

from scripts.review_manifest import export_reviews, merge_reviews, parse_reviews


MANIFEST = [
    {'id': 'one', 'task': 'quality', 'image': 'one.jpg', 'candidateSplit': 'train',
     'sourceDataset': 'source', 'sourceLabel': 'Fresh', 'reviewedLabel': None,
     'reviewedSourceGroup': None, 'reviewer': None, 'reviewedAt': None},
    {'id': 'two', 'task': 'disease', 'image': 'two.jpg', 'candidateSplit': 'test',
     'sourceDataset': 'source', 'sourceLabel': 'Defect', 'reviewedLabel': None,
     'reviewedSourceGroup': None, 'reviewer': None, 'reviewedAt': None},
]


class ReviewManifestTests(unittest.TestCase):
    def test_export_filters_task_and_preserves_review_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'quality.csv'
            self.assertEqual(export_reviews(MANIFEST, output, 'quality'), 1)
            with output.open(encoding='utf-8-sig', newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]['id'], 'one')
            self.assertIn('reviewedSourceGroup', rows[0])

    def test_complete_review_merges_without_mutating_source(self):
        reviews = {'one': {'reviewedLabel': 'Grade A', 'reviewedSourceGroup': 'fruit-1',
                           'reviewer': 'reviewer-1', 'reviewedAt': '2026-10-04T10:00:00+08:00'}}
        merged, count = merge_reviews(MANIFEST, reviews)
        self.assertEqual(count, 1)
        self.assertEqual(merged[0]['reviewedLabel'], 'Grade A')
        self.assertIsNone(MANIFEST[0]['reviewedLabel'])

    def test_partial_invalid_and_overwriting_reviews_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reviews.csv'
            path.write_text('id,reviewedLabel,reviewedSourceGroup,reviewer,reviewedAt\n'
                            'one,Grade A,,,\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'all filled or all blank'):
                parse_reviews(path, {'Grade A'})
        existing = [dict(MANIFEST[0], reviewedLabel='Grade B', reviewedSourceGroup='fruit-1',
                         reviewer='reviewer-1', reviewedAt='2026-10-04T10:00:00+08:00')]
        replacement = {'one': {'reviewedLabel': 'Grade A', 'reviewedSourceGroup': 'fruit-1',
                               'reviewer': 'reviewer-1', 'reviewedAt': '2026-10-04T10:00:00+08:00'}}
        with self.assertRaisesRegex(ValueError, 'refusing to overwrite'):
            merge_reviews(existing, replacement)

    def test_unknown_ids_fail_closed(self):
        review = {'missing': {'reviewedLabel': 'Grade A', 'reviewedSourceGroup': 'fruit-1',
                              'reviewer': 'reviewer-1', 'reviewedAt': '2026-10-04T10:00:00+08:00'}}
        with self.assertRaisesRegex(ValueError, 'unknown IDs'):
            merge_reviews(MANIFEST, review)


if __name__ == '__main__':
    unittest.main()

