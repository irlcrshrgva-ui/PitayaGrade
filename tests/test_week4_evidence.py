import csv
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
        self.model_rows = [
            dict(evaluation_id='q1', evaluated_at='2026-10-25T10:00:00+08:00', task='quality',
                 model_name='MobileNetV2', model_version='1', model_sha256=sha,
                 test_manifest='quality.json', test_manifest_sha256=sha, test_sample_count='10',
                 classes='Grade A|Grade B|Grade C|Reject', input_size='224', confidence_threshold='0.5',
                 device='phone', runtime='onnx', accuracy='.8', macro_precision='.7', macro_recall='.7',
                 macro_f1='.7', map50='', map50_95='', mask_map50='', mean_latency_ms='10',
                 p95_latency_ms='15', failed_samples='0', confusion_matrix_path='q.csv',
                 predictions_path='p.csv', notes='', reviewer='reviewer-01'),
            dict(evaluation_id='d1', evaluated_at='2026-10-25T10:00:00+08:00', task='disease',
                 model_name='YOLOv8n-seg', model_version='1', model_sha256=sha,
                 test_manifest='disease.json', test_manifest_sha256=sha, test_sample_count='10',
                 classes='Sunburn', input_size='128', confidence_threshold='0.5', device='phone',
                 runtime='onnx', accuracy='', macro_precision='', macro_recall='', macro_f1='',
                 map50='.7', map50_95='.6', mask_map50='.5', mean_latency_ms='12', p95_latency_ms='18',
                 failed_samples='0', confusion_matrix_path='d.csv', predictions_path='dp.csv',
                 notes='', reviewer='reviewer-02')]
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


if __name__ == '__main__':
    unittest.main()
