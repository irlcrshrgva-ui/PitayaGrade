"""Fail closed when research labels, grouping, or evidence are incomplete."""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))

from scripts.image_orientation import upright_digest
LABELS = {
    'manuscript-quality': {'Grade A', 'Grade B', 'Grade C', 'Reject'},
    'manuscript-detection': {'Dragon Fruit'},
    'manuscript-disease': {'Healthy', 'Anthracnose', 'Stem Canker', 'Soft Rot', 'Pest Damage', 'Sunburn', 'Fungal Spots'},
    'maturity': {'Mature Dragon Fruit', 'Immature Dragon Fruit'},
    'source-quality': {'Fresh Dragon Fruit', 'Defect Dragon Fruit'},
}

def validate(rows, target, root=ROOT, check_files=True, require_class_coverage=True):
    errors = []
    if not isinstance(rows, list) or not rows:
        return ['No records supplied']
    groups, pixels, coverage = defaultdict(set), defaultdict(set), defaultdict(set)
    upright_pixels = defaultdict(set)
    roi_sources = defaultdict(set)
    ids = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append('Invalid record: expected an object')
            continue
        if any(not isinstance(value, str) for key, value in row.items()
               if key in ('id', 'candidateSplit', 'reviewedLabel', 'reviewedSourceGroup',
                          'reviewer', 'reviewedAt', 'image', 'pixelSha256', 'fileSha256')
               and value is not None):
            errors.append('Invalid record: review fields must be strings')
            continue
        ident = row.get('id', '<missing id>')
        if not ident or ident == '<missing id>':
            errors.append('Missing record id')
        if ident in ids:
            errors.append(f'{ident}: duplicate record id')
        ids.add(ident)
        split = row.get('candidateSplit')
        if split not in ('train', 'val', 'test'):
            errors.append(f'{ident}: invalid split')
        if not all((row.get(k) or '').strip() for k in ('reviewedSourceGroup', 'reviewer', 'reviewedAt')):
            errors.append(f'{ident}: missing source-group review evidence')
        label = row.get('reviewedLabel')
        if label not in LABELS[target]:
            errors.append(f'{ident}: missing or incompatible reviewed label')
        coverage[split].add(label)
        if row.get('reviewedSourceGroup'):
            groups[row['reviewedSourceGroup']].add(split)
        roi_source = row.get('roiSourceId')
        if roi_source is not None:
            if not isinstance(roi_source, str) or not roi_source.strip():
                errors.append(f'{ident}: invalid ROI source identifier')
            else:
                roi_sources[roi_source.strip()].add(split)
        if not row.get('pixelSha256'):
            errors.append(f'{ident}: missing pixel hash')
        else:
            pixels[row['pixelSha256']].add(split)
        if check_files:
            if 'cropProvenance' in row:
                from scripts.verify_crop_provenance import verify_crop
                errors.extend(verify_crop(row, root))
            file = (root / (row.get('image') or '')).resolve()
            if not file.is_relative_to(root.resolve()) or not file.is_file():
                errors.append(f'{ident}: missing image or path outside workspace')
            elif hashlib.sha256(file.read_bytes()).hexdigest() != row.get('fileSha256'):
                errors.append(f'{ident}: image checksum mismatch')
            else:
                from PIL import Image
                try:
                    with Image.open(file) as image:
                        digest = hashlib.sha256(image.convert('RGB').tobytes()).hexdigest()
                        upright_pixels[upright_digest(image)].add(split)
                    if digest != row.get('pixelSha256'):
                        errors.append(f'{ident}: pixel checksum mismatch')
                except (OSError, ValueError) as error:
                    errors.append(f'{ident}: image cannot be decoded or oriented: {error}')
    for name, mapping in [('source group', groups), ('ROI source', roi_sources), ('identical image', pixels),
                          ('identical upright image', upright_pixels)]:
        for group, splits in mapping.items():
            if len(splits) > 1:
                errors.append(f'{name} {group}: crosses splits')
    for split in ('train', 'val', 'test') if require_class_coverage else ():
        missing = LABELS[target] - coverage[split]
        if missing:
            errors.append(f'{split}: missing classes: {", ".join(sorted(missing))}')
    return errors

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--target', choices=LABELS, required=True)
    args = parser.parse_args()
    errors = validate(json.loads(args.manifest.read_text(encoding='utf-8')), args.target)
    print(json.dumps({'ready': not errors, 'errorCount': len(errors), 'firstErrors': errors[:20]}, indent=2))
    raise SystemExit(1 if errors else 0)
