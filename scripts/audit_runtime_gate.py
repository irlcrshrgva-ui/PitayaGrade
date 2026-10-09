"""Audit the browser detector and visual gate against local dragon-fruit photos."""
import argparse
import colorsys
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'www/model/best.onnx'
CLASSES = ['Grade A', 'Grade B', 'Grade C', 'Reject']


def infer(session, path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        model_image = image.resize((640, 640), Image.Resampling.BILINEAR)
        runtime_image = image.resize((128, 128), Image.Resampling.BILINEAR)
    pixels = np.asarray(model_image, dtype=np.float32) / 255.0
    tensor = np.transpose(pixels, (2, 0, 1))[None, ...]
    output = session.run(None, {session.get_inputs()[0].name: tensor})[0]
    scores = output[0, 4:8, :]
    class_index, detection_index = np.unravel_index(int(np.argmax(scores)), scores.shape)
    confidence = float(scores[class_index, detection_index])
    cx, cy, width, height = (float(output[0, channel, detection_index]) for channel in range(4))
    box = (
        max(0.0, (cx - width / 2) / 640),
        max(0.0, (cy - height / 2) / 640),
        min(1.0, (cx + width / 2) / 640),
        min(1.0, (cy + height / 2) / 640),
    )
    return CLASSES[class_index], confidence, box, np.asarray(runtime_image)


def gate_metrics(pixels, box, padding=0.0):
    left, top, right, bottom = box
    width, height = right - left, bottom - top
    left = max(0.0, left - width * padding)
    top = max(0.0, top - height * padding)
    right = min(1.0, right + width * padding)
    bottom = min(1.0, bottom + height * padding)
    gx0, gy0 = max(0, int(left * 8)), max(0, int(top * 8))
    gx1, gy1 = min(8, int(np.ceil(right * 8))), min(8, int(np.ceil(bottom * 8)))
    roi = pixels[gy0 * 16:gy1 * 16, gx0 * 16:gx1 * 16, :]
    pink = green = magenta = 0
    for red, green_channel, blue in roi.reshape(-1, 3):
        hue, saturation, value = colorsys.rgb_to_hsv(red / 255, green_channel / 255, blue / 255)
        hue *= 360
        saturation *= 100
        value *= 100
        if (hue >= 270 or hue <= 30) and saturation > 15 and value > 25:
            pink += 1
            if hue >= 300 or hue <= 10:
                magenta += 1
        elif 55 <= hue <= 175 and saturation > 15 and value > 20:
            green += 1
    total = max(1, roi.shape[0] * roi.shape[1])
    return pink / total, green / total, magenta / total, (gx0, gy0, gx1, gy1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    candidates = sorted((ROOT / 'dataset/public/quality/review').rglob('*.jpg'))
    candidates += sorted((ROOT / 'dataset_prepared').rglob('*.jpg'))
    if args.sample and len(candidates) > args.limit:
        indexes = np.linspace(0, len(candidates) - 1, args.limit, dtype=int)
        candidates = [candidates[index] for index in indexes]
    session = ort.InferenceSession(str(MODEL), providers=['CPUExecutionProvider'])
    accepted = confidence_passes = green_failures = fixed_accepted = fixed_confidence_passes = 0
    for path in candidates[:args.limit]:
        label, confidence, box, pixels = infer(session, path)
        pink, green, magenta, cells = gate_metrics(pixels, box)
        confidence_ok = confidence >= 0.65
        gate_ok = pink >= 0.06 and green >= 0.02 and 1.5 <= pink / max(green, 1e-9) <= 25
        fixed_confidence_ok = confidence >= 0.50
        fixed_gate_ok = pink >= 0.06 and (green >= 0.01 or magenta >= 0.08)
        confidence_passes += confidence_ok
        accepted += confidence_ok and gate_ok
        fixed_confidence_passes += fixed_confidence_ok
        fixed_accepted += fixed_confidence_ok and fixed_gate_ok
        green_failures += confidence_ok and pink >= 0.06 and green < 0.02
        print(f'{path.relative_to(ROOT)}\t{label}\t{confidence:.3f}\tpink={pink:.3f}\tgreen={green:.3f}\tmagenta={magenta:.3f}\tcells={cells}\taccepted={confidence_ok and gate_ok}')
    print(f'SUMMARY images={min(args.limit, len(candidates))} old_confidence_passes={confidence_passes} '
          f'old_accepted={accepted} green_only_failures={green_failures} '
          f'fixed_confidence_passes={fixed_confidence_passes} fixed_accepted={fixed_accepted}')


if __name__ == '__main__':
    main()
