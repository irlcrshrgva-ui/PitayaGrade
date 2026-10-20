"""Create deterministic, duplicate-grouped image-classification partitions."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageOps

from scripts.mendeley_disease import file_hash

# Broad publisher categories stay broad. No invented pathogen diagnoses or masks.
LABELS = {
    'kpsywfwkrf': {
        'Black_Rot': 'fruit_black_rot', 'Fungi': 'fruit_fungi', 'Healthy_fruit': 'healthy_fruit',
        'Healthy_leaf': 'healthy_stem_leaf', 'Rust': 'stem_rust', 'Scab': 'stem_scab',
        'Stem_Canker': 'stem_canker', 'Sunburn': 'stem_sunburn'},
    'cfchfdpfw5': {'Good fruit': 'fruit_good_source', 'Bad fruit': 'fruit_bad_unspecified',
                   'Good leaf': 'leaf_good_source', 'Bad leaf': 'leaf_bad_unspecified'}}


def signature(path):
    with Image.open(path) as image:
        rgb = ImageOps.exif_transpose(image).convert('RGB')
        pixel_hash = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
        pixels = np.asarray(rgb.convert('L').resize((9, 8), Image.Resampling.LANCZOS))
        bits = pixels[:, 1:] > pixels[:, :-1]
        dhash = int.from_bytes(np.packbits(bits).tobytes(), 'big')
        return pixel_hash, dhash


def prepare(root, output, mapping, seed=42):
    if output.exists():
        raise FileExistsError('Choose a new manifest path')
    records = json.loads((root / 'source-files.json').read_text())
    archive_root = root / 'cfchfdpfw5' / 'extracted' / 'Dragon fruit and leaf'
    if not archive_root.exists():
        raise ValueError('First dataset archive has not been extracted')
    for path in sorted(archive_root.rglob('*')):
        if path.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.bmp', '.webp'} or '__MACOSX' in path.parts:
            continue
        label = path.parent.name
        records.append({'dataset': 'cfchfdpfw5', 'version': 1, 'sourceLabel': label,
                        'path': path.relative_to(root).as_posix()})
    unknown = sorted({(r['dataset'], r['sourceLabel']) for r in records
                      if r['sourceLabel'] not in mapping.get(r['dataset'], {})})
    if unknown:
        raise ValueError('Unmapped publisher folders (supply explicit JSON mapping): ' + repr(unknown))
    parents = list(range(len(records)))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    def union(i, j):
        parents[find(i)] = find(j)

    hashes = {}
    pixels_seen = {}
    def inspect(row):
        path = root / row['path']
        actual = file_hash(path)
        if row.get('sha256', actual) != actual:
            raise ValueError('Source checksum mismatch: ' + str(path))
        pixel, dhash = signature(path)
        return actual, pixel, dhash

    # Five 13-bit bands ensure candidates sharing a <=4-bit dHash distance meet.
    bands = defaultdict(list)
    def inspections():
        with ThreadPoolExecutor(max_workers=8) as pool:
            yield from pool.map(inspect, records)

    inspected = inspections()
    for i, (row, (actual, pixel, dhash)) in enumerate(zip(records, inspected)):
        row['sha256'] = actual
        row['label'] = mapping[row['dataset']][row['sourceLabel']]
        row['task'] = 'disease' if row['dataset'] == 'kpsywfwkrf' else 'health'
        row['pixelSha256'] = pixel
        row['dhash'] = f'{dhash:016x}'
        for key, seen in ((row['sha256'], hashes), (pixel, pixels_seen)):
            if key in seen:
                union(i, seen[key])
            seen[key] = i
        candidates = set()
        for band in range(5):
            key = (band, (dhash >> (13 * band)) & 8191)
            candidates.update(bands[key])
            bands[key].append(i)
        for j in candidates:
            if (dhash ^ int(records[j]['dhash'], 16)).bit_count() <= 4:
                union(i, j)
        if i % 500 == 0:
            print('Inspected', i, flush=True)
    groups = defaultdict(list)
    for i, row in enumerate(records):
        groups[find(i)].append(row)
    by_class = defaultdict(list)
    quarantined = []
    duplicates = []
    for group in groups.values():
        group_id = min(r['sha256'] for r in group)
        if len({r['label'] for r in group}) != 1:
            quarantined.extend(dict(r, reason='conflicting labels in duplicate group', group=group_id) for r in group)
            continue
        # Keep one representative per near-duplicate group, retaining every origin.
        chosen = dict(sorted(group, key=lambda r: r['path'])[0])
        chosen['group'] = group_id
        chosen['origins'] = [{k: r[k] for k in ('dataset', 'sourceLabel', 'path', 'sha256')} for r in group]
        duplicates.extend(r for r in group if r['path'] != chosen['path'])
        by_class[chosen['label']].append(chosen)
    selected = []
    rng = random.Random(seed)
    for label, rows in sorted(by_class.items()):
        rows.sort(key=lambda r: r['group'])
        rng.shuffle(rows)
        if len(rows) < 10:
            raise ValueError('Too few independent groups for ' + label)
        n_val = max(1, round(len(rows) * .15))
        n_test = max(1, round(len(rows) * .15))
        for index, row in enumerate(rows):
            row['split'] = 'validation' if index < n_val else 'test' if index < n_val + n_test else 'train'
            selected.append(row)
    result = {'schemaVersion': 1, 'seed': seed, 'ratios': [0.70, 0.15, 0.15], 'mapping': mapping,
              'root': str(root.resolve()), 'rows': selected, 'quarantined': quarantined,
              'removedDuplicates': len(duplicates), 'counts': dict(Counter(r['split'] + '/' + r['label'] for r in selected)),
              'limitations': ['dHash distance <=4 plus decoded pixel and file hashes group visual duplicates across both sources.',
                              'No plant/session IDs supplied; visually distinct photos of one plant may remain across splits.',
                              'Publisher image-level labels are not independently verified diagnoses, grades, or segmentation masks.',
                              'The first archive has only Good/Bad fruit/leaf folders. Its health task stays separate from named conditions.']}
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + '.partial')
    with partial.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    # Publish only a complete manifest; hard-link creation refuses existing outputs.
    os.link(partial, output)
    partial.unlink()
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mapping', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.root.resolve(), args.output, json.loads(args.mapping.read_text()))
    print(json.dumps(result['counts'], indent=2))
