import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('validation', Path(__file__).resolve().parents[1] / 'scripts/validate-research-data.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)

def records():
    return [dict(id=f'{split}-{label}', candidateSplit=split, reviewedLabel=label,
                 reviewedSourceGroup=f'{split}-{label}', reviewer='Example reviewer',
                 reviewedAt='2026-09-19', pixelSha256=f'{split}-{label}')
            for split in ('train', 'val', 'test') for label in ('Grade A', 'Grade B', 'Grade C', 'Reject')]

class ValidationTests(unittest.TestCase):
    def test_complete_review_metadata(self):
        self.assertEqual(validation.validate(records(), 'manuscript-quality', check_files=False), [])

    def test_source_labels_cannot_substitute_for_grades(self):
        rows = records()
        rows[0]['reviewedLabel'] = 'Fresh Dragon Fruit'
        self.assertTrue(any('incompatible' in e for e in validation.validate(rows, 'manuscript-quality', check_files=False)))

    def test_related_images_cannot_cross_splits(self):
        rows = records()
        rows[4]['reviewedSourceGroup'] = rows[0]['reviewedSourceGroup']
        self.assertTrue(any('crosses splits' in e for e in validation.validate(rows, 'manuscript-quality', check_files=False)))

    def test_no_review_is_not_ready(self):
        rows = records()
        rows[0]['reviewer'] = None
        self.assertTrue(any('review evidence' in e for e in validation.validate(rows, 'manuscript-quality', check_files=False)))

    def test_quality_crops_of_same_source_cannot_cross_splits(self):
        rows = records()
        rows[0]['roiSourceId'] = 'source-photo'
        rows[4]['roiSourceId'] = ' source-photo '
        self.assertTrue(any('ROI source' in e and 'crosses splits' in e
                            for e in validation.validate(rows, 'manuscript-quality', check_files=False)))

if __name__ == '__main__':
    unittest.main()
