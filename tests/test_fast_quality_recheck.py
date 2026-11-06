import unittest

import numpy as np

from scripts.create_fast_quality_recheck import priority_score, select_groups


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


if __name__ == "__main__":
    unittest.main()
