"""Synthetic behavior checks; these settings are not agricultural calibration."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.preprocessing_preview import process, preview, validate_config


class PreprocessingTests(unittest.TestCase):
    def setUp(self):
        self.config = dict(hsvRanges=[[[0, 100, 50], [10, 255, 255]],
                                     [[170, 100, 50], [179, 255, 255]]],
                           grabcutIterations=2, claheClipLimit=2.0, claheGrid=[4, 4],
                           laplacianThreshold=1e9, seed=42)
        self.pixels = np.full((32, 48, 3), [20, 130, 30], dtype=np.uint8)
        self.pixels[8:24, 12:36] = [210, 30, 40]
        self.pixels[12:20, 18:30] = [170, 25, 35]
        self.image = Image.fromarray(self.pixels)

    def test_segments_synthetic_fruit_and_preserves_dimensions(self):
        images, stats = process(self.image, self.config)
        self.assertEqual(images['processed'].shape, self.pixels.shape)
        self.assertTrue(np.all(images['fruit-mask'][10:22, 14:34] == 255))
        self.assertTrue(np.all(images['processed'][:5] == 0))
        self.assertFalse(stats['blurApplied'])
        self.assertTrue(np.array_equal(images['processed'], images['lighting']))
        self.assertTrue(np.array_equal(np.array(self.image), self.pixels))

    def test_blur_threshold_and_repeatability(self):
        self.config['laplacianThreshold'] = 0
        images, stats = process(self.image, self.config)
        self.assertTrue(stats['blurApplied'])
        self.assertGreater(stats['laplacianVariance'], 0)
        self.assertFalse(np.array_equal(images['processed'], images['lighting']))
        again, other = process(self.image, self.config)
        self.assertEqual(stats, other)
        self.assertTrue(np.array_equal(images['processed'], again['processed']))

    def test_threshold_equality_does_not_blur(self):
        _, stats = process(self.image, self.config)
        self.config['laplacianThreshold'] = stats['laplacianVariance']
        self.assertFalse(process(self.image, self.config)[1]['blurApplied'])

    def test_missing_invalid_or_unknown_settings_rejected(self):
        for key, value in [('hsvRanges', []), ('grabcutIterations', True),
                           ('seed', -1), ('claheClipLimit', float('nan')),
                           ('laplacianThreshold', -1), ('claheGrid', [0, 2]),
                           ('hsvRanges', [[[179, 0, 0], [0, 255, 255]]]),
                           ('hsvRanges', [[[0, 0, 0], [180, 255, 255]]])]:
            config = copy.deepcopy(self.config)
            config[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_config(config)
        for config in ({}, dict(self.config, typo=1)):
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_degenerate_initialization_fails_without_invented_mask(self):
        for color in ((210, 30, 40), (20, 130, 30)):
            with self.assertRaisesRegex(ValueError, 'foreground and five background'):
                process(Image.new('RGB', (32, 32), color), self.config)

    def test_exif_orientation_is_applied_once(self):
        self.image.getexif()[274] = 6
        images, stats = process(self.image, self.config)
        self.assertEqual(stats['size'], [32, 48])
        self.assertTrue(np.array_equal(images['upright'], np.rot90(self.pixels, -1)))

    def test_preview_records_exact_settings_hashes_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.png'
            self.image.save(source)
            original = source.read_bytes()
            record = preview(source, self.config, root / 'preview')
            saved = json.loads((root / 'preview/preview.json').read_text())
            self.assertEqual(saved, record)
            self.assertEqual(saved['config'], self.config)
            self.assertEqual(source.read_bytes(), original)
            for name, digest in record['outputHashes'].items():
                self.assertEqual(hashlib.sha256((root / 'preview' / name).read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                preview(source, self.config, root / 'preview')

    def test_bad_input_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source.png'
            Image.new('RGB', (32, 32), 'black').save(source)
            with self.assertRaises(ValueError):
                preview(source, self.config, root / 'preview')
            self.assertFalse((root / 'preview').exists())
