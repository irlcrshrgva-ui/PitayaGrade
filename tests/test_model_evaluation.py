import unittest

from scripts.summarize_model_evaluation import summarize


LABELS = {'Grade A', 'Grade B', 'Grade C', 'Reject'}
MANIFEST = [
    {'id': 'a', 'candidateSplit': 'test', 'reviewedLabel': 'Grade A'},
    {'id': 'b', 'candidateSplit': 'test', 'reviewedLabel': 'Grade B'},
    {'id': 'c', 'candidateSplit': 'test', 'reviewedLabel': 'Grade C'},
    {'id': 'r', 'candidateSplit': 'test', 'reviewedLabel': 'Reject'},
]


def prediction(model, sample, label, confidence=.8, latency=10):
    return {'model_id': model, 'sample_id': sample, 'predicted_label': label,
            'confidence': str(confidence), 'inference_ms': str(latency)}


class EvaluationSummaryTests(unittest.TestCase):
    def test_complete_predictions_produce_traceable_metrics(self):
        rows = [prediction('model-a', 'a', 'Grade A', latency=1),
                prediction('model-a', 'b', 'Grade B', latency=2),
                prediction('model-a', 'c', 'Grade B', latency=3),
                prediction('model-a', 'r', 'Reject', latency=4)]
        result = summarize(MANIFEST, rows, LABELS)[0]
        self.assertEqual(result['sampleCount'], 4)
        self.assertEqual(result['accuracy'], .75)
        self.assertEqual(result['confusionMatrix']['Grade C']['Grade B'], 1)
        self.assertEqual(result['p95LatencyMs'], 4)
        self.assertEqual(result['mistakes'][0]['sampleId'], 'c')

    def test_multiple_models_are_compared_on_the_same_samples(self):
        rows = []
        for model in ('mobile', 'efficient'):
            rows.extend(prediction(model, row['id'], row['reviewedLabel']) for row in MANIFEST)
        results = summarize(MANIFEST, rows, LABELS)
        self.assertEqual([result['modelId'] for result in results], ['efficient', 'mobile'])
        self.assertTrue(all(result['accuracy'] == 1 for result in results))

    def test_missing_duplicate_and_unknown_predictions_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'missing 3 test predictions'):
            summarize(MANIFEST, [prediction('model', 'a', 'Grade A')], LABELS)
        duplicate = [prediction('model', row['id'], row['reviewedLabel']) for row in MANIFEST]
        duplicate.append(prediction('model', 'a', 'Grade A'))
        with self.assertRaisesRegex(ValueError, 'duplicate prediction'):
            summarize(MANIFEST, duplicate, LABELS)
        with self.assertRaisesRegex(ValueError, 'unknown or non-test sample'):
            summarize(MANIFEST, [prediction('model', 'unknown', 'Grade A')], LABELS)

    def test_invalid_labels_confidence_and_latency_fail_closed(self):
        bad = [prediction('model', row['id'], row['reviewedLabel']) for row in MANIFEST]
        bad[0]['predicted_label'] = 'Fresh'
        bad[1]['confidence'] = '1.1'
        bad[2]['inference_ms'] = '-1'
        with self.assertRaisesRegex(ValueError, 'incompatible label'):
            summarize(MANIFEST, bad, LABELS)


if __name__ == '__main__':
    unittest.main()

