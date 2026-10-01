import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageOps
from scripts.image_orientation import load_upright_rgb, orient_box, orientation_of, upright_digest
from scripts.reviewed_detection import prepare_detection_dataset, validate_detection
from scripts.reviewed_training import validation

ROOT = Path(__file__).resolve().parents[1]


def pattern():
    image = Image.new('RGB', (12, 8))
    for x in range(2, 5):
        for y in range(1, 3):
            image.putpixel((x, y), (255, 20, 10))
    return image


class OrientationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def record(self, image, name, split, orientation=1):
        exif = image.getexif()
        exif[274] = orientation
        file = self.root / (name + '.png')
        image.save(file, exif=exif)
        with Image.open(file) as raw:
            digest = hashlib.sha256(raw.convert('RGB').tobytes()).hexdigest()
        return dict(id=name, image=file.name, candidateSplit=split, reviewedLabel='Dragon Fruit',
                    reviewedSourceGroup=name, reviewer='Synthetic test fixture', reviewedAt='2026-09-20',
                    annotationReviewer='Synthetic test fixture', annotationReviewedAt='2026-09-20',
                    boundingBoxes=[[3.5 / 12, 2 / 8, 3 / 12, 2 / 8]],
                    fileSha256=hashlib.sha256(file.read_bytes()).hexdigest(), pixelSha256=digest)

    def rows(self, orientation=6):
        return [self.record(pattern(), 'rotated', 'train', orientation),
                self.record(Image.new('RGB', (12, 8), (10, 20, 30)), 'val', 'val'),
                self.record(Image.new('RGB', (12, 8), (30, 20, 10)), 'test', 'test')]

    def test_all_eight_box_transforms_match_actual_image_pixels(self):
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                row = self.record(pattern(), f'orientation-{orientation}', 'train', orientation)
                actual = load_upright_rgb(self.root / row['image'])
                left, top, right, bottom = actual.getbbox()
                expected = [(left + right) / 2 / actual.width, (top + bottom) / 2 / actual.height,
                            (right - left) / actual.width, (bottom - top) / actual.height]
                for value, target in zip(orient_box(row['boundingBoxes'][0], orientation), expected):
                    self.assertAlmostEqual(value, target)
                self.assertEqual(orientation_of(actual), 1)

    def test_oriented_images_require_coordinate_space(self):
        with self.assertRaisesRegex(ValueError, 'boxCoordinateSpace'):
            prepare_detection_dataset(self.rows(), self.root / 'run', self.root)
        self.assertFalse((self.root / 'run').exists())

    def test_export_rotates_image_and_raw_boxes_preserving_source(self):
        rows = self.rows()
        rows[0]['boxCoordinateSpace'] = 'raw'
        config = prepare_detection_dataset(rows, self.root / 'run', self.root)
        exported = json.loads((config.parent.parent / 'prepared-images.json').read_text())[0]
        self.assertEqual(exported['sourceOrientation'], 6)
        self.assertEqual(exported['size'], [8, 12])
        self.assertEqual(exported['boundingBoxes'], [orient_box(rows[0]['boundingBoxes'][0], 6)])
        output = config.parent.parent / exported['image']
        with Image.open(output) as image:
            self.assertEqual(orientation_of(image), 1)
            self.assertEqual(image.tobytes(), load_upright_rgb(self.root / rows[0]['image']).tobytes())
        self.assertEqual(hashlib.sha256((self.root / rows[0]['image']).read_bytes()).hexdigest(), rows[0]['fileSha256'])
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), exported['fileSha256'])

    def test_already_upright_box_coordinates_are_not_rotated_twice(self):
        rows = self.rows()
        rows[0]['boxCoordinateSpace'] = 'upright'
        rows[0]['boundingBoxes'] = [orient_box(rows[0]['boundingBoxes'][0], 6)]
        config = prepare_detection_dataset(rows, self.root / 'run', self.root)
        exported = json.loads((config.parent.parent / 'prepared-images.json').read_text())[0]
        self.assertEqual(exported['boundingBoxes'], rows[0]['boundingBoxes'])

    def test_rejects_same_upright_image_across_splits_with_different_raw_pixels(self):
        rows = self.rows(1)
        raw = pattern().transpose(Image.Transpose.ROTATE_90)
        rows[1] = self.record(raw, 'same-upright', 'val', 6)
        self.assertNotEqual(rows[0]['pixelSha256'], rows[1]['pixelSha256'])
        errors = validation.validate(rows, 'manuscript-detection', self.root)
        self.assertTrue(any('identical upright image' in e and 'crosses splits' in e for e in errors), errors)

    def test_upright_hash_includes_dimensions(self):
        self.assertNotEqual(upright_digest(Image.new('RGB', (4, 6))), upright_digest(Image.new('RGB', (6, 4))))

    def test_invalid_orientation_is_rejected(self):
        rows = self.rows(9)
        errors = validate_detection(rows, self.root)
        self.assertTrue(any('Invalid EXIF orientation' in e for e in errors), errors)

    def test_validator_remains_callable_as_a_script(self):
        manifest = self.root / 'empty.json'
        manifest.write_text('[]')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate-research-data.py'), str(manifest),
                                 '--target', 'manuscript-quality'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)['ready'])


if __name__ == '__main__':
    unittest.main()
