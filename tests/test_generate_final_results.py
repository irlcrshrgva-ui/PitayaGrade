import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_final_results import generate


class GenerateFinalResultsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        model_fields = ['evaluation_id','task','model_id','model_name','accuracy','macro_precision',
                        'macro_recall','macro_f1','map50','map50_95','mask_map50','mean_latency_ms','p95_latency_ms']
        self.write('model-evaluation.csv', model_fields, [
            ['q1','quality','mobilenetv2-quality','MobileNetV2','.8','.7','.75','.72','','','','4','6'],
            ['d1','disease','yolov8n-disease-seg','YOLOv8n-seg','','','','','.6','.5','.4','12','18']])
        self.write('device-test.csv', ['device_model','android_version','status'],
                   [['Phone A','15','pass'], ['Phone A','15','pass']])
        self.write('uat.csv', ['participant_id','completed','ease_rating_1_to_5',
                               'confidence_rating_1_to_5','time_seconds','task_id'],
                   [['p1','true','4','5','20','scan'], ['p2','true','5','4','30','report']])
        files = {}
        for name in ('model-evaluation.csv','device-test.csv','uat.csv'):
            data = (self.root / name).read_bytes()
            with (self.root / name).open(newline='', encoding='utf-8') as handle:
                rows = len(list(csv.DictReader(handle)))
            files[name] = {'sha256':hashlib.sha256(data).hexdigest(), 'rows':rows}
        self.audit = self.root / 'evidence-audit.json'
        self.audit.write_text(json.dumps({'generatedAt':'2026-10-25T00:00:00Z',
            'status':'pass','errors':[],'files':files}), encoding='utf-8')

    def write(self, name, fields, rows):
        with (self.root / name).open('w', newline='', encoding='utf-8') as handle:
            writer = csv.writer(handle); writer.writerow(fields); writer.writerows(rows)

    def test_generates_traceable_tables_and_figures(self):
        output = self.root / 'results'
        trace = generate(self.root, self.audit, output)
        self.assertEqual(trace['status'], 'generated-from-validated-evidence')
        self.assertIn('80.0%', (output / 'model-results.md').read_text(encoding='utf-8'))
        self.assertIn('100.0%', (output / 'uat-summary.md').read_text(encoding='utf-8'))
        self.assertIn('<svg', (output / 'quality-model-results.svg').read_text(encoding='utf-8'))
        self.assertEqual(set(trace['outputs']), {
            'model-results.md','quality-model-results.svg','disease-model-results.svg',
            'device-test-summary.md','uat-summary.md','uat-results.svg'})

    def test_refuses_changed_or_unvalidated_evidence(self):
        (self.root / 'uat.csv').write_text('changed\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'no longer matches'):
            generate(self.root, self.audit, self.root / 'bad-results')
        value = json.loads(self.audit.read_text(encoding='utf-8'))
        value['status'] = 'blocked'; self.audit.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not passing'):
            generate(self.root, self.audit, self.root / 'blocked-results')


if __name__ == '__main__':
    unittest.main()
