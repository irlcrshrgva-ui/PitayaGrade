import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.stage_quality_week4_evidence import stage_quality_evidence


class StageQualityWeek4EvidenceTests(unittest.TestCase):
    def test_staged_package_is_complete_for_quality_but_not_release(self):
        root = Path(__file__).resolve().parents[1]
        build_root = root / ".codex-build"
        build_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=build_root) as temporary:
            output = Path(temporary) / "quality-evidence"
            audit = stage_quality_evidence(root, output)

            self.assertEqual(audit["status"], "quality-only-verified-release-incomplete")
            self.assertFalse(audit["releaseReady"])
            self.assertEqual(len(audit["models"]), 3)
            self.assertEqual(audit["testSampleCountPerModel"], 226)
            self.assertFalse((output / "device-test.csv").exists())
            self.assertFalse((output / "uat.csv").exists())
            self.assertFalse((output / "evidence-audit.json").exists())

            with (output / "model-evaluation.csv").open(newline="", encoding="utf-8") as handle:
                evaluations = list(csv.DictReader(handle))
            self.assertEqual({row["model_id"] for row in evaluations}, {
                "mobilenetv2-quality", "resnet50-quality", "efficientnet-b3-quality"
            })
            self.assertTrue(all(row["test_sample_count"] == "226" for row in evaluations))

            with (output / "predictions.csv").open(newline="", encoding="utf-8") as handle:
                predictions = list(csv.DictReader(handle))
            self.assertEqual(len(predictions), 3 * 226)

            saved_audit = json.loads((output / "quality-evidence-audit.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_audit["models"], audit["models"])


if __name__ == "__main__":
    unittest.main()
