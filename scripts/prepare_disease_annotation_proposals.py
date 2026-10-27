"""Create human-reviewable fruit-crop proposals from retained disease source images."""
import argparse
import hashlib
import json
import math
import shutil
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
INPUT_SIZE = 640
GRADE_CLASSES = ['Grade A', 'Grade B', 'Grade C', 'Reject']
FRUIT_SOURCE_LABELS = {
    'fruit_bad_unspecified', 'fruit_black_rot', 'fruit_fungi',
    'fruit_good_source', 'healthy_fruit',
}


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def select_rows(rows, per_source_label):
    """Deterministically sample each retained fruit source label without relabeling it."""
    grouped = defaultdict(list)
    for row in rows:
        if row.get('label') in FRUIT_SOURCE_LABELS:
            grouped[row['label']].append(row)
    missing = sorted(FRUIT_SOURCE_LABELS - set(grouped))
    if missing:
        raise ValueError(f'Missing retained fruit source labels: {", ".join(missing)}')
    selected = []
    for label in sorted(grouped):
        candidates = sorted(grouped[label], key=lambda row: (row.get('split', ''), row.get('sha256', ''), row['path']))
        target = min(per_source_label, len(candidates))
        quotas = {'train': int(target * .70), 'validation': int(target * .15)}
        quotas['test'] = target - quotas['train'] - quotas['validation']
        chosen = []
        for split in ('train', 'validation', 'test'):
            chosen.extend([row for row in candidates if row.get('split') == split][:quotas[split]])
        chosen_paths = {row['path'] for row in chosen}
        chosen.extend(row for row in candidates if row['path'] not in chosen_paths)
        selected.extend(chosen[:target])
    return selected


