import unittest

from scripts.reconcile_review_splits import reconcile_splits


def row(ident, split, group, pixel=None):
    return {
        'id': ident,
        'task': 'quality',
        'candidateSplit': split,
        'reviewedSourceGroup': group,
        'pixelSha256': pixel or ident,
    }


class ReconcileReviewSplitsTests(unittest.TestCase):
    def test_source_group_is_moved_to_one_split(self):
        reconciled, summary = reconcile_splits([
            row('a', 'train', 'fruit-1'),
            row('b', 'train', 'fruit-1'),
            row('c', 'val', 'fruit-1'),
        ])
        self.assertEqual({item['candidateSplit'] for item in reconciled}, {'train'})
        self.assertEqual(summary, {'linkedComponentsChanged': 1, 'rowsMoved': 1})

    def test_pixel_link_transitively_connects_groups(self):
        reconciled, _ = reconcile_splits([
            row('a', 'train', 'fruit-1', 'same'),
            row('b', 'val', 'fruit-2', 'same'),
            row('c', 'val', 'fruit-2', 'different'),
        ])
        self.assertEqual(len({item['candidateSplit'] for item in reconciled}), 1)

    def test_does_not_mutate_input(self):
        rows = [row('a', 'train', 'fruit-1'), row('b', 'val', 'fruit-1')]
        reconcile_splits(rows)
        self.assertEqual([item['candidateSplit'] for item in rows], ['train', 'val'])

    def test_missing_group_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing task or reviewed source group'):
            reconcile_splits([row('a', 'train', '')])


if __name__ == '__main__':
    unittest.main()
