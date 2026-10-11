import unittest

from scripts.create_review_packages import assign_bundles, build_bundles, verify_assignments


class ReviewPackageTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'id': f'quality:{index}', 'task': 'quality', 'image': f'dataset/public/prepared/quality/{index}.jpg'}
            for index in range(7)
        ]
        self.suggestions = {'groups': [{
            'suggestedSourceGroup': 'candidate-source-0001',
            'members': [{'id': 'quality:0'}, {'id': 'quality:1'}],
        }]}

    def test_split_is_complete_balanced_and_keeps_candidate_groups_together(self):
        bundles = build_bundles(self.rows, self.suggestions)
        assignments = assign_bundles(bundles, 3)
        verify_assignments(self.rows, assignments, self.suggestions)
        sizes = [len(assignment['rows']) for assignment in assignments]
        self.assertLessEqual(max(sizes) - min(sizes), 1)
        owners = [{row['id'] for row in assignment['rows']} for assignment in assignments]
        self.assertTrue(any({'quality:0', 'quality:1'} <= ids for ids in owners))

    def test_unknown_group_member_is_rejected(self):
        broken = {'groups': [{
            'suggestedSourceGroup': 'candidate-source-0001',
            'members': [{'id': 'quality:0'}, {'id': 'missing'}],
        }]}
        with self.assertRaisesRegex(ValueError, 'unknown'):
            build_bundles(self.rows, broken)


if __name__ == '__main__':
    unittest.main()
