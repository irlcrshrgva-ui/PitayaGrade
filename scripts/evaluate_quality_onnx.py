"""Run a quality ONNX candidate on the frozen held-out manifest and export predictions."""
import argparse
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.image_orientation import load_upright_rgb
from scripts.reviewed_training import ROOT, read_reviewed_manifest, write_prediction_csv

CLASS_NAMES = ['Grade A', 'Grade B', 'Grade C', 'Reject']
MODEL_IDS = {'mobilenetv2-quality', 'resnet50-quality', 'efficientnet-b3-quality'}
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preprocess(path, size=224):
    image = load_upright_rgb(path).resize((size, size), Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - MEAN) / STD
    return np.transpose(array, (2, 0, 1))[None].astype(np.float32, copy=False)


def probabilities(values):
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    if values.size != len(CLASS_NAMES) or not np.isfinite(values).all():
        raise ValueError('Quality model must return four finite logits')
    shifted = values - values.max()
    exponent = np.exp(shifted)
    return exponent / exponent.sum()


def evaluate(rows, session, root=ROOT, size=224):
    test_rows = sorted((row for row in rows if row.get('candidateSplit') == 'test'), key=lambda row: row['id'])
    if not test_rows:
        raise ValueError('Reviewed manifest contains no held-out quality rows')
    inputs, outputs = session.get_inputs(), session.get_outputs()
    if len(inputs) != 1 or list(inputs[0].shape) != [1, 3, size, size]:
        raise ValueError(f'Unexpected ONNX input contract: {[item.shape for item in inputs]}')
    if len(outputs) != 1 or list(outputs[0].shape) != [1, len(CLASS_NAMES)]:
        raise ValueError(f'Unexpected ONNX output contract: {[item.shape for item in outputs]}')
    name = inputs[0].name
    sample_ids, labels, confidences, latencies = [], [], [], []
    # Warm-up is excluded from evidence latency.
    session.run(None, {name: preprocess(Path(root) / test_rows[0]['image'], size)})
    for row in test_rows:
        tensor = preprocess(Path(root) / row['image'], size)
        started = time.perf_counter()
        result = session.run(None, {name: tensor})[0]
        latency = (time.perf_counter() - started) * 1000
        scores = probabilities(result)
        predicted = int(np.argmax(scores))
        sample_ids.append(row['id'])
        labels.append(CLASS_NAMES[predicted])
        confidences.append(float(scores[predicted]))
        latencies.append(latency)
    return sample_ids, labels, confidences, latencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--model-id', required=True, choices=sorted(MODEL_IDS))
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report_path = args.output.with_suffix('.evaluation.json')
    if args.output.exists() or report_path.exists():
        parser.error('Output evidence already exists; choose a new path')
    try:
        rows = read_reviewed_manifest(args.manifest)
        import onnxruntime as ort
        session = ort.InferenceSession(str(args.model), providers=['CPUExecutionProvider'])
        sample_ids, labels, confidences, latencies = evaluate(rows, session)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_prediction_csv(args.output, args.model_id, sample_ids, labels, confidences, latencies)
        ordered = sorted(latencies)
        report = {
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'status': 'held-out-onnx-predictions',
            'modelId': args.model_id,
            'model': {'path': str(args.model), 'sha256': sha256(args.model)},
            'manifest': {'path': str(args.manifest), 'sha256': sha256(args.manifest)},
            'runtime': {'name': 'onnxruntime', 'version': ort.__version__,
                        'provider': session.get_providers()[0]},
            'preprocessing': {'orientation': 'EXIF upright RGB', 'size': 224,
                              'resize': 'Pillow bilinear', 'scale': '0..1',
                              'mean': MEAN.tolist(), 'std': STD.tolist()},
            'classOrder': CLASS_NAMES,
            'sampleCount': len(sample_ids),
            'meanLatencyMs': sum(latencies) / len(latencies),
            'p95LatencyMs': ordered[max(0, math.ceil(.95 * len(ordered)) - 1)],
            'predictions': {'path': str(args.output), 'sha256': sha256(args.output)},
        }
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, ImportError) as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
