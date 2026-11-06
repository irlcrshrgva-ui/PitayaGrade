import unittest

import numpy as np

from scripts.ensemble_quality_probe import metrics, weight_grid


class QualityEnsembleProbeTests(unittest.TestCase):
    def test_weight_grid_is_convex_and_complete_for_two_models(self):
        weights = list(weight_grid(2, 4))
        self.assertEqual(len(weights), 5)
        self.assertTrue(all(np.isclose(item.sum(), 1.0) for item in weights))
        self.assertTrue(all((item >= 0).all() for item in weights))

    def test_metrics_returns_accuracy_macro_f1_and_confusion(self):
        result = metrics([0, 1, 2, 3], [0, 1, 1, 3])
        self.assertEqual(result["correct"], 3)
        self.assertEqual(result["count"], 4)
        self.assertAlmostEqual(result["accuracy"], 0.75)
        self.assertEqual(result["confusionMatrix"][2][1], 1)
        self.assertGreater(result["macroF1"], 0)
        self.assertLess(result["macroF1"], 1)


if __name__ == "__main__":
    unittest.main()
