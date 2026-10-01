"""Export original bytes and a deduplicated review manifest; never invent labels.

The candidate partitions are NOT cleared for final evaluation until a reviewer
has supplied source-fruit/video groups and the validation gate passes.
"""
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]

def candidate_splits(groups, seed=42):
    strata = defaultdict(list)
    for group in groups:
        signature = tuple(sorted({(r['task'], r['label']) for r in group['records']}))
        strata[signature].append(group['pixelSha256'])
    assignments = {}
    for signature in sorted(strata):
        ids = sorted(strata[signature])
        random.Random(seed).shuffle(ids)
        train_end, val_end = int(len(ids) * .70), int(len(ids) * .85)
        for i, digest in enumerate(ids):
            assignments[digest] = 'train' if i < train_end else 'val' if i < val_end else 'test'
    return assignments

def main():
    groups = json.loads((ROOT / 'research/public-image-groups.json').read_text())
    assignments = candidate_splits(groups)
    selected = {}
    for group in groups:
        by_task = defaultdict(list)
        for record in group['records']:
            by_task[record['task']].append(record)
        for task, records in by_task.items():
            if len({r['label'] for r in records}) != 1:
                raise ValueError('Conflicting source labels for identical pixels')
            record = min(records, key=lambda r: r['row'])
            selected[(task, record['row'])] = (group['pixelSha256'], len(records))
    manifest, counts = [], defaultdict(Counter)
    for task in ('quality', 'maturity'):
        table = pq.read_table(ROOT / 'dataset/public' / task / 'original.parquet')
        names = json.loads(table.schema.metadata[b'huggingface'])['info']['features']['label']['names']
        for i, row in enumerate(table.to_pylist()):
            if (task, i) not in selected:
                continue
            digest, copies = selected[(task, i)]
            destination = ROOT / 'dataset/public/prepared' / task / (digest + '.jpg')
            destination.parent.mkdir(parents=True, exist_ok=True)
            data = row['image']['bytes']
            if destination.exists() and destination.read_bytes() != data:
                raise ValueError(f'Existing export differs: {destination}')
            if not destination.exists():
                destination.write_bytes(data)
            label = names[row['label']]
            split = assignments[digest]
            counts[task][split + ': ' + label] += 1
            manifest.append({
                'id': task + ':' + str(i), 'task': task, 'sourceRow': i,
                'sourceDataset': 'https://data.mendeley.com/datasets/2jpzbx8tm6/1',
                'image': destination.relative_to(ROOT).as_posix(),
                'fileSha256': hashlib.sha256(data).hexdigest(), 'pixelSha256': digest,
                'sourceLabel': label, 'originalCopies': copies,
                'candidateSplit': split,
                'reviewedSourceGroup': None, 'reviewedLabel': None,
                'reviewer': None, 'reviewedAt': None,
            })
    output = ROOT / 'research/public-review-manifest.json'
    if output.exists():
        old = json.loads(output.read_text())
        if any(row.get('reviewer') or row.get('reviewedSourceGroup') or row.get('reviewedLabel') for row in old):
            raise ValueError('Existing review work preserved. Refusing to overwrite reviewed manifest.')
    output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    summary = {'status': 'review_required_not_training_ready', 'exportedRecords': len(manifest),
               'counts': dict(counts), 'seed': 42,
               'notes': ['Identical pixels share one candidate partition across tasks.',
                         'Related but nonidentical photos may still cross partitions.',
                         'Reviewer/source groups and validated target labels are required before final evaluation.']}
    (ROOT / 'research/public-preparation.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    main()
