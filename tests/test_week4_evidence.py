import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_week4_evidence import FILES, validate_evidence


class Week4EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sha = 'a' * 64
        for task in ('quality', 'disease'):
            (self.root / f'{task}.json').write_text(json.dumps([{'id':f'{task}-{i}'} for i in range(10)]))
        model_specs = [
            ('yolov8-nano', 'quality', 'YOLOv8-Nano', '640'),
            ('mobilenetv2-quality', 'quality', 'MobileNetV2', '224'),
            ('resnet50-quality', 'quality', 'ResNet50', '224'),
            ('efficientnet-b3-quality', 'quality', 'EfficientNet-B3', '224'),
            ('yolov8n-disease-seg', 'disease', 'YOLOv8n-seg', '128'),
        ]
        self.model_rows = []
        for index, (model_id, task, name, input_size) in enumerate(model_specs):
            model_path = self.root / f'{model_id}.onnx'
            model_path.write_bytes(f'model-{model_id}'.encode())
            predictions = self.root / f'{model_id}-predictions.csv'
            with predictions.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.DictWriter(handle, fieldnames=['model_id', 'sample_id', 'predicted_label',
                                                             'confidence', 'inference_ms'])
                writer.writeheader()
                for sample in range(10):
                    writer.writerow({'model_id':model_id, 'sample_id':f'{task}-{sample}',
                                     'predicted_label':'Grade A' if task == 'quality' else 'Sunburn',
                                     'confidence':'.8', 'inference_ms':'10'})
            confusion = self.root / f'{model_id}-confusion.csv'
            confusion.write_text('actual,predicted,count\nA,A,10\n', encoding='utf-8')
            manifest = self.root / f'{task}.json'
            quality = task == 'quality'
            self.model_rows.append(dict(
                evaluation_id=f'e{index}', evaluated_at='2026-10-25T10:00:00+08:00', task=task,
                model_id=model_id, model_name=name, model_version='1', model_path=model_path.name,
                model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest(),
                test_manifest=manifest.name,
                test_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                test_sample_count='10', classes='Grade A|Grade B|Grade C|Reject' if quality else 'Sunburn',
                input_size=input_size, confidence_threshold='0.5', device='phone', runtime='onnx',
                accuracy='.8' if quality else '', macro_precision='.7' if quality else '',
                macro_recall='.7' if quality else '', macro_f1='.7' if quality else '',
                map50='' if quality else '.7', map50_95='' if quality else '.6',
                mask_map50='' if quality else '.5', mean_latency_ms='10', p95_latency_ms='15',
                failed_samples='0', confusion_matrix_path=confusion.name,
                predictions_path=predictions.name, notes='', reviewer='reviewer-01'))
        self.device_rows = [dict(test_run_id='run-1', tested_at='2026-10-25T11:00:00+08:00',
            device_model='Phone A', android_version='15', app_version='1', apk_sha256=sha,
            network_state='offline', test_case='photo scan', precondition='installed', steps='scan',
            expected_result='grade', actual_result='grade', status='pass', evidence_path='photo.png',
            defect_id='', tester='tester-01')]
        self.uat_rows = [dict(session_id='s1', tested_at='2026-10-25T12:00:00+08:00',
            participant_id='p1', participant_role='farmer', device_model='Phone A', app_version='1',
            task_id='scan', task_description='Scan fruit', completed='true', time_seconds='20',
            error_count='0', help_needed='false', ease_rating_1_to_5='4',
            confidence_rating_1_to_5='4', participant_comment='Clear', observer_note='', issue_id='')]
        self.write('model-evaluation.csv', self.model_rows)
        self.write('device-test.csv', self.device_rows)
        self.write('uat.csv', self.uat_rows)

    def write(self, name, rows):
        fields = list(FILES[name])
        extras = sorted(set().union(*(row.keys() for row in rows)) - set(fields))
        with (self.root / name).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields + extras)
            writer.writeheader()
            writer.writerows(rows)

    def test_valid_evidence_produces_checksum_audit(self):
        report = validate_evidence(self.root)
        self.assertEqual(report['status'], 'pass')
        self.assertFalse(report['errors'])
        self.assertEqual(report['deviceCount'], 1)
        self.assertEqual(report['participantCount'], 1)
        self.assertEqual(set(report['modelAssets']), {row['model_id'] for row in self.model_rows})

    def test_unresolved_device_failure_blocks_release(self):
        self.device_rows[0]['status'] = 'fail'
        self.write('device-test.csv', self.device_rows)
        report = validate_evidence(self.root)
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(any('blocks release' in error for error in report['errors']))

    def test_missing_model_task_and_bad_uat_rating_are_rejected(self):
        self.write('model-evaluation.csv', self.model_rows[:1])
        self.uat_rows[0]['ease_rating_1_to_5'] = '6'
        self.write('uat.csv', self.uat_rows)
        report = validate_evidence(self.root)
        self.assertTrue(any('both quality and disease' in error for error in report['errors']))
        self.assertTrue(any('ease_rating' in error for error in report['errors']))

    def test_mismatched_model_hash_and_incomplete_predictions_are_rejected(self):
        self.model_rows[0]['model_sha256'] = '0' * 64
        predictions = self.root / self.model_rows[1]['predictions_path']
        lines = predictions.read_text(encoding='utf-8').splitlines()
        predictions.write_text('\n'.join(lines[:-1]) + '\n', encoding='utf-8')
        self.write('model-evaluation.csv', self.model_rows)
        report = validate_evidence(self.root)
        self.assertTrue(any('model_sha256 does not match' in error for error in report['errors']))
        self.assertTrue(any('predictions row count' in error for error in report['errors']))


if __name__ == '__main__':
    unittest.main()
