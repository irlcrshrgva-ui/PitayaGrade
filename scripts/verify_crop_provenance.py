"""Reproduce reviewed crop pixels from their retained source images and boxes."""
import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from scripts.crop_geometry import crop_bounds, ROUNDING
from scripts.image_orientation import orientation_of, orient_box, upright_rgb


def workspace_file(value, root):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing provenance file path')
    path = (root / value).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Provenance file is missing or outside the workspace')
    return path


def verify_crop(row, root):
    """Return errors without changing any image or review field."""
    root = Path(root).resolve()
    try:
        if not isinstance(row, dict) or not isinstance(row.get('cropProvenance'), dict):
            raise ValueError('Explicit cropProvenance required')
        provenance = row['cropProvenance']
        snapshot = workspace_file(provenance.get('sourceManifest'), root).read_bytes()
        if hashlib.sha256(snapshot).hexdigest() != provenance.get('sourceManifestSha256'):
            raise ValueError('Source manifest checksum mismatch')
        sources = json.loads(snapshot)
        if not isinstance(sources, list) or any(not isinstance(source, dict) for source in sources):
            raise ValueError('Source manifest must contain records')
        matches = [source for source in sources if source.get('id') == row.get('roiSourceId')]
        if len(matches) != 1:
            raise ValueError('ROI source must match exactly one retained source record')
        source = matches[0]
        for key in ('candidateSplit', 'reviewedSourceGroup'):
            if row.get(key) != source.get(key):
                raise ValueError(f'Crop {key} differs from retained source')
        if row.get('imageRole') != 'fruit-roi':
            raise ValueError('Crop imageRole must be fruit-roi')
        if (source.get('image') != provenance.get('sourceImage') or
                source.get('fileSha256') != provenance.get('sourceFileSha256')):
            raise ValueError('Source image provenance differs from retained record')
        for key, source_key in (('boxReviewer', 'annotationReviewer'), ('boxReviewedAt', 'annotationReviewedAt')):
            if (not isinstance(source.get(source_key), str) or not source[source_key].strip() or
                    provenance.get(key) != source[source_key]):
                raise ValueError('Bounding-box review evidence differs from retained source')
        index = provenance.get('sourceBoxIndex')
        boxes = source.get('boundingBoxes')
        if type(index) is not int or not isinstance(boxes, list) or not 0 <= index < len(boxes):
            raise ValueError('Invalid source box index')
        expected_id = hashlib.sha256(json.dumps([source['id'], index]).encode()).hexdigest()
        if row.get('id') != expected_id:
            raise ValueError('Crop identifier does not match its source box')
        data = workspace_file(source.get('image'), root).read_bytes()
        if hashlib.sha256(data).hexdigest() != source.get('fileSha256'):
            raise ValueError('Source image checksum mismatch')
        with Image.open(BytesIO(data)) as original:
            orientation = orientation_of(original)
            if hashlib.sha256(original.convert('RGB').tobytes()).hexdigest() != source.get('pixelSha256'):
                raise ValueError('Source pixel checksum mismatch')
            if orientation != 1 and source.get('boxCoordinateSpace') not in ('raw', 'upright'):
                raise ValueError('Oriented source needs explicit boxCoordinateSpace')
            if source.get('boxCoordinateSpace') not in (None, 'raw', 'upright'):
                raise ValueError('Invalid source boxCoordinateSpace')
            upright = upright_rgb(original)
        box = orient_box(boxes[index], orientation) if source.get('boxCoordinateSpace') == 'raw' else boxes[index]
        bounds = crop_bounds(box, upright.size)
        expected = upright.crop(bounds)
        for key, value in (('sourceOrientation', orientation), ('uprightBox', list(box)),
                           ('uprightSourceSize', list(upright.size)), ('pixelBounds', list(bounds)),
                           ('cropSize', list(expected.size)), ('rounding', ROUNDING)):
            if provenance.get(key) != value:
                raise ValueError(f'Crop provenance {key} does not match reproduced geometry')
        data = workspace_file(row.get('image'), root).read_bytes()
        if hashlib.sha256(data).hexdigest() != row.get('fileSha256'):
            raise ValueError('Crop file checksum mismatch')
        with Image.open(BytesIO(data)) as actual:
            if orientation_of(actual) != 1:
                raise ValueError('Crop must already be upright')
            actual = actual.convert('RGB')
            if actual.size != expected.size or actual.tobytes() != expected.tobytes():
                raise ValueError('Crop pixels do not match reviewed source box')
            if hashlib.sha256(actual.tobytes()).hexdigest() != row.get('pixelSha256'):
                raise ValueError('Crop pixel checksum mismatch')
    except (ValueError, OSError, TypeError, KeyError, IndexError) as error:
        ident = row.get('id', '<missing id>') if isinstance(row, dict) else '<invalid row>'
        return [f'{ident}: {error}']
    return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        rows = json.loads(args.manifest.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or not rows:
            raise ValueError('Manifest must contain crop records')
        errors = [error for row in rows for error in verify_crop(row, args.root)]
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({'verified': not errors, 'records': len(rows), 'errorCount': len(errors),
                      'firstErrors': errors[:20],
                      'limitation': 'Pixel provenance does not prove box, grade or disease annotation truth.'}, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
