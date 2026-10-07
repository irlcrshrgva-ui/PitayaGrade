"""Create non-authoritative quality-label proposals from the bundled ONNX model."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
CLASSES = ['Grade A', 'Grade B', 'Grade C', 'Reject']
INPUT_SIZE = 640
CONFIDENCE_THRESHOLD = 0.30


def _safe_image(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f'Image path escapes the project root: {relative}')
    if not candidate.is_file():
        raise FileNotFoundError(f'Missing review image: {relative}')
    return candidate


def preprocess(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB').resize(
            (INPUT_SIZE, INPUT_SIZE), Image.Resampling.BILINEAR)
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    return np.transpose(pixels, (2, 0, 1))[None, ...]


def decode(output):
    values = np.asarray(output)
    if values.ndim != 3 or values.shape[0] != 1 or values.shape[1] != 4 + len(CLASSES) or values.shape[2] < 1:
        raise ValueError(f'Unsupported grade-model output shape: {list(values.shape)}')
    if not np.isfinite(values).all():
        raise ValueError('Grade model produced non-finite output')
    class_scores = values[0, 4:4 + len(CLASSES), :]
    flat_index = int(np.argmax(class_scores))
    class_index, detection_index = np.unravel_index(flat_index, class_scores.shape)
    confidence = float(class_scores[class_index, detection_index])
    return {
        'proposedLabel': CLASSES[class_index] if confidence >= CONFIDENCE_THRESHOLD else None,
        'confidence': confidence,
        'reviewPriority': round(1.0 - min(1.0, max(0.0, confidence)), 6),
    }


def generate_suggestions(rows, root, model_path, session, limit=None):
    model_path = Path(model_path)
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    input_name = session.get_inputs()[0].name
    output = session.get_outputs()[0]
    proposals = []
    selected = [row for row in rows if row.get('task') == 'quality' and not row.get('reviewedLabel')]
    if limit is not None:
        selected = selected[:limit]
    for position, row in enumerate(selected, 1):
        tensor = preprocess(_safe_image(root, row.get('image', '')))
        result = session.run([output.name], {input_name: tensor})[0]
        decoded = decode(result)
        proposals.append({
            'id': row.get('id'),
            **decoded,
            'sourceLabel': row.get('sourceLabel'),
            'candidateSplit': row.get('candidateSplit'),
            'modelId': 'yolov8-nano',
            'modelSha256': model_hash,
            'status': 'unverified-model-proposal',
            'humanReviewRequired': True,
        })
        if position % 100 == 0:
            print(f'Processed {position}/{len(selected)} quality candidates')
    proposals.sort(key=lambda item: (-item['reviewPriority'], item['id'] or ''))
    return proposals


def write_outputs(output, proposals, model_path, manifest_path):
    output = Path(output)
    csv_output = output.with_suffix('.csv')
    if output.exists() or csv_output.exists():
        raise FileExistsError('Refusing to overwrite existing suggestion output')
    output.parent.mkdir(parents=True, exist_ok=True)
    record = {
        'schemaVersion': 1,
        'purpose': 'review assistance only; not ground truth or research evidence',
        'model': str(Path(model_path)),
        'manifest': str(Path(manifest_path)),
        'proposalCount': len(proposals),
        'proposals': proposals,
    }
    output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    with csv_output.open('w', newline='', encoding='utf-8-sig') as stream:
        fields = ['id', 'proposedLabel', 'confidence', 'reviewPriority', 'sourceLabel',
                  'candidateSplit', 'modelId', 'modelSha256', 'status', 'humanReviewRequired']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(proposals)
    return output, csv_output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'research/public-review-manifest.json')
    parser.add_argument('--model', type=Path, default=ROOT / 'www/model/best.onnx')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be a positive integer')
    if args.output.exists() or args.output.with_suffix('.csv').exists():
        parser.error('Output already exists; choose a new path')
    try:
        import onnxruntime as ort
        rows = json.loads(args.manifest.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            raise ValueError('Review manifest must be a JSON list')
        session = ort.InferenceSession(str(args.model), providers=['CPUExecutionProvider'])
        proposals = generate_suggestions(rows, ROOT, args.model, session, args.limit)
        json_output, csv_output = write_outputs(args.output, proposals, args.model, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f'Wrote {len(proposals)} unverified proposals to {json_output} and {csv_output}')
    print('A human reviewer must confirm or correct every proposal before import.')


if __name__ == '__main__':
    main()
