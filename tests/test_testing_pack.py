import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.create_testing_pack import DEVICE_CASES, UAT_TASKS, create_pack


class TestingPackTests(unittest.TestCase):
    def test_pack_is_bound_to_apk_but_contains_no_fabricated_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apk = root / 'PitayaGrade.apk'
            apk.write_bytes(b'test-apk-content')
            output = root / 'pack'
            digest = create_pack(output, apk, '1.0.0-testing')
            self.assertEqual(digest, hashlib.sha256(apk.read_bytes()).hexdigest())
            with (output / 'device-test.csv').open(encoding='utf-8-sig', newline='') as handle:
                devices = list(csv.DictReader(handle))
            self.assertEqual(len(devices), len(DEVICE_CASES))
            self.assertTrue(all(row['apk_sha256'] == digest for row in devices))
            self.assertTrue(all(row['expected_result'] for row in devices))
            for field in ('tested_at', 'device_model', 'android_version', 'actual_result',
                          'status', 'evidence_path', 'tester'):
                self.assertTrue(all(not row[field] for row in devices), field)
            with (output / 'uat.csv').open(encoding='utf-8-sig', newline='') as handle:
                uat = list(csv.DictReader(handle))
            self.assertEqual(len(uat), len(UAT_TASKS))
            self.assertTrue(all(row['task_id'] and row['task_description'] for row in uat))
            for field in ('session_id', 'tested_at', 'participant_id', 'completed',
                          'time_seconds', 'error_count', 'help_needed'):
                self.assertTrue(all(not row[field] for row in uat), field)
            self.assertIn('BLANK PLANS', (output / 'README.txt').read_text(encoding='utf-8'))

    def test_existing_pack_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            apk = root / 'app.apk'
            apk.write_bytes(b'apk')
            output = root / 'pack'
            output.mkdir()
            sentinel = output / 'device-test.csv'
            sentinel.write_text('human evidence', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'never overwritten'):
                create_pack(output, apk, '1.0.0-testing')
            self.assertEqual(sentinel.read_text(encoding='utf-8'), 'human evidence')


if __name__ == '__main__':
    unittest.main()
