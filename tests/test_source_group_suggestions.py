import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.suggest_source_groups import suggest, write_outputs


class SourceGroupSuggestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.rows = []
        for name, split, reverse in [('a', 'train', False), ('b', 'test', False),
                                     ('c', 'val', True)]:
            image = Image.new('L', (16, 16))
            pixels = []
            for y in range(16):
                for x in range(16):
                    value = (255 if x > y else 0)
                    pixels.append(255 - value if reverse else value)
            image.putdata(pixels)
            path = self.root / f'{name}.png'
            image.save(path)
            self.rows.append({'id': name, 'task': 'quality', 'candidateSplit': split,
                              'sourceLabel': 'source', 'image': path.name})

    def tearDown(self):
        self.temp.cleanup()

    def test_flags_similar_images_crossing_splits_without_approving_them(self):
        report, assignments = suggest(self.rows, self.root, 0, 0)
        self.assertEqual(report['candidateGroupCount'], 1)
        self.assertEqual(report['crossSplitGroupCount'], 1)
        self.assertEqual({row['id'] for row in assignments}, {'a', 'b'})
        self.assertTrue(all(row['status'] == 'unverified-source-group-suggestion'
                            for row in assignments))
        self.assertNotIn('reviewedSourceGroup', assignments[0])

    def test_outputs_are_separate_and_never_overwritten(self):
        report, assignments = suggest(self.rows, self.root, 0, 0)
        output = self.root / 'suggestions.json'
        json_output, csv_output = write_outputs(output, report, assignments)
        self.assertTrue(json_output.is_file())
        self.assertTrue(csv_output.is_file())
        self.assertEqual(json.loads(json_output.read_text())['purpose'],
                         'review assistance only; perceptual similarity is not source identity')
        with self.assertRaises(FileExistsError):
            write_outputs(output, report, assignments)


if __name__ == '__main__':
    unittest.main()

