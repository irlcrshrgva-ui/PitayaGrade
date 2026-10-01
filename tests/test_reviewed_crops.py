import hashlib
import copy
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageOps

from scripts.reviewed_crops import prepare_crops
from scripts.reviewed_segmentation import validate_segmentation
from scripts.reviewed_training import validation
from scripts.verify_crop_provenance import verify_crop


class CropTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for i, split in enumerate(('train', 'val', 'test')):
            image = Image.new('RGB', (8, 4))
            image.putdata([(x * 20, y * 30, i) for y in range(4) for x in range(8)])
            file = self.root / f'{i}.png'
            image.save(file)
            self.rows.append(dict(id=f'source-{i}', image=file.name, candidateSplit=split,
                                  reviewedLabel='Dragon Fruit', reviewedSourceGroup=f'fruit-{i}',
                                  reviewer='Synthetic', reviewedAt='2026-09-21',
                                  annotationReviewer='Synthetic', annotationReviewedAt='2026-09-21',
                                  boundingBoxes=[[.25, .5, .5, 1]], boxCoordinateSpace='raw',
                                  fileSha256=hashlib.sha256(file.read_bytes()).hexdigest(),
                                  pixelSha256=hashlib.sha256(image.tobytes()).hexdigest()))

    def test_crops_match_pixels_and_keep_provenance_without_inventing_reviews(self):
        result = prepare_crops(self.rows, self.root / 'run', self.root)
        crops = json.loads(result.read_text())
        for source, crop in zip(self.rows, crops):
            with Image.open(self.root / source['image']) as image, Image.open(self.root / crop['image']) as actual:
                self.assertEqual(actual.tobytes(), image.crop((0, 0, 4, 4)).tobytes())
                self.assertEqual(actual.getexif().get(274, 1), 1)
            self.assertEqual(crop['cropProvenance']['pixelBounds'], [0, 0, 4, 4])
            self.assertEqual(crop['candidateSplit'], source['candidateSplit'])
            self.assertEqual(crop['reviewedSourceGroup'], source['reviewedSourceGroup'])
            self.assertEqual(crop['roiSourceId'], source['id'])
            self.assertEqual(verify_crop(crop, self.root), [])
            self.assertIsNone(crop['reviewedLabel'])
            self.assertIsNone(crop['regions'])
            self.assertEqual(hashlib.sha256((self.root / source['image']).read_bytes()).hexdigest(), source['fileSha256'])
        self.assertTrue(validation.validate(crops, 'manuscript-quality', self.root))
        self.assertTrue(validate_segmentation(crops, self.root))

    def test_all_exif_modes_crop_same_reviewed_raw_region(self):
        for orientation in range(1, 9):
            with self.subTest(orientation=orientation):
                for row in self.rows:
                    file = self.root / row['image']
                    with Image.open(file) as image:
                        exif = image.getexif()
                        exif[274] = orientation
                        image.save(file, exif=exif)
                    row['fileSha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
                crops = json.loads(prepare_crops(self.rows, self.root / f'run-{orientation}', self.root).read_text())
                self.assertEqual(verify_crop(crops[0], self.root), [])
                with Image.open(self.root / self.rows[0]['image']) as original:
                    expected = original.crop((0, 0, 4, 4))
                    expected.getexif()[274] = orientation
                    expected = ImageOps.exif_transpose(expected)
                with Image.open(self.root / crops[0]['image']) as actual:
                    self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_multiple_boxes_produce_separate_crops_in_same_group(self):
        self.rows[0]['boundingBoxes'].append([.75, .5, .5, 1])
        crops = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())
        self.assertEqual(len(crops), 4)
        self.assertNotEqual(crops[0]['id'], crops[1]['id'])
        self.assertEqual(crops[0]['roiSourceId'], crops[1]['roiSourceId'])
        self.assertEqual(crops[0]['reviewedSourceGroup'], crops[1]['reviewedSourceGroup'])

    def test_upright_boxes_are_not_rotated_twice_and_round_outward(self):
        row = self.rows[0]
        file = self.root / row['image']
        with Image.open(file) as image:
            exif = image.getexif()
            exif[274] = 6
            image.save(file, exif=exif)
        row['fileSha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        row['boxCoordinateSpace'] = 'upright'
        row['boundingBoxes'] = [[.5, .25, .6, .4]]
        crops = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())
        self.assertEqual(crops[0]['cropProvenance']['pixelBounds'], [0, 0, 4, 4])
        with Image.open(file) as original, Image.open(self.root / crops[0]['image']) as actual:
            expected = ImageOps.exif_transpose(original).crop((0, 0, 4, 4))
            self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_invalid_review_fails_before_writing(self):
        self.rows[0]['annotationReviewer'] = ''
        with self.assertRaises(ValueError):
            prepare_crops(self.rows, self.root / 'run', self.root)
        self.assertFalse((self.root / 'run').exists())

    def test_rehashed_replacement_crop_is_rejected_by_training_gate(self):
        crops = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())
        crop = crops[0]
        file = self.root / crop['image']
        replacement = Image.new('RGB', (4, 4), (255, 0, 255))
        replacement.save(file)
        crop['fileSha256'] = hashlib.sha256(file.read_bytes()).hexdigest()
        crop['pixelSha256'] = hashlib.sha256(replacement.tobytes()).hexdigest()
        crop.update(reviewedLabel='Grade A', reviewer='Synthetic', reviewedAt='2026-10-01')
        self.assertIn('Crop pixels', verify_crop(crop, self.root)[0])
        errors = validation.validate(crops, 'manuscript-quality', self.root, require_class_coverage=False)
        self.assertTrue(any('Crop pixels' in error for error in errors))

    def test_changed_source_snapshot_and_reassigned_split_are_rejected(self):
        crops = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())
        crop = crops[0]
        changed = copy.deepcopy(crop)
        changed['candidateSplit'] = 'test'
        self.assertIn('candidateSplit', verify_crop(changed, self.root)[0])
        changed = copy.deepcopy(crop)
        changed['reviewedSourceGroup'] = 'unrelated'
        self.assertIn('reviewedSourceGroup', verify_crop(changed, self.root)[0])
        (self.root / 'run/source-manifest.json').write_text('[]')
        self.assertIn('Source manifest checksum', verify_crop(crop, self.root)[0])

    def test_forged_geometry_or_review_and_outside_paths_are_rejected(self):
        crop = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())[0]
        for key, value in (('pixelBounds', [1, 0, 4, 4]), ('sourceBoxIndex', True),
                           ('boxReviewer', 'Someone else'), ('sourceManifest', '../outside.json'),
                           ('cropSize', [8, 4]), ('sourceOrientation', 6)):
            with self.subTest(key=key):
                changed = copy.deepcopy(crop)
                changed['cropProvenance'][key] = value
                self.assertTrue(verify_crop(changed, self.root))
        self.assertTrue(verify_crop(None, self.root))
        self.assertTrue(verify_crop({'cropProvenance': {}}, self.root))

    def test_changed_source_pixels_are_rejected_even_if_crop_stays_intact(self):
        crop = json.loads(prepare_crops(self.rows, self.root / 'run', self.root).read_text())[0]
        Image.new('RGB', (8, 4), 'black').save(self.root / self.rows[0]['image'])
        self.assertIn('Source image checksum', verify_crop(crop, self.root)[0])

    def test_existing_output_and_outside_workspace_rejected(self):
        with self.assertRaises(FileExistsError):
            prepare_crops(self.rows, self.root, self.root)
        with self.assertRaisesRegex(ValueError, 'inside the workspace'):
            prepare_crops(self.rows, self.root.parent / 'outside-crops', self.root)
