import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image
from scripts.reviewed_detection import prepare_detection_dataset, read_detection_manifest, validate_detection
from train_yolo import train_detector

ROOT = Path(__file__).resolve().parents[1]


class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for index, split in enumerate(('train', 'val', 'test')):
            file = self.root / f'{index}.png'
            image = Image.new('RGB', (12, 12), (index, 20, 30))
            image.save(file)
            self.rows.append(dict(id=str(index), image=file.name, candidateSplit=split,
                                  reviewedLabel='Dragon Fruit', reviewedSourceGroup=str(index),
                                  reviewer='Synthetic fixture', reviewedAt='2026-09-20',
                                  annotationReviewer='Synthetic fixture', annotationReviewedAt='2026-09-20',
                                  boundingBoxes=[[0.3, 0.4, 0.2, 0.4], [0.8, 0.7, 0.2, 0.2]],
                                  fileSha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                                  pixelSha256=hashlib.sha256(image.tobytes()).hexdigest()))

    def test_export_preserves_real_boxes_and_partitions(self):
        config = prepare_detection_dataset(self.rows, self.root / 'run', self.root)
        self.assertIn('0: Dragon Fruit', config.read_text())
        for row in self.rows:
            labels = list((config.parent / 'labels' / row['candidateSplit']).glob('*.txt'))
            self.assertEqual(len(labels), 1)
            actual = [[float(n) for n in line.split()] for line in labels[0].read_text().splitlines()]
            self.assertEqual(actual, [[0] + box for box in row['boundingBoxes']])
            images = list((config.parent / 'images' / row['candidateSplit']).iterdir())
            self.assertEqual(hashlib.sha256(images[0].read_bytes()).hexdigest(), row['fileSha256'])
        snapshot = json.loads((config.parent.parent / 'reviewed-manifest.json').read_text())
        self.assertEqual(snapshot, self.rows)

    def test_missing_annotations_fail_before_output(self):
        self.rows[0].pop('boundingBoxes')
        with self.assertRaisesRegex(ValueError, 'no boxes are inferred'):
            prepare_detection_dataset(self.rows, self.root / 'run', self.root)
        self.assertFalse((self.root / 'run').exists())

    def test_rejects_invalid_geometry(self):
        for box in ([0.5, 0.5, 0, 0.2], [0.1, 0.5, 0.8, 0.4],
                    [float('nan'), 0.5, 0.2, 0.2], [True, 0.5, 0.2, 0.2],
                    [0.5, 0.5, 0.2], ['0.5', 0.5, 0.2, 0.2]):
            with self.subTest(box=box):
                rows = copy.deepcopy(self.rows)
                rows[0]['boundingBoxes'] = [box]
                self.assertTrue(validate_detection(rows, self.root, check_files=False))

    def test_requires_annotation_review_separately(self):
        self.rows[0]['annotationReviewer'] = ' '
        self.assertTrue(any('bounding-box review' in e for e in validate_detection(self.rows, self.root)))

    def test_rejects_grade_labels_for_detector(self):
        self.rows[0]['reviewedLabel'] = 'Grade A'
        self.assertTrue(any('incompatible' in e for e in validate_detection(self.rows, self.root)))

    def test_rejects_related_images_across_splits(self):
        self.rows[1]['reviewedSourceGroup'] = self.rows[0]['reviewedSourceGroup']
        self.assertTrue(any('crosses splits' in e for e in validate_detection(self.rows, self.root)))

    def test_refuses_existing_output(self):
        output = self.root / 'existing'
        output.mkdir()
        with self.assertRaises(FileExistsError):
            prepare_detection_dataset(self.rows, output, self.root)

    def test_cli_blocks_unreviewed_data_before_imports(self):
        manifest = self.root / 'unreviewed.json'
        manifest.write_text(json.dumps([{'id': 'unreviewed'}]))
        for script in ('train_yolo.py', 'PitayaGrade_Colab_Training.py'):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, str(ROOT / script), '--manifest', str(manifest),
                                         '--run-dir', str(self.root / 'run')], text=True, capture_output=True)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('not training-ready', result.stderr)
                self.assertNotIn('ModuleNotFoundError', result.stderr)
                self.assertFalse((self.root / 'run').exists())

    def test_detector_evaluates_only_after_both_training_phases(self):
        calls = []
        run = self.root / 'run'

        class FakeYolo:
            def __init__(self, checkpoint):
                calls.append(('load', checkpoint))

            def train(self, **kwargs):
                calls.append(('train', kwargs))
                best = Path(kwargs['project']) / kwargs['name'] / 'weights' / 'best.pt'
                best.parent.mkdir(parents=True)
                best.write_bytes(b'synthetic checkpoint')
                (best.parent.parent / 'results.csv').write_text('epoch,val/total_loss\n1,2\n')

            def val(self, **kwargs):
                calls.append(('val', kwargs))
                return SimpleNamespace(results_dict={'synthetic_test_metric': 0})

        best = train_detector(self.root / 'data.yaml', run, FakeYolo, 'cpu', 'test-trainer')
        self.assertTrue(best.is_file())
        self.assertEqual([name for name, _ in calls], ['load', 'train', 'load', 'train', 'load', 'val'])
        self.assertEqual(calls[1][1]['freeze'], 10)
        self.assertEqual(calls[3][1]['lr0'], 1e-5)
        self.assertEqual(calls[-1][1]['split'], 'test')
        self.assertFalse(calls[1][1]['exist_ok'])
        self.assertEqual(calls[1][1]['trainer'], 'test-trainer')
        self.assertEqual(calls[3][1]['trainer'], 'test-trainer')

    def test_missing_checkpoint_stops_before_test_evaluation(self):
        class NoCheckpoint:
            def __init__(self, checkpoint):
                pass

            def train(self, **kwargs):
                pass

        with self.assertRaisesRegex(RuntimeError, 'Phase 1'):
            train_detector(self.root / 'data.yaml', self.root / 'run', NoCheckpoint, 'cpu', 'test-trainer')


if __name__ == '__main__':
    unittest.main()
