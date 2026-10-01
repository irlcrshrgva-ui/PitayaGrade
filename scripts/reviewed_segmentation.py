"""Prepare manually reviewed symptom boundaries on fruit ROI images."""
import argparse
import hashlib
import json
import math
from collections import defaultdict
from io import BytesIO
from pathlib import Path

from PIL import Image
from scripts.image_orientation import orientation_of, orient_box, upright_rgb
from scripts.reviewed_training import ROOT, validation

SYMPTOMS = ('Anthracnose', 'Stem Canker', 'Soft Rot', 'Pest Damage', 'Sunburn', 'Fungal Spots')


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _intersects(a, b, c, d):
    ab_c, ab_d, cd_a, cd_b = _cross(a, b, c), _cross(a, b, d), _cross(c, d, a), _cross(c, d, b)
    if ab_c * ab_d < 0 and cd_a * cd_b < 0:
        return True
    for start, end, point, cross in ((a, b, c, ab_c), (a, b, d, ab_d), (c, d, a, cd_a), (c, d, b, cd_b)):
        if abs(cross) < 1e-12 and all(min(start[i], end[i]) <= point[i] <= max(start[i], end[i]) for i in (0, 1)):
            return True
    return False


def polygon_error(points):
    if not isinstance(points, list) or len(points) < 3:
        return 'polygon requires at least three vertices'
    if any(not isinstance(p, list) or len(p) != 2 or
           any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p) for p in points):
        return 'polygon vertices must be finite normalized xy pairs'
    if len({tuple(p) for p in points}) != len(points):
        return 'polygon has repeated vertices; omit the repeated closing vertex'
    n = len(points)
    area = sum(points[i][0] * points[(i + 1) % n][1] - points[(i + 1) % n][0] * points[i][1] for i in range(n))
    if abs(area) < 1e-12:
        return 'polygon has zero area'
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            if _intersects(points[i], points[(i + 1) % n], points[j], points[(j + 1) % n]):
                return 'polygon self-intersects'
    return None


def validate_segmentation(rows, root=ROOT, check_files=True):
    errors = validation.validate(rows, 'manuscript-disease', root, check_files, require_class_coverage=False)
    if not isinstance(rows, list):
        return errors
    coverage = defaultdict(set)
    for row in rows:
        if not isinstance(row, dict):
            continue
        ident = row.get('id', '<missing id>')
        split = row.get('candidateSplit')
        if not isinstance(split, str):
            continue
        if row.get('imageRole') != 'fruit-roi':
            errors.append(f'{ident}: reviewed fruit-roi imageRole required')
        if row.get('annotationsComplete') is not True or not all(
                isinstance(row.get(key), str) and row[key].strip()
                for key in ('annotationReviewer', 'annotationReviewedAt', 'roiSourceId')):
            errors.append(f'{ident}: missing complete mask/crop review evidence')
        if row.get('maskCoordinateSpace') not in ('raw', 'upright'):
            errors.append(f'{ident}: maskCoordinateSpace must explicitly be raw or upright')
        regions = row.get('regions')
        if not isinstance(regions, list):
            errors.append(f'{ident}: explicit regions list required; masks are never inferred')
            continue
        if row.get('reviewedLabel') == 'Healthy':
            if regions:
                errors.append(f'{ident}: Healthy review conflicts with symptom regions')
            else:
                coverage[split].add('Healthy')
        labels = set()
        for region in regions:
            if not isinstance(region, dict) or region.get('label') not in SYMPTOMS:
                errors.append(f'{ident}: unsupported symptom label')
                continue
            label = region['label']
            labels.add(label)
            error = polygon_error(region.get('polygon'))
            if region.get('holes'):
                error = 'polygon holes need a reviewed compatible representation; they cannot be silently filled'
            if error:
                errors.append(f'{ident}: {error}')
            else:
                coverage[split].add(label)
        if row.get('reviewedLabel') != 'Healthy' and (
                not isinstance(row.get('reviewedLabel'), str) or row['reviewedLabel'] not in labels):
            errors.append(f'{ident}: reviewed disease requires an annotated region of that class')
    for split in ('train', 'val', 'test'):
        missing = (set(SYMPTOMS) | {'Healthy'}) - coverage[split]
        if missing:
            errors.append(f'{split}: missing reviewed mask/Healthy coverage: {", ".join(sorted(missing))}')
    return errors


def read_segmentation_manifest(path, root=ROOT):
    rows = json.loads(Path(path).read_text(encoding='utf-8'))
    errors = validate_segmentation(rows, root, check_files=False)
    if not errors:
        errors = validate_segmentation(rows, root)
    if errors:
        raise ValueError(f'Segmentation data is not training-ready ({len(errors)} errors):\n' + '\n'.join(errors[:20]))
    return rows


def prepare_segmentation_dataset(rows, run_dir, root=ROOT):
    errors = validate_segmentation(rows, root)
    if errors:
        raise ValueError('\n'.join(errors[:20]))
    run_dir = Path(run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    dataset = run_dir / 'dataset'
    exports = []
    for row in rows:
        data = (root / row['image']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['fileSha256']:
            raise ValueError('Image changed during preparation')
        with Image.open(BytesIO(data)) as original:
            orientation = orientation_of(original)
            image = upright_rgb(original)
        stem = hashlib.sha256(row['id'].encode()).hexdigest()
        output = dataset / 'images' / row['candidateSplit'] / (stem + '.png')
        label_file = dataset / 'labels' / row['candidateSplit'] / (stem + '.txt')
        output.parent.mkdir(parents=True, exist_ok=True)
        label_file.parent.mkdir(parents=True, exist_ok=True)
        image.save(output, format='PNG')
        regions, lines = [], []
        for region in row['regions']:
            points = region['polygon']
            if row['maskCoordinateSpace'] == 'raw':
                points = [orient_box([x, y, 0, 0], orientation)[:2] for x, y in points]
            regions.append({'label': region['label'], 'polygon': points})
            values = [str(SYMPTOMS.index(region['label']))] + [str(v) for point in points for v in point]
            lines.append(' '.join(values))
        label_file.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
        exports.append({'id': row['id'], 'image': output.relative_to(run_dir).as_posix(),
                        'sourceFileSha256': row['fileSha256'], 'sourceOrientation': orientation,
                        'fileSha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                        'size': list(image.size), 'maskCoordinateSpace': 'upright', 'regions': regions})
    config = dataset / 'data.yaml'
    config.write_text('path: ' + json.dumps(dataset.as_posix()) + '\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n' +
                      ''.join(f'  {i}: {label}\n' for i, label in enumerate(SYMPTOMS)), encoding='utf-8')
    (run_dir / 'reviewed-manifest.json').write_text(json.dumps(rows, indent=2) + '\n', encoding='utf-8')
    (run_dir / 'prepared-images.json').write_text(json.dumps(exports, indent=2) + '\n', encoding='utf-8')
    return config


def segmentation_arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        args.rows = read_segmentation_manifest(args.manifest)
        if args.run_dir.exists():
            raise ValueError('Run directory already exists; choose a new directory.')
    except (ValueError, OSError) as error:
        parser.error(str(error))
    return args
