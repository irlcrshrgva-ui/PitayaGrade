import hashlib
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.evaluate_quality_onnx import CLASS_NAMES, evaluate, preprocess, probabilities


class Value:
    def __init__(self, name, shape):
        self.name, self.shape = name, shape


class FakeSession:
    def get_inputs(self):
        return [Value('images', [1, 3, 224, 224])]

    def get_outputs(self):
        return [Value('logits', [1, 4])]

    def run(self, _outputs, feed):
        assert feed['images'].shape == (1, 3, 224, 224)
        return [np.array([[0., 1., 0., -1.]], dtype=np.float32)]


class QualityOnnxEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for index in range(2):
            path = self.root / f'{index}.png'
            image = Image.new('RGB', (20, 10), (255, index * 30, 0))
            image.save(path)
            self.rows.append({'id': f'test-{index}', 'task':'quality', 'image':path.name,
                              'candidateSplit':'test', 'reviewedLabel':'Grade B',
                              'fileSha256':hashlib.sha256(path.read_bytes()).hexdigest()})

    def test_preprocessing_matches_imagenet_contract(self):
        tensor = preprocess(self.root / '0.png')
        self.assertEqual(tensor.shape, (1, 3, 224, 224))
        self.assertEqual(tensor.dtype, np.float32)
        self.assertAlmostEqual(float(tensor[0, 0, 0, 0]), (1 - .485) / .229, places=4)

    def test_evaluation_returns_one_runtime_prediction_per_test_id(self):
        ids, labels, confidence, latency = evaluate(self.rows, FakeSession(), self.root)
        self.assertEqual(ids, ['test-0', 'test-1'])
        self.assertEqual(labels, ['Grade B', 'Grade B'])
        self.assertTrue(all(0 < value < 1 for value in confidence))
        self.assertTrue(all(value >= 0 for value in latency))

    def test_softmax_rejects_wrong_or_nonfinite_output(self):
        self.assertAlmostEqual(float(probabilities([0, 1, 0, -1]).sum()), 1)
        with self.assertRaisesRegex(ValueError, 'four finite'):
            probabilities([0, 1])
        with self.assertRaisesRegex(ValueError, 'four finite'):
            probabilities([0, 1, np.nan, -1])


if __name__ == '__main__':
    unittest.main()
