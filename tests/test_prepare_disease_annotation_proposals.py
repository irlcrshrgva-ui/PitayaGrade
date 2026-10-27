import unittest

import numpy as np

from scripts.prepare_disease_annotation_proposals import decode_proposal, pixel_bounds, select_rows


class PrepareDiseaseAnnotationProposalsTests(unittest.TestCase):
    def test_selects_deterministic_balanced_source_rows(self):
        rows = []
        labels = ['fruit_bad_unspecified', 'fruit_black_rot', 'fruit_fungi',
                  'fruit_good_source', 'healthy_fruit']
        for label in labels:
            for index in range(3):
                rows.append({'label': label, 'split': 'train', 'sha256': f'{index:064d}',
                             'path': f'{label}/{index}.jpg'})
        selected = select_rows(list(reversed(rows)), 2)
        self.assertEqual(len(selected), 10)
        self.assertEqual({row['sha256'] for row in selected}, {f'{index:064d}' for index in range(2)})

    def test_decodes_detector_box_and_maps_pixel_bounds(self):
        output = np.zeros((1, 8, 2), dtype=np.float32)
        output[0, 0:4, 1] = [320, 320, 320, 160]
        output[0, 6, 1] = .8
        proposal = decode_proposal(output)
        self.assertEqual(proposal['proposedGrade'], 'Grade C')
        self.assertAlmostEqual(proposal['confidence'], .8)
        self.assertEqual(pixel_bounds(proposal['box'], 1000, 500), (225, 181, 775, 319))

    def test_rejects_invalid_detector_outputs(self):
        with self.assertRaisesRegex(ValueError, 'shape'):
            decode_proposal(np.zeros((1, 4), dtype=np.float32))
        output = np.zeros((1, 8, 1), dtype=np.float32)
        output[0, 4, 0] = .8
        with self.assertRaisesRegex(ValueError, 'empty'):
            decode_proposal(output)


if __name__ == '__main__':
    unittest.main()
