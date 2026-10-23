import unittest

from scripts.create_assisted_recheck_packages import assisted_bundles, assignment_index
from scripts.create_review_packages import assign_bundles


def row(ident, task, group, reviewer='AI-assisted-reviewer-01'):
    return {'id': ident, 'task': task, 'reviewedSourceGroup': group, 'reviewer': reviewer}


class AssistedRecheckPackageTests(unittest.TestCase):
    def test_only_assisted_rows_are_balanced_without_splitting_groups(self):
        rows = [
            row('a', 'quality', 'fruit-1'),
            row('b', 'quality', 'fruit-1'),
            row('c', 'maturity', 'fruit-2'),
            row('d', 'quality', 'fruit-3', 'reviewer-02'),
        ]
        assignments = assign_bundles(assisted_bundles(rows), 2)
        owners = {}
        for index, assignment in enumerate(assignments):
            for item in assignment['rows']:
                owners[item['id']] = index
        self.assertEqual(owners['a'], owners['b'])
        self.assertNotIn('d', owners)
        public = assignment_index(assignments)
        self.assertEqual(public['manifestRowCount'], 3)
        self.assertEqual(sum(item['recordCount'] for item in public['assignments']), 3)

    def test_manifest_without_assisted_rows_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no AI-assisted records'):
            assisted_bundles([row('a', 'quality', 'fruit-1', 'reviewer-01')])


if __name__ == '__main__':
    unittest.main()
