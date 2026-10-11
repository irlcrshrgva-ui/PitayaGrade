import unittest

from scripts.merge_review_exports import merge_exports


def row(ident, reviewer=None):
    return {
        'id': ident, 'task': 'quality', 'image': f'dataset/public/prepared/quality/{ident}.jpg',
        'candidateSplit': 'train', 'sourceDataset': 'fixture', 'sourceLabel': 'original',
        'fileSha256': ident * 4, 'pixelSha256': ident * 4,
        'reviewedLabel': 'Grade A' if reviewer else None,
        'reviewedSourceGroup': f'fruit-{ident}' if reviewer else None,
        'reviewer': reviewer, 'reviewedAt': '2026-10-11T10:00:00+08:00' if reviewer else None,
    }


class MergeReviewExportsTests(unittest.TestCase):
    def setUp(self):
        self.manifest = [row('a'), row('b')]
        self.index = {'assignments': [
            {'reviewerId': 'reviewer-01', 'recordIds': ['a']},
            {'reviewerId': 'reviewer-02', 'recordIds': ['b']},
        ]}

    def test_complete_non_overlapping_exports_merge(self):
        merged = merge_exports(self.manifest, self.index, [
            ('one.json', [row('a', 'reviewer-01')]),
            ('two.json', [row('b', 'reviewer-02')]),
        ])
        self.assertEqual([item['reviewer'] for item in merged], ['reviewer-01', 'reviewer-02'])

    def test_missing_export_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing completed exports'):
            merge_exports(self.manifest, self.index, [('one.json', [row('a', 'reviewer-01')])])

    def test_changed_identity_is_rejected(self):
        changed = row('a', 'reviewer-01')
        changed['image'] = 'changed.jpg'
        with self.assertRaisesRegex(ValueError, 'protected field'):
            merge_exports(self.manifest, self.index, [
                ('one.json', [changed]), ('two.json', [row('b', 'reviewer-02')])])


if __name__ == '__main__':
    unittest.main()
