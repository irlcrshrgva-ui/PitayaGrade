"""Diagnostic: full-image and localized-crop recognition on fruit and lookalikes.

Tinted negatives are synthetic stress tests, not real-world testing or new
independent images. Caltech source pictures may overlap the deployed gate's
training set. This measures software changes, not field accuracy.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]


def tint_magenta(image):
    hsv = np.asarray(image.convert('HSV')).copy()
    colorful = hsv[:, :, 2] > 25
    hsv[:, :, 0][colorful] = 227  # about 320 degrees
    hsv[:, :, 1][colorful] = np.maximum(hsv[:, :, 1][colorful], 185)
    return Image.fromarray(hsv, 'HSV').convert('RGB')


def tensor(image, size, normalized=False):
    values = np.asarray(image.resize((size, size), Image.Resampling.BILINEAR), dtype=np.float32) / 255
    if normalized:
        values = (values - np.array([.485, .456, .406], dtype=np.float32)) / np.array([.229, .224, .225], dtype=np.float32)
    return values.transpose(2, 0, 1)[None].astype(np.float32)


def probability(session, image):
    logits = session.run(None, {session.get_inputs()[0].name: tensor(image, 160, True)})[0][0]
    values = np.exp(logits - np.max(logits))
    return float(values[1] / values.sum())


def detect_crop(detector, image):
    output = detector.run(None, {detector.get_inputs()[0].name: tensor(image, 640)})[0][0]
    scores = output[4:].max(axis=0)
    index = int(scores.argmax())
    cx, cy, width, height = output[:4, index] / 640
    left, top, right, bottom = max(0., float(cx - width / 2)), max(0., float(cy - height / 2)), min(1., float(cx + width / 2)), min(1., float(cy + height / 2))
    if not np.isfinite([left, top, right, bottom]).all() or right <= left or bottom <= top:
        return float(scores[index]), None
    import math
    x, y = math.floor(max(0, left - .04) * image.width), math.floor(max(0, top - .04) * image.height)
    sw = max(1, math.ceil((min(1, right + .04) - max(0, left - .04)) * image.width))
    sh = max(1, math.ceil((min(1, bottom + .04) - max(0, top - .04)) * image.height))
    return float(scores[index]), image.crop((x, y, x + sw, y + sh))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gate', type=Path, default=ROOT / 'www/model/gate/dragonfruit-presence-gate.onnx')
    parser.add_argument('--threshold', type=float, default=.5)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite an existing diagnostic')
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    gate = ort.InferenceSession(str(args.gate), sess_options=options, providers=['CPUExecutionProvider'])
    detector = ort.InferenceSession(str(ROOT / 'www/model/best.onnx'), sess_options=options, providers=['CPUExecutionProvider'])
    quality = json.loads((ROOT / 'local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json').read_text())
    samples = [(row['image'], ROOT / row['image'], 1, 'original', 'frozen-quality-test')
               for row in quality if row['candidateSplit'] == 'test']
    base = ROOT / 'dataset/nonfruit/caltech101/caltech101/101_ObjectCategories'
    for category in ['soccer_ball', 'strawberry', 'sunflower', 'Faces', 'Faces_easy', 'brain', 'cup', 'headphone', 'watch', 'camera']:
        paths = sorted((base / category).glob('*.jpg'), key=lambda path: hashlib.sha256(path.name.encode()).hexdigest())
        for path in paths[:40 if category == 'soccer_ball' else 15]:
            for variant in ('original', 'magenta-tinted'):
                samples.append((f'{category}/{path.name}/{variant}', path, 0, variant, category))
    rows = []
    for number, (identity, path, target, variant, category) in enumerate(samples):
        with Image.open(path) as opened:
            image = ImageOps.exif_transpose(opened).convert('RGB')
        if variant == 'magenta-tinted':
            image = tint_magenta(image)
        full = probability(gate, image)
        detection_score, crop = detect_crop(detector, image) if full >= args.threshold else (0., None)
        localized = probability(gate, crop) if crop and detection_score >= .5 else None
        rows.append({'id': identity, 'target': target, 'variant': variant, 'category': category,
                     'sourceFileSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'fullProbability': full, 'detectorScore': detection_score, 'cropProbability': localized,
                     'oldModelChecksPass': full >= args.threshold and detection_score >= .5,
                     'newModelChecksPass': full >= args.threshold and detection_score >= .5 and localized is not None and localized >= args.threshold})
        if (number + 1) % 100 == 0:
            print(f'Diagnosed {number + 1}/{len(samples)}', flush=True)
    summary = {}
    for category in sorted({row['category'] for row in rows}):
        subset = [row for row in rows if row['category'] == category]
        summary[category] = {'count': len(subset), 'oldAccepted': sum(row['oldModelChecksPass'] for row in subset),
                             'newAccepted': sum(row['newModelChecksPass'] for row in subset)}
    report = {'status': 'object-rejection-diagnostic-not-field-accuracy',
              'gateSha256': hashlib.sha256(args.gate.read_bytes()).hexdigest(),
              'detectorSha256': hashlib.sha256((ROOT / 'www/model/best.onnx').read_bytes()).hexdigest(),
              'positiveManifestSha256': hashlib.sha256((ROOT / 'local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json').read_bytes()).hexdigest(),
              'presenceThreshold': args.threshold, 'detectorThreshold': .5,
              'limitations': ['Negatives may overlap prior training', 'Tinted samples are synthetic',
                              'Browser canvas and Pillow interpolation may differ',
                              'Model checks only; subsequent app color/exposure checks can reject more images'],
              'summary': summary, 'rows': rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
