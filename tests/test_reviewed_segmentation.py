import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from scripts.reviewed_segmentation import SYMPTOMS, polygon_error, validate_segmentation, prepare_segmentation_dataset

ROOT = Path(__file__).resolve().parents[1]


class SegmentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for split in ('train', 'val', 'test'):
            for label in ('Healthy', *SYMPTOMS):
                index = len(self.rows)
                file = self.root / f'{index}.png'
                image = Image.new('RGB', (16, 12), (index, 20, 30))
                image.save(file)
                self.rows.append(dict(id=str(index), image=file.name, candidateSplit=split,
                                      reviewedLabel=label, reviewedSourceGroup=str(index),
                                      reviewer='Synthetic fixture', reviewedAt='2026-09-20',
                                      imageRole='fruit-roi', roiSourceId=f'synthetic-source-{index}',
                                      annotationsComplete=True, annotationReviewer='Synthetic fixture',
                                      annotationReviewedAt='2026-09-20', maskCoordinateSpace='upright',
                                      regions=[] if label == 'Healthy' else [{'label': label, 'polygon': [[.2, .2], [.6, .2], [.6, .7], [.2, .7]]}],
                                      fileSha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                                      pixelSha256=hashlib.sha256(image.tobytes()).hexdigest()))

    def test_exports_reviewed_regions_and_healthy_negative(self):
        config = prepare_segmentation_dataset(self.rows, self.root / 'run', self.root)
        self.assertIn('0: Anthracnose', config.read_text())
        self.assertNotIn('Healthy', config.read_text())
        for row in self.rows:
            stem = hashlib.sha256(row['id'].encode()).hexdigest()
            text = (config.parent / 'labels' / row['candidateSplit'] / (stem + '.txt')).read_text()
            if row['reviewedLabel'] == 'Healthy':
                self.assertEqual(text, '')
            else:
                values = [float(n) for n in text.split()]
                self.assertEqual(values[0], SYMPTOMS.index(row['reviewedLabel']))
                self.assertEqual(values[1:], [.2, .2, .6, .2, .6, .7, .2, .7])
            self.assertEqual(hashlib.sha256((self.root / row['image']).read_bytes()).hexdigest(), row['fileSha256'])

    def test_disease_label_cannot_substitute_for_a_mask(self):
        self.rows[1]['regions'] = []
        with self.assertRaisesRegex(ValueError, 'annotated region'):
            prepare_segmentation_dataset(self.rows, self.root / 'run', self.root)
        self.assertFalse((self.root / 'run').exists())

    def test_missing_review_or_crop_context_is_rejected(self):
        for key in ('annotationsComplete', 'annotationReviewer', 'roiSourceId', 'imageRole', 'maskCoordinateSpace'):
            with self.subTest(key=key):
                rows = copy.deepcopy(self.rows)
                rows[0].pop(key)
                self.assertTrue(validate_segmentation(rows, self.root, check_files=False))

    def test_healthy_cannot_have_a_symptom_mask(self):
        self.rows[0]['regions'] = copy.deepcopy(self.rows[1]['regions'])
        self.assertTrue(any('Healthy review conflicts' in e for e in validate_segmentation(self.rows, self.root)))

    def test_invalid_polygons_rejected(self):
        for points in ([], [[0, 0], [1, 1]], [[0, 0], [0, 0], [1, 1]],
                       [[0, 0], [.5, .5], [1, 1]], [[0, 0], [1, 1], [0, 1], [1, 0]],
                       [[0, 0], [2, 0], [1, 1]], [[float('nan'), 0], [1, 0], [1, 1]],
                       [[True, 0], [1, 0], [1, 1]]):
            with self.subTest(points=points):
                self.assertIsNotNone(polygon_error(points))

    def test_concave_polygon_is_preserved(self):
        self.assertIsNone(polygon_error([[0, 0], [1, 0], [.5, .5], [1, 1], [0, 1]]))

    def test_holes_and_unknown_labels_are_not_silently_dropped(self):
        self.rows[1]['regions'][0]['holes'] = [[[.3, .3], [.4, .3], [.3, .4]]]
        self.assertTrue(any('holes' in e for e in validate_segmentation(self.rows, self.root)))
        self.rows[1]['regions'][0]['label'] = 'Ripe'
        self.assertTrue(any('unsupported' in e for e in validate_segmentation(self.rows, self.root)))

    def test_duplicate_source_groups_cannot_cross_splits(self):
        self.rows[7]['reviewedSourceGroup'] = self.rows[0]['reviewedSourceGroup']
        self.assertTrue(any('crosses splits' in e for e in validate_segmentation(self.rows, self.root)))

    def test_coverage_is_checked_against_actual_masks(self):
        self.rows[6]['regions'] = copy.deepcopy(self.rows[1]['regions'])
        self.rows[6]['reviewedLabel'] = 'Anthracnose'
        self.assertTrue(any('Fungal Spots' in e and 'coverage' in e for e in validate_segmentation(self.rows, self.root)))

    def test_crops_of_same_source_cannot_cross_splits(self):
        self.rows[7]['roiSourceId'] = ' ' + self.rows[0]['roiSourceId'] + ' '
        with self.assertRaisesRegex(ValueError, 'ROI source .*crosses splits'):
            prepare_segmentation_dataset(self.rows, self.root / 'run', self.root)
        self.assertFalse((self.root / 'run').exists())

    def test_multiple_crops_of_same_source_in_one_split_are_allowed(self):
        self.rows[1]['roiSourceId'] = self.rows[0]['roiSourceId']
        self.assertEqual(validate_segmentation(self.rows, self.root), [])

    def test_existing_results_are_preserved(self):
        output = self.root / 'existing'
        output.mkdir()
        with self.assertRaises(FileExistsError):
            prepare_segmentation_dataset(self.rows, output, self.root)

    def test_exif_rotates_raw_polygons_with_image(self):
        row = self.rows[1]
        file = self.root / row['image']
        with Image.open(file) as source:
            exif = source.getexif()
            exif[274] = 6
            source.save(file, exif=exif)
        row['fileSha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        row['maskCoordinateSpace'] = 'raw'
        config = prepare_segmentation_dataset(self.rows, self.root / 'run', self.root)
        exported = json.loads((config.parent.parent / 'prepared-images.json').read_text())[1]
        self.assertEqual(exported['size'], [12, 16])
        for point, expected in zip(exported['regions'][0]['polygon'], [[.8, .2], [.8, .6], [.3, .6], [.3, .2]]):
            for value, target in zip(point, expected):
                self.assertAlmostEqual(value, target)

    def test_cli_rejects_unreviewed_manifest_before_loading_frameworks(self):
        manifest = self.root / 'unreviewed.json'
        manifest.write_text(json.dumps([{'id': 'unreviewed'}]))
        result = subprocess.run([sys.executable, str(ROOT / 'train_segmentation.py'), '--manifest', str(manifest),
                                 '--run-dir', str(self.root / 'run'), '--prepare-only'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('not training-ready', result.stderr)
        self.assertFalse((self.root / 'run').exists())


if __name__ == '__main__':
    unittest.main()
