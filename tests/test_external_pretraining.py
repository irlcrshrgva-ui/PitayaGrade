import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.external_pretraining import read_external_pretraining_audit


class ExternalPretrainingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frozen = self.root / "frozen.json"
        self.frozen.write_text("[]", encoding="utf-8")
        self.archive = self.root / "source.zip"
        self.archive.write_bytes(b"source archive")
        records = []
        for split in ("train", "test"):
            for label in ("good", "medium"):
                path = self.root / f"{split}-{label}.png"
                Image.new("RGB", (4, 4), (len(records) * 30, 20, 10)).save(path)
                records.append({
                    "sourceSplit": split,
                    "sourceLabel": label,
                    "path": path.relative_to(self.root).as_posix(),
                    "fileSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "pixelSha256": f"pixel-{len(records)}",
                })
        self.audit = {
            "purpose": "external feature pretraining only; not official grade ground truth",
            "frozenManifest": self.frozen.relative_to(self.root).as_posix(),
            "source": {
                "archive": self.archive.relative_to(self.root).as_posix(),
                "archiveSha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
            },
            "counts": {"safeIndependentRecords": len(records)},
            "safeRecords": records,
        }
        self.path = self.root / "audit.json"

    def read(self):
        self.path.write_text(json.dumps(self.audit), encoding="utf-8")
        return read_external_pretraining_audit(self.path, self.frozen, self.root)

    def test_accepts_two_label_leakage_safe_evidence(self):
        data = self.read()
        self.assertEqual(data["validatedCounts"], {
            "test/good": 1,
            "test/medium": 1,
            "train/good": 1,
            "train/medium": 1,
        })

    def test_rejects_grade_mapping_or_bad_label(self):
        self.audit["safeRecords"][0]["sourceLabel"] = "bad"
        with self.assertRaisesRegex(ValueError, "good/medium"):
            self.read()

    def test_rejects_different_frozen_manifest(self):
        other = self.root / "other.json"
        other.write_text("[]", encoding="utf-8")
        self.path.write_text(json.dumps(self.audit), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "frozen manifest"):
            read_external_pretraining_audit(self.path, other, self.root)

    def test_rejects_changed_external_image(self):
        Path(self.root / self.audit["safeRecords"][0]["path"]).write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            self.read()

    def test_rejects_duplicate_pixels(self):
        self.audit["safeRecords"][1]["pixelSha256"] = self.audit["safeRecords"][0]["pixelSha256"]
        with self.assertRaisesRegex(ValueError, "exact duplicate"):
            self.read()


if __name__ == "__main__":
    unittest.main()
