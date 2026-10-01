import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from scripts.reviewed_training import read_reviewed_manifest, prepare_reviewed_dataset

ROOT = Path(__file__).resolve().parents[1]


class ReviewedTrainingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for split in ('train', 'val', 'test'):
            for label in ('Grade A', 'Grade B', 'Grade C', 'Reject'):
                index = len(self.rows)
                file = self.root / f'{index}.png'
                image = Image.new('RGB', (3, 3), (index, 20, 30))
                image.save(file)
                self.rows.append(dict(id=str(index), image=file.name, candidateSplit=split,
                                      reviewedLabel=label, reviewedSourceGroup=str(index),
                                      reviewer='Synthetic test fixture', reviewedAt='2026-09-20',
                                      fileSha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                                      pixelSha256=hashlib.sha256(image.tobytes()).hexdigest()))
        self.manifest = self.root / 'manifest.json'

    def read(self):
        self.manifest.write_text(json.dumps(self.rows), encoding='utf-8')
        return read_reviewed_manifest(self.manifest, self.root)

    def test_preserves_labels_splits_and_bytes(self):
        prepared = prepare_reviewed_dataset(self.read(), self.root / 'run', self.root)
        for row in self.rows:
            files = list((prepared / row['candidateSplit'] / row['reviewedLabel']).iterdir())
            self.assertEqual(len(files), 1)
            self.assertEqual(hashlib.sha256(files[0].read_bytes()).hexdigest(), row['fileSha256'])

    def test_refuses_reusing_run(self):
        run = self.root / 'run'
        run.mkdir()
        marker = run / 'previous-result'
        marker.write_text('preserve')
        with self.assertRaises(FileExistsError):
            prepare_reviewed_dataset(self.read(), run, self.root)
        self.assertEqual(marker.read_text(), 'preserve')

    def test_unreviewed_labels_block_preparation(self):
        self.rows[0]['reviewedLabel'] = 'Ripe_frames'
        with self.assertRaisesRegex(ValueError, 'incompatible'):
            self.read()

    def test_pixel_hash_is_verified(self):
        self.rows[0]['pixelSha256'] = 'fabricated'
        with self.assertRaisesRegex(ValueError, 'pixel checksum'):
            self.read()

    def test_changed_image_is_rejected(self):
        (self.root / self.rows[0]['image']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'image checksum'):
            self.read()

    def test_cross_split_duplicate_is_rejected(self):
        for key in ('image', 'fileSha256', 'pixelSha256'):
            self.rows[4][key] = self.rows[0][key]
        with self.assertRaisesRegex(ValueError, 'crosses splits'):
            self.read()

    def test_blank_reviewer_rejected(self):
        self.rows[0]['reviewer'] = '   '
        with self.assertRaisesRegex(ValueError, 'review evidence'):
            self.read()

    def test_cli_requires_manifest_before_framework_import(self):
        result = subprocess.run([sys.executable, str(ROOT / 'train_models.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--manifest', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)


if __name__ == '__main__':
    unittest.main()
