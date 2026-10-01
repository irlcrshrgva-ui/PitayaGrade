"""Measure visible symptom area from aligned binary masks, without making diagnoses."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.reviewed_segmentation import SYMPTOMS


def binary_mask(value):
    array = np.asarray(value)
    if array.ndim != 2 or not array.size or array.dtype.kind not in 'bui':
        raise ValueError('Masks must be nonempty two-dimensional binary integer arrays')
    if not np.isin(array, [0, 1, 255]).all():
        raise ValueError('Masks must contain only 0/1/255; threshold probabilities explicitly upstream')
    return array != 0


def measure_coverage(fruit_mask, regions):
    fruit = binary_mask(fruit_mask)
    denominator = int(fruit.sum())
    if denominator == 0:
        raise ValueError('Cannot measure coverage with an empty fruit mask')
    if not isinstance(regions, list):
        raise ValueError('Provide an explicit region list, including [] for no detected regions')
    classes = {}
    outside = np.zeros(fruit.shape, dtype=bool)
    for region in regions:
        if not isinstance(region, dict) or region.get('label') not in SYMPTOMS:
            raise ValueError('Unknown symptom class')
        mask = binary_mask(region.get('mask'))
        if mask.shape != fruit.shape:
            raise ValueError('Fruit and symptom masks must share dimensions and coordinate space')
        classes.setdefault(region['label'], np.zeros(fruit.shape, dtype=bool))
        classes[region['label']] |= mask & fruit
        outside |= mask & ~fruit
    combined = np.zeros(fruit.shape, dtype=bool)
    per_class = {}
    for label, mask in classes.items():
        combined |= mask
        count = int(mask.sum())
        per_class[label] = {'pixels': count, 'percentOfVisibleFruit': 100 * count / denominator}
    count = int(combined.sum())
    return {'fruitPixels': denominator, 'symptomPixels': count,
            'percentOfVisibleFruit': 100 * count / denominator,
            'perClass': per_class, 'symptomPixelsOutsideFruit': int(outside.sum()),
            'coordinateConvention': 'aligned upright masks of the same ROI',
            'limitations': ['Area describes the visible two-dimensional fruit mask, not total fruit surface.',
                            'Accuracy depends on both fruit and symptom masks; this is not a diagnosis.',
                            'Zero symptom area does not establish Healthy status.',
                            'Per-class percentages may overlap; total counts their union once.']}


def measure_files(manifest, output):
    manifest = Path(manifest).resolve()
    output = Path(output)
    if output.exists():
        raise FileExistsError('Choose a new coverage output file')
    raw = manifest.read_bytes()
    config = json.loads(raw)
    if not isinstance(config, dict) or config.get('coordinateSpace') != 'upright-roi':
        raise ValueError('Declare coordinateSpace as upright-roi after checking mask alignment')
    if not isinstance(config.get('regions'), list):
        raise ValueError('Explicit regions list required')
    provenance = []

    def read(path):
        if not isinstance(path, str) or not path:
            raise ValueError('Each mask needs a file path')
        file = (manifest.parent / path).resolve()
        data = file.read_bytes()
        from io import BytesIO
        with Image.open(BytesIO(data)) as image:
            if image.getexif().get(274, 1) != 1:
                raise ValueError('Masks must already be upright; do not rotate one mask independently')
            mask = np.array(image)
        provenance.append({'file': str(file), 'sha256': hashlib.sha256(data).hexdigest()})
        return mask

    fruit = read(config.get('fruitMask'))
    regions = []
    for region in config['regions']:
        if not isinstance(region, dict):
            raise ValueError('Region must specify label and mask file')
        regions.append({'label': region.get('label'), 'mask': read(region.get('mask'))})
    result = measure_coverage(fruit, regions)
    result['inputs'] = provenance
    result['manifestSha256'] = hashlib.sha256(raw).hexdigest()
    with output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = measure_files(args.manifest, args.output)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(f"Visible fruit mask coverage: {result['percentOfVisibleFruit']:.2f}%; not a diagnosis.")


if __name__ == '__main__':
    main()
