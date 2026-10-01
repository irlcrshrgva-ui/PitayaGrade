import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from scripts.disease_coverage import measure_coverage, measure_files


class CoverageTests(unittest.TestCase):
    def test_overlapping_instances_and_classes_count_union_once(self):
        fruit = np.ones((4, 4), dtype=np.uint8)
        first = np.zeros_like(fruit); first[:2] = 1
        second = np.zeros_like(fruit); second[1:3] = 255
        result = measure_coverage(fruit, [{'label': 'Sunburn', 'mask': first},
                                         {'label': 'Sunburn', 'mask': first},
                                         {'label': 'Pest Damage', 'mask': second}])
        self.assertEqual(result['percentOfVisibleFruit'], 75)
        self.assertEqual(result['perClass']['Sunburn']['percentOfVisibleFruit'], 50)
        self.assertEqual(result['symptomPixels'], 12)

    def test_background_is_excluded_from_both_denominator_and_symptom_area(self):
        fruit = np.zeros((4, 4), dtype=np.uint8); fruit[:2] = 1
        symptom = np.ones_like(fruit)
        result = measure_coverage(fruit, [{'label': 'Soft Rot', 'mask': symptom}])
        self.assertEqual(result['fruitPixels'], 8)
        self.assertEqual(result['symptomPixels'], 8)
        self.assertEqual(result['percentOfVisibleFruit'], 100)
        self.assertEqual(result['symptomPixelsOutsideFruit'], 8)

    def test_no_regions_is_zero_coverage_without_a_healthy_diagnosis(self):
        result = measure_coverage(np.ones((3, 3), dtype=bool), [])
        self.assertEqual(result['percentOfVisibleFruit'], 0)
        self.assertNotIn('isHealthy', result)

    def test_empty_invalid_and_misaligned_masks_rejected(self):
        for fruit in (np.zeros((2, 2), dtype=np.uint8), np.ones((2, 2), dtype=float),
                      np.full((2, 2), 2), np.ones((2, 2, 3), dtype=np.uint8)):
            with self.subTest(shape=fruit.shape), self.assertRaises(ValueError):
                measure_coverage(fruit, [])
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            measure_coverage(np.ones((2, 2), dtype=np.uint8),
                             [{'label': 'Sunburn', 'mask': np.ones((3, 3), dtype=np.uint8)}])

    def test_unknown_labels_and_implicit_region_list_rejected(self):
        for regions in (None, [{'label': 'Healthy', 'mask': np.ones((2, 2), dtype=np.uint8)}]):
            with self.assertRaises(ValueError):
                measure_coverage(np.ones((2, 2), dtype=np.uint8), regions)

    def test_file_measurement_is_traceable_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            Image.new('L', (4, 4), 255).save(root / 'fruit.png')
            mask = np.zeros((4, 4), dtype=np.uint8); mask[:1] = 255
            Image.fromarray(mask).save(root / 'symptom.png')
            manifest = root / 'input.json'
            manifest.write_text(json.dumps({'coordinateSpace': 'upright-roi', 'fruitMask': 'fruit.png',
                'regions': [{'label': 'Fungal Spots', 'mask': 'symptom.png'}]}))
            output = root / 'result.json'
            result = measure_files(manifest, output)
            self.assertEqual(result['percentOfVisibleFruit'], 25)
            self.assertEqual(len(result['inputs']), 2)
            self.assertEqual(json.loads(output.read_text()), result)
            with self.assertRaises(FileExistsError):
                measure_files(manifest, output)
