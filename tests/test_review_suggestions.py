import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.suggest_reviews import decode, generate_suggestions, preprocess, write_outputs


class _Endpoint:
    def __init__(self, name):
        self.name = name


class _Session:
    def __init__(self, outputs):
        self.outputs = iter(outputs)

    def get_inputs(self):
        return [_Endpoint('images')]

    def get_outputs(self):
        return [_Endpoint('output0')]

    def run(self, names, feeds):
        if names != ['output0'] or list(feeds) != ['images']:
            raise AssertionError('unexpected inference request')
        self.last_shape = list(feeds['images'].shape)
        return [next(self.outputs)]


class ReviewSuggestionTests(unittest.TestCase):
    def _output(self, class_index, confidence):
        output = np.zeros((1, 8, 2), dtype=np.float32)
        output[0, 4 + class_index, 1] = confidence
        return output

    def test_decodes_grade_without_promoting_low_confidence(self):
        accepted = decode(self._output(2, .8))
        self.assertEqual(accepted['proposedLabel'], 'Grade C')
        self.assertAlmostEqual(accepted['confidence'], .8)
        rejected = decode(self._output(0, .2))
        self.assertIsNone(rejected['proposedLabel'])
        self.assertGreater(rejected['reviewPriority'], accepted['reviewPriority'])
        with self.assertRaisesRegex(ValueError, 'shape'):
            decode(np.zeros((1, 7, 2), dtype=np.float32))

    def test_generates_separate_uncertainty_ranked_proposals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / 'fruit.png'
            Image.new('RGB', (12, 8), (200, 30, 80)).save(image)
            model = root / 'model.onnx'
            model.write_bytes(b'model fixture')
            rows = [
                {'id':'high', 'task':'quality', 'image':'fruit.png', 'sourceLabel':'Fresh',
                 'candidateSplit':'train', 'reviewedLabel':None},
                {'id':'low', 'task':'quality', 'image':'fruit.png', 'sourceLabel':'Fresh',
                 'candidateSplit':'test', 'reviewedLabel':None},
                {'id':'reviewed', 'task':'quality', 'image':'fruit.png', 'reviewedLabel':'Grade A'},
                {'id':'maturity', 'task':'maturity', 'image':'fruit.png', 'reviewedLabel':None},
            ]
            session = _Session([self._output(1, .9), self._output(3, .4)])
            proposals = generate_suggestions(rows, root, model, session)
            self.assertEqual([row['id'] for row in proposals], ['low', 'high'])
            self.assertTrue(all(row['humanReviewRequired'] for row in proposals))
            self.assertTrue(all(row['status'] == 'unverified-model-proposal' for row in proposals))
            self.assertEqual(session.last_shape, [1, 3, 640, 640])
            original = json.loads(json.dumps(rows))
            output, csv_output = write_outputs(root / 'suggestions.json', proposals, model, root / 'manifest.json')
            self.assertTrue(output.is_file())
            self.assertTrue(csv_output.is_file())
            saved = json.loads(output.read_text(encoding='utf-8'))
            self.assertIn('not ground truth', saved['purpose'])
            self.assertEqual(rows, original)

    def test_preprocesses_rgb_and_rejects_nonfinite_output(self):
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / 'fruit.png'
            Image.new('RGB', (2, 1), (255, 128, 0)).save(image)
            tensor = preprocess(image)
            self.assertEqual(list(tensor.shape), [1, 3, 640, 640])
            self.assertAlmostEqual(float(tensor[0, 0, 0, 0]), 1.0)
            self.assertAlmostEqual(float(tensor[0, 1, 0, 0]), 128 / 255, places=5)
            output = self._output(0, .8)
            output[0, 4, 0] = np.nan
            with self.assertRaisesRegex(ValueError, 'non-finite'):
                decode(output)


if __name__ == '__main__':
    unittest.main()
