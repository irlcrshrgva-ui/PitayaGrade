import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from scripts.mendeley_disease import file_hash
from scripts.prepare_disease import prepare
from scripts.train_disease import validate_manifest


class DiseaseDataTests(unittest.TestCase):
    def fixture(self, root):
        (root / 'cfchfdpfw5' / 'extracted' / 'Dragon fruit and leaf').mkdir(parents=True)
        rows = []
        rng = np.random.default_rng(7)
        for label in ('Healthy_fruit', 'Black_Rot'):
            for i in range(12):
                path = root / f'{label}-{i}.png'
                Image.fromarray(rng.integers(0, 256, (48, 48, 3), dtype=np.uint8)).save(path)
                rows.append({'dataset': 'kpsywfwkrf', 'sourceLabel': label, 'path': path.name,
                             'sha256': file_hash(path)})
        (root / 'source-files.json').write_text(json.dumps(rows))
        return rows

    def test_deduplication_and_deterministic_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.fixture(root)
            duplicate = root / 'duplicate.bmp'
            with Image.open(root / rows[0]['path']) as image:
                image.save(duplicate)
            rows.append(dict(rows[0], path=duplicate.name, sha256=file_hash(duplicate)))
            (root / 'source-files.json').write_text(json.dumps(rows))
            mapping = {'kpsywfwkrf': {'Healthy_fruit': 'healthy_fruit', 'Black_Rot': 'fruit_black_rot'}}
            first = prepare(root, root / 'one.json', mapping)
            second = prepare(root, root / 'two.json', mapping)
            self.assertEqual(first, second)
            self.assertEqual(first['removedDuplicates'], 1)
            self.assertEqual(len(first['rows']), 24)
            self.assertEqual(validate_manifest(first), ['fruit_black_rot', 'healthy_fruit'])
            with self.assertRaises(FileExistsError):
                prepare(root, root / 'one.json', mapping)

    def test_conflicting_duplicates_are_quarantined(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.fixture(root)
            rows.append(dict(rows[0], sourceLabel='Black_Rot'))
            (root / 'source-files.json').write_text(json.dumps(rows))
            result = prepare(root, root / 'out.json', {'kpsywfwkrf': {
                'Healthy_fruit': 'healthy_fruit', 'Black_Rot': 'fruit_black_rot'}})
            self.assertEqual(len(result['quarantined']), 2)
            self.assertEqual(len(result['rows']), 23)

    def test_unknown_labels_and_changed_files_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'Unmapped'):
                prepare(root, root / 'out.json', {})
            (root / rows[0]['path']).write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                prepare(root, root / 'out.json', {'kpsywfwkrf': {
                    'Healthy_fruit': 'healthy_fruit', 'Black_Rot': 'fruit_black_rot'}})

    def test_training_rejects_duplicate_groups(self):
        rows = [{'split': split, 'label': 'one', 'group': 'same',
                 'sha256': str(i), 'pixelSha256': str(i)}
                for i, split in enumerate(('train', 'validation', 'test'))]
        with self.assertRaisesRegex(ValueError, 'leaking group'):
            validate_manifest({'rows': rows})


if __name__ == '__main__':
    unittest.main()
