import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.create_annotation_packages import annotation_bundles, create_packages


class AnnotationPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = []
        for index, split in enumerate(('train', 'train', 'val', 'test', 'test', 'val')):
            image = self.root / f'{index}.png'
            image.write_bytes(b'crop-' + bytes([index]))
            self.rows.append({
                'id': f'crop-{index}', 'image': image.name,
                'fileSha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                'pixelSha256': hashlib.sha256(b'pixel-' + bytes([index])).hexdigest(),
                'candidateSplit': split, 'reviewedSourceGroup': f'fruit-{index}',
                'imageRole': 'fruit-roi', 'roiSourceId': f'source-{index}',
                'reviewedLabel': None, 'reviewer': None, 'reviewedAt': None,
                'annotationsComplete': False, 'annotationReviewer': None,
                'annotationReviewedAt': None, 'maskCoordinateSpace': 'upright', 'regions': None,
            })
        self.manifest = self.root / 'crops.json'
        self.manifest.write_text(json.dumps(self.rows), encoding='utf-8')

    def test_packages_are_nonoverlapping_and_contain_matching_images(self):
        public, archives = create_packages(self.manifest, self.root / 'packages', 3, self.root)
        self.assertEqual(public['manifestRowCount'], len(self.rows))
        assigned = [record for item in public['assignments'] for record in item['recordIds']]
        self.assertEqual(sorted(assigned), sorted(row['id'] for row in self.rows))
        self.assertEqual(len(set(assigned)), len(assigned))
        for archive in archives:
            with zipfile.ZipFile(archive) as bundle:
                rows = json.loads(bundle.read('annotation-manifest.json'))
                self.assertEqual(sum(name.startswith('images/') for name in bundle.namelist()), len(rows))
                self.assertTrue(all(row['image'].startswith('images/') for row in rows))

    def test_related_crops_cannot_cross_splits(self):
        self.rows[1]['reviewedSourceGroup'] = self.rows[0]['reviewedSourceGroup']
        self.rows[1]['candidateSplit'] = 'val'
        with self.assertRaisesRegex(ValueError, 'cross'):
            annotation_bundles(self.rows)

    def test_refuses_precompleted_or_modified_crops(self):
        self.rows[0]['annotationsComplete'] = True
        with self.assertRaisesRegex(ValueError, 'unannotated'):
            annotation_bundles(self.rows)

        self.rows[0]['annotationsComplete'] = False
        (self.root / self.rows[0]['image']).write_bytes(b'changed')
        self.manifest.write_text(json.dumps(self.rows), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            create_packages(self.manifest, self.root / 'bad-packages', 3, self.root)


if __name__ == '__main__':
    unittest.main()
