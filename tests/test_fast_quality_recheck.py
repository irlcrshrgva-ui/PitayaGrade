import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

import numpy as np

from scripts.create_fast_quality_recheck import priority_score, select_groups
from scripts.finalize_fast_quality_rechecks import load_assignment, row_map


class FastQualityRecheckTests(unittest.TestCase):
    def test_disagreement_has_higher_priority_than_confident_agreement(self):
        agreement = np.asarray([[0.9, 0.05, 0.03, 0.02]] * 3)
        disagreement = np.asarray([
            [0.8, 0.1, 0.05, 0.05],
            [0.1, 0.8, 0.05, 0.05],
            [0.1, 0.1, 0.75, 0.05],
        ])
        low, _, _ = priority_score(0, agreement)
        high, _, _ = priority_score(0, disagreement)
        self.assertGreater(high, low)

    def test_selection_keeps_source_groups_together(self):
        candidates = [
            {"priority": 0.9, "row": {"id": "quality:1", "task": "quality", "reviewedSourceGroup": "fruit-a"}},
            {"priority": 0.8, "row": {"id": "quality:2", "task": "quality", "reviewedSourceGroup": "fruit-a"}},
            {"priority": 0.7, "row": {"id": "quality:3", "task": "quality", "reviewedSourceGroup": "fruit-b"}},
        ]
        selected = select_groups(candidates, 1)
        self.assertEqual({item["row"]["id"] for item in selected[0]}, {"quality:1", "quality:2"})

    def test_completed_rows_require_unique_ids(self):
        with self.assertRaisesRegex(ValueError, 'duplicate id'):
            row_map([{'id': 'quality:1'}, {'id': 'quality:1'}], 'completed')

    def test_assignment_audit_forbids_test_records(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'assignment.zip'
            stream = io.StringIO(newline='')
            writer = csv.DictWriter(stream, fieldnames=['id'])
            writer.writeheader()
            writer.writerow({'id': 'quality:1'})
            audit = {'reviewerId': 'reviewer-01', 'recordCount': 1, 'testRecordsIncluded': 1}
            with zipfile.ZipFile(archive, 'w') as bundle:
                bundle.writestr('audit.json', json.dumps(audit))
                bundle.writestr('review.csv', stream.getvalue().encode('utf-8-sig'))
            with self.assertRaisesRegex(ValueError, 'invalid assignment audit'):
                load_assignment(archive)


if __name__ == "__main__":
    unittest.main()
