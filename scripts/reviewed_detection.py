"""Validate actual reviewed fruit boxes and export a separate detection dataset."""
import argparse
import hashlib
import json
import math
from io import BytesIO
from pathlib import Path
from PIL import Image

from scripts.reviewed_training import ROOT, validation
from scripts.image_orientation import orientation_of, orient_box, upright_rgb


def validate_detection(rows, root=ROOT, check_files=True):
    errors = validation.validate(rows, 'manuscript-detection', root, check_files)
    if not isinstance(rows, list):
        return errors
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = row.get('id', '<missing id>')
        if not all(isinstance(row.get(key), str) and row[key].strip()
                   for key in ('annotationReviewer', 'annotationReviewedAt')):
            errors.append(f'{ident}: missing bounding-box review evidence')
        boxes = row.get('boundingBoxes')
        space = row.get('boxCoordinateSpace')
        if space is not None and space not in ('raw', 'upright'):
            errors.append(f'{ident}: boxCoordinateSpace must be raw or upright')
        if not isinstance(boxes, list) or not boxes:
            errors.append(f'{ident}: reviewed boundingBoxes are required; no boxes are inferred')
            continue
        for box in boxes:
            if (not isinstance(box, list) or len(box) != 4 or
                    any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) for n in box)):
                errors.append(f'{ident}: box must contain four finite normalized xywh numbers')
                continue
            x, y, width, height = box
            if not (0 < width <= 1 and 0 < height <= 1 and
                    0 <= x - width / 2 and x + width / 2 <= 1 and
                    0 <= y - height / 2 and y + height / 2 <= 1):
                errors.append(f'{ident}: box has zero area or extends beyond the image')
    if check_files and not errors:
        for row in rows:
            with Image.open(root / row['image']) as image:
                if orientation_of(image) != 1 and row.get('boxCoordinateSpace') not in ('raw', 'upright'):
                    errors.append(f"{row['id']}: oriented image requires explicit boxCoordinateSpace (raw or upright)")
    return errors


def read_detection_manifest(manifest, root=ROOT):
    rows = json.loads(Path(manifest).read_text(encoding='utf-8'))
    # Fail early on missing reviews before decoding thousands of images.
    errors = validate_detection(rows, root, check_files=False)
    if not errors:
        errors = validate_detection(rows, root)
    if errors:
        raise ValueError(f'Detection data is not training-ready ({len(errors)} errors):\n' + '\n'.join(errors[:20]))
    return rows


def prepare_detection_dataset(rows, run_dir, root=ROOT):
    errors = validate_detection(rows, root)
    if errors:
        raise ValueError('\n'.join(errors[:20]))
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    dataset = run_dir / 'dataset'
    exports = []
    for row in rows:
        source = root / row['image']
        stem = hashlib.sha256(row['id'].encode()).hexdigest()
        # Re-read exactly the bytes validated for this source; preserve originals.
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['fileSha256']:
            raise ValueError('Image changed during preparation')
        with Image.open(BytesIO(data)) as opened:
            orientation = orientation_of(opened)
            upright = upright_rgb(opened)
        suffix = '.png' if orientation != 1 else source.suffix.lower()
        image = dataset / 'images' / row['candidateSplit'] / (stem + suffix)
        label = dataset / 'labels' / row['candidateSplit'] / (stem + '.txt')
        image.parent.mkdir(parents=True, exist_ok=True)
        label.parent.mkdir(parents=True, exist_ok=True)
        if orientation == 1:
            image.write_bytes(data)
        else:
            upright.save(image, format='PNG')
        boxes = row['boundingBoxes']
        if row.get('boxCoordinateSpace') == 'raw':
            boxes = [orient_box(box, orientation) for box in boxes]
        label.write_text(''.join('0 ' + ' '.join(str(n) for n in box) + '\n'
                                 for box in boxes), encoding='utf-8')
        exports.append({'id': row['id'], 'image': image.relative_to(run_dir).as_posix(),
                        'sourceFileSha256': row['fileSha256'], 'sourceOrientation': orientation,
                        'fileSha256': hashlib.sha256(image.read_bytes()).hexdigest(),
                        'size': list(upright.size), 'boxCoordinateSpace': 'upright', 'boundingBoxes': boxes})
    config = dataset / 'data.yaml'
    config.write_text('path: ' + json.dumps(dataset.as_posix()) + '\n'
                      'train: images/train\nval: images/val\ntest: images/test\n'
                      'names:\n  0: Dragon Fruit\n', encoding='utf-8')
    (run_dir / 'reviewed-manifest.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    (run_dir / 'prepared-images.json').write_text(json.dumps(exports, indent=2) + '\n', encoding='utf-8')
    return config


def detection_arguments(argv=None):
    parser = argparse.ArgumentParser(description='Prepare/train manuscript YOLOv8-Nano fruit detection using reviewed boxes.')
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--prepare-only', action='store_true', help='Validate and export without importing training frameworks.')
    args = parser.parse_args(argv)
    try:
        args.rows = read_detection_manifest(args.manifest)
        if args.run_dir.exists():
            raise ValueError('Run directory already exists; choose a new directory.')
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args