def preprocess(image):
    resized = image.resize((INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    pixels = np.asarray(resized, dtype=np.float32) / 255.0
    return np.transpose(pixels, (2, 0, 1))[None, ...]


def decode_proposal(output):
    values = np.asarray(output)
    if values.ndim != 3 or values.shape[0] != 1 or values.shape[1] != 8 or values.shape[2] < 1:
        raise ValueError(f'Unsupported detector output shape: {list(values.shape)}')
    if not np.isfinite(values).all():
        raise ValueError('Detector produced non-finite output')
    scores = values[0, 4:8, :]
    flat = int(np.argmax(scores))
    class_index, detection_index = np.unravel_index(flat, scores.shape)
    cx, cy, width, height = (float(values[0, channel, detection_index]) for channel in range(4))
    if width <= 0 or height <= 0:
        raise ValueError('Detector proposed an empty crop')
    box = ((cx - width / 2) / INPUT_SIZE, (cy - height / 2) / INPUT_SIZE,
           (cx + width / 2) / INPUT_SIZE, (cy + height / 2) / INPUT_SIZE)
    if not all(math.isfinite(value) for value in box):
        raise ValueError('Detector proposed a non-finite crop')
    left, top, right, bottom = box
    box_width, box_height = right - left, bottom - top
    padding = .05
    box = (max(0.0, left - box_width * padding), max(0.0, top - box_height * padding),
           min(1.0, right + box_width * padding), min(1.0, bottom + box_height * padding))
    if box[2] - box[0] < .03 or box[3] - box[1] < .03:
        raise ValueError('Detector proposed an implausibly small crop')
    return {'box': [round(value, 8) for value in box],
            'confidence': round(float(scores[class_index, detection_index]), 8),
            'proposedGrade': GRADE_CLASSES[class_index]}


def pixel_bounds(box, width, height):
    left = max(0, min(width - 1, int(math.floor(box[0] * width))))
    top = max(0, min(height - 1, int(math.floor(box[1] * height))))
    right = max(left + 1, min(width, int(math.ceil(box[2] * width))))
    bottom = max(top + 1, min(height, int(math.ceil(box[3] * height))))
    return left, top, right, bottom


def prepare(manifest_path, output_dir, model_path, per_source_label=120, workers=4, root=ROOT):
    output_dir, root = Path(output_dir), Path(root).resolve()
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite {output_dir}')
    payload = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    rows = payload.get('rows') if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError('Disease source manifest must contain a non-empty rows array')
    import onnxruntime as ort
    session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    selected = select_rows(rows, per_source_label)
    model_hash = hashlib.sha256(Path(model_path).read_bytes()).hexdigest()
    try:
        output_relative = output_dir.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError('Output directory must be inside the project root') from error
    output_dir.mkdir(parents=True)
    manifest_rows, failures = [], []
    try:
        def process(source_row):
            source = (Path(manifest_path).parent / source_row['path']).resolve()
            if not source.is_relative_to(Path(manifest_path).parent.resolve()) or not source.is_file():
                raise FileNotFoundError(f'Missing source image: {source_row["path"]}')
            try:
                with Image.open(source) as raw:
                    upright = ImageOps.exif_transpose(raw).convert('RGB')
                result = session.run([output_name], {input_name: preprocess(upright)})[0]
                proposal = decode_proposal(result)
                bounds = pixel_bounds(proposal['box'], *upright.size)
                crop = upright.crop(bounds)
                original_crop_size = list(crop.size)
                crop.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                source_identity = f'{source_row["sha256"]}:{source_row["label"]}:{source_row["split"]}'
                ident_hash = sha256_bytes(source_identity.encode('utf-8'))
                ident = f'disease-crop:{ident_hash}'
                split = 'val' if source_row['split'] == 'validation' else source_row['split']
                relative = output_relative / 'images' / split / f'{ident_hash}.png'
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                crop.save(destination, format='PNG', optimize=True)
                encoded = destination.read_bytes()
                return ({
                    'id': ident, 'task': 'disease', 'image': relative.as_posix(),
                    'candidateSplit': split, 'sourceDataset': source_row['dataset'],
                    'sourceLabel': source_row['sourceLabel'], 'sourceMappedLabel': source_row['label'],
                    'sourcePath': source_row['path'], 'sourceFileSha256': source_row['sha256'],
                    'fileSha256': sha256_bytes(encoded), 'pixelSha256': sha256_bytes(crop.tobytes()),
                    'reviewedSourceGroup': source_row.get('group') or source_row['sha256'],
                    'imageRole': 'fruit-roi', 'roiSourceId': source_row['sha256'],
                    'maskCoordinateSpace': 'upright', 'reviewedLabel': None, 'reviewer': None,
                    'reviewedAt': None, 'annotationsComplete': False, 'annotationReviewer': None,
                    'annotationReviewedAt': None, 'regions': None,
                    'cropReviewStatus': 'unverified-model-proposal', 'cropReviewer': None,
                    'cropReviewedAt': None, 'excludedFromTraining': False, 'exclusionReason': None,
                    'cropProvenance': {
                        'method': 'model-assisted-proposal', 'model': str(Path(model_path).relative_to(root)).replace('\\', '/'),
                        'modelSha256': model_hash, 'proposalConfidence': proposal['confidence'],
                        'proposedGradeNotDiseaseLabel': proposal['proposedGrade'],
                        'normalizedUprightBox': proposal['box'], 'uprightPixelBounds': list(bounds),
                        'originalCropSize': original_crop_size, 'cropSize': list(crop.size),
                        'reviewResizeMaximum': 1024, 'humanReviewRequired': True,
                    },
                }, None)
            except (OSError, ValueError, RuntimeError) as error:
                return (None, {'path': source_row['path'], 'sourceLabel': source_row['label'], 'error': str(error)})

        with ThreadPoolExecutor(max_workers=workers) as executor:
            results = executor.map(process, selected)
            for position, (proposal_row, failure) in enumerate(results, 1):
                if proposal_row:
                    manifest_rows.append(proposal_row)
                if failure:
                    failures.append(failure)
                if position % 100 == 0:
                    print(f'Prepared {position}/{len(selected)} proposed fruit crops', flush=True)
        manifest_path_out = output_dir / 'crop-review-manifest.json'
        manifest_path_out.write_text(json.dumps(manifest_rows, indent=2) + '\n', encoding='utf-8')
        audit = {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'status': 'unverified-model-assisted-crop-proposals',
            'humanReviewRequired': True, 'sourceManifest': str(manifest_path),
            'sourceManifestSha256': hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest(),
            'model': str(model_path), 'modelSha256': model_hash,
            'requestedCount': len(selected), 'proposalCount': len(manifest_rows),
            'failureCount': len(failures), 'failures': failures,
            'sourceLabelCounts': dict(sorted(Counter(row['sourceMappedLabel'] for row in manifest_rows).items())),
            'splitCounts': dict(sorted(Counter(row['candidateSplit'] for row in manifest_rows).items())),
            'manifestSha256': hashlib.sha256(manifest_path_out.read_bytes()).hexdigest(),
            'warning': 'Source labels and detector grades are provenance only, never disease ground truth.',
        }
        (output_dir / 'proposal-audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
        return audit
    except Exception:
        shutil.rmtree(output_dir, ignore_errors=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path, default=ROOT / 'www/model/best.onnx')
    parser.add_argument('--per-source-label', type=int, default=120)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.per_source_label < 1:
        parser.error('--per-source-label must be positive')
    if not 1 <= args.workers <= 8:
        parser.error('--workers must be between 1 and 8')
    try:
        print(json.dumps(prepare(args.manifest, args.output, args.model, args.per_source_label,
                                 args.workers), indent=2))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
