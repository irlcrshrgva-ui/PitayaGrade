import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from scripts.reviewed_training import (read_reviewed_manifest, prepare_reviewed_dataset,
                                       prepared_sample_ids, write_prediction_csv)

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
                self.rows.append(dict(id=str(index), task='quality', image=file.name, candidateSplit=split,
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

    def test_maturity_rows_are_excluded_from_quality_training(self):
        maturity = dict(self.rows[0], id='maturity-row', task='maturity',
                        reviewedLabel='Mature Dragon Fruit', reviewedSourceGroup='maturity-fruit')
        self.rows.append(maturity)
        loaded = self.read()
        self.assertEqual(len(loaded), len(self.rows) - 1)
        self.assertTrue(all(row['task'] == 'quality' for row in loaded))

    def test_cli_requires_manifest_before_framework_import(self):
        result = subprocess.run([sys.executable, str(ROOT / 'train_models.py')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--manifest', result.stderr)
        self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_prepared_samples_recover_frozen_manifest_ids(self):
        prepared = prepare_reviewed_dataset(self.read(), self.root / 'run', self.root)
        samples = sorted((path, 0) for path in (prepared / 'test').glob('*/*'))
        expected = sorted(row['id'] for row in self.rows if row['candidateSplit'] == 'test')
        self.assertEqual(sorted(prepared_sample_ids(self.rows, samples)), expected)
        with self.assertRaisesRegex(ValueError, 'no reviewed-manifest identity'):
            prepared_sample_ids(self.rows, samples + [(prepared / 'test' / 'unknown.jpg', 0)])

    def test_prediction_csv_is_complete_and_traceable(self):
        output = self.root / 'predictions.csv'
        write_prediction_csv(output, 'mobilenetv2-quality', ['one', 'two'],
                             ['Grade A', 'Reject'], [.8, .9], [4.5, 5.5])
        text = output.read_text(encoding='utf-8')
        self.assertIn('model_id,sample_id,predicted_label,confidence,inference_ms', text)
        self.assertIn('mobilenetv2-quality,one,Grade A,0.8000000000,4.500000', text)
        with self.assertRaisesRegex(ValueError, 'one complete row'):
            write_prediction_csv(self.root / 'bad.csv', 'model', ['one'], [], [], [])


if __name__ == '__main__':
    unittest.main()
