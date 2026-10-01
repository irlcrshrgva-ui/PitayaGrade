"""Export upright fruit crops from reviewed boxes for subsequent label/mask review."""
import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from scripts.image_orientation import orientation_of, orient_box, upright_rgb
from scripts.crop_geometry import crop_bounds, ROUNDING
from scripts.reviewed_detection import read_detection_manifest, validate_detection
from scripts.reviewed_training import ROOT


def prepare_crops(rows, run_dir, root=ROOT):
    root = Path(root).resolve()
    run_dir = Path(run_dir).resolve()
    if not run_dir.is_relative_to(root):
        raise ValueError('Crop output must be inside the workspace for review-manifest paths')
    errors = validate_detection(rows, root)
    if errors:
        raise ValueError('\n'.join(errors[:20]))
    run_dir.mkdir(parents=True, exist_ok=False)
    snapshot = run_dir / 'source-manifest.json'
    snapshot.write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    snapshot_hash = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    crops = []
    for row in rows:
        data = (root / row['image']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['fileSha256']:
            raise ValueError('Image changed during crop preparation')
        with Image.open(BytesIO(data)) as original:
            orientation = orientation_of(original)
            image = upright_rgb(original)
        for index, original_box in enumerate(row['boundingBoxes']):
            box = orient_box(original_box, orientation) if row.get('boxCoordinateSpace') == 'raw' else original_box
            # Enclose the entire reviewed box; Pillow uses an exclusive right/bottom.
            bounds = crop_bounds(box, image.size)
            crop = image.crop(bounds)
            ident = hashlib.sha256(json.dumps([row['id'], index]).encode()).hexdigest()
            output = run_dir / 'images' / row['candidateSplit'] / (ident + '.png')
            output.parent.mkdir(parents=True, exist_ok=True)
            # Do not carry source EXIF orientation into already upright crops.
            clean = Image.frombytes('RGB', crop.size, crop.tobytes())
            clean.save(output)
            crops.append({
                'id': ident, 'image': output.relative_to(root).as_posix(),
                'fileSha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                'pixelSha256': hashlib.sha256(clean.tobytes()).hexdigest(),
                'candidateSplit': row['candidateSplit'],
                'reviewedSourceGroup': row['reviewedSourceGroup'],
                'imageRole': 'fruit-roi', 'roiSourceId': row['id'],
                'reviewedLabel': None, 'reviewer': None, 'reviewedAt': None,
                'annotationsComplete': False, 'annotationReviewer': None,
                'annotationReviewedAt': None, 'maskCoordinateSpace': 'upright',
                'regions': None,
                'cropProvenance': {
                    'sourceManifest': snapshot.relative_to(root).as_posix(),
                    'sourceManifestSha256': snapshot_hash,
                    'sourceImage': row['image'], 'sourceFileSha256': row['fileSha256'],
                    'sourceOrientation': orientation, 'sourceBoxIndex': index,
                    'uprightBox': box, 'uprightSourceSize': list(image.size),
                    'pixelBounds': list(bounds), 'cropSize': list(clean.size),
                    'rounding': ROUNDING,
                    'boxReviewer': row['annotationReviewer'],
                    'boxReviewedAt': row['annotationReviewedAt'],
                },
            })
    manifest = run_dir / 'crop-review-manifest.json'
    manifest.write_text(json.dumps(crops, indent=2) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        rows = read_detection_manifest(args.manifest)
        manifest = prepare_crops(rows, args.run_dir)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f'Crops awaiting grade/disease review: {manifest}')
    print('No grade, disease diagnosis or symptom mask was inferred.')


if __name__ == '__main__':
    main()
