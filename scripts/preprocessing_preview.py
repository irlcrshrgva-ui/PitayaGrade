"""Preview explicit research preprocessing settings; never modify training inputs."""
import argparse
import hashlib
import json
import math
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from scripts.image_orientation import upright_rgb


def validate_config(config):
    required = {'hsvRanges', 'grabcutIterations', 'claheClipLimit', 'claheGrid',
                'laplacianThreshold', 'seed'}
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError('Config must contain exactly: ' + ', '.join(sorted(required)))
    ranges = config['hsvRanges']
    if not isinstance(ranges, list) or not ranges:
        raise ValueError('hsvRanges must contain explicit lower/upper HSV bounds')
    for bounds in ranges:
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError('Each HSV range requires lower and upper triples')
        for values in bounds:
            if (not isinstance(values, list) or len(values) != 3 or
                    any(type(v) is not int or not 0 <= v <= limit
                        for v, limit in zip(values, (179, 255, 255)))):
                raise ValueError('HSV bounds must be integers within H=0..179, S/V=0..255')
        if any(low > high for low, high in zip(*bounds)):
            raise ValueError('HSV lower bounds must not exceed upper bounds; split hue wrap into two ranges')
    for key in ('claheClipLimit', 'laplacianThreshold'):
        value = config[key]
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError(f'{key} must be finite and nonnegative')
    if config['claheClipLimit'] == 0:
        raise ValueError('claheClipLimit must be positive')
    grid = config['claheGrid']
    if not isinstance(grid, list) or len(grid) != 2 or any(type(n) is not int or n < 1 for n in grid):
        raise ValueError('claheGrid must contain two positive integers')
    if type(config['grabcutIterations']) is not int or config['grabcutIterations'] < 1:
        raise ValueError('grabcutIterations must be a positive integer')
    if type(config['seed']) is not int or not 0 <= config['seed'] < 2**31:
        raise ValueError('seed must be an integer in 0..2147483647')


def process(image, config):
    validate_config(config)
    rgb = np.array(upright_rgb(image), dtype=np.uint8)
    if min(rgb.shape[:2]) < 3:
        raise ValueError('Image must be at least 3x3 pixels')
    if any(n > dimension for n, dimension in zip(config['claheGrid'], (rgb.shape[1], rgb.shape[0]))):
        raise ValueError('CLAHE grid cannot exceed image dimensions')
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    seed_mask = np.zeros(rgb.shape[:2], dtype=np.uint8)
    for lower, upper in config['hsvRanges']:
        seed_mask |= cv2.inRange(hsv, np.array(lower, dtype=np.uint8), np.array(upper, dtype=np.uint8))
    # Both classes need enough samples for GrabCut's five-component color models.
    foreground = seed_mask > 0
    if np.count_nonzero(foreground) < 5 or np.count_nonzero(~foreground) < 5:
        raise ValueError('HSV initialization needs at least five foreground and five background pixels')
    mask = np.where(foreground, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
    cv2.setRNGSeed(config['seed'])
    cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mask, None,
                np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
                config['grabcutIterations'], cv2.GC_INIT_WITH_MASK)
    fruit = (mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)
    if not fruit.any() or fruit.all():
        raise ValueError('GrabCut produced an empty or full mask; inspect settings and source image')
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    lab[:, :, 0] = cv2.createCLAHE(clipLimit=config['claheClipLimit'],
                                 tileGridSize=tuple(config['claheGrid'])).apply(lab[:, :, 0])
    corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    # Measure within the mask interior to avoid artificial segmentation edges.
    interior = cv2.erode(fruit.astype(np.uint8), np.ones((3, 3), np.uint8),
                         borderType=cv2.BORDER_CONSTANT, borderValue=0).astype(bool)
    if not interior.any():
        raise ValueError('Fruit mask has no interior pixels for the Laplacian statistic')
    laplacian = cv2.Laplacian(cv2.cvtColor(corrected, cv2.COLOR_RGB2GRAY), cv2.CV_64F)
    variance = float(laplacian[interior].var())
    blurred = variance > config['laplacianThreshold']
    output = cv2.GaussianBlur(corrected, (3, 3), 0) if blurred else corrected.copy()
    output[~fruit] = 0
    corrected[~fruit] = 0
    return {'upright': rgb, 'hsv-seed': seed_mask, 'fruit-mask': fruit.astype(np.uint8) * 255,
            'lighting': corrected, 'processed': output}, {
                'laplacianVariance': variance, 'blurApplied': blurred,
                'foregroundFraction': float(fruit.mean()), 'size': [rgb.shape[1], rgb.shape[0]],
            }


def preview(image_path, config, output_dir):
    validate_config(config)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError('Choose a new output directory')
    data = Path(image_path).read_bytes()
    with Image.open(BytesIO(data)) as image:
        images, measurements = process(image, config)
    output_dir.mkdir(parents=True, exist_ok=False)
    hashes = {}
    for name, array in images.items():
        path = output_dir / (name + '.png')
        Image.fromarray(array).save(path)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    record = {'purpose': 'research-preview-only', 'source': str(Path(image_path).resolve()),
              'sourceSha256': hashlib.sha256(data).hexdigest(), 'config': config,
              'opencv': cv2.__version__, 'numpy': np.__version__, 'measurements': measurements,
              'outputHashes': hashes,
              'order': ['EXIF upright RGB', 'HSV-seeded GrabCut', 'LAB luminance CLAHE',
                        'interior Laplacian variance', 'conditional 3x3 Gaussian blur', 'mask background'],
              'limitations': ['Settings and masks require research review; not ground-truth fruit or disease masks.',
                              'Laplacian variance also responds to texture and edges; it does not establish noise.',
                              'Native-size preview only; no model resize/normalization or training integration.',
                              'Orientation first and native-size processing are explicit preview conventions, not full manuscript alignment.']}
    (output_dir / 'preview.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        preview(args.image, json.loads(args.config.read_text(encoding='utf-8')), args.output_dir)
    except (ValueError, OSError, cv2.error) as error:
        parser.error(str(error))
    print(f'Research preview saved: {args.output_dir}. Settings are not validated for training.')


if __name__ == '__main__':
    main()
