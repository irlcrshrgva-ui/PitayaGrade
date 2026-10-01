"""Audit downloaded original datasets without assigning new research labels."""
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
hashes = defaultdict(list)
report = {}
for task in ('quality', 'maturity'):
    table = pq.read_table(ROOT / 'dataset' / 'public' / task / 'original.parquet')
    metadata = json.loads(table.schema.metadata[b'huggingface'])
    names = metadata['info']['features']['label']['names']
    counts, dimensions, errors = Counter(), Counter(), []
    samples = Counter()
    for i, row in enumerate(table.to_pylist()):
        label = names[row['label']]
        counts[label] += 1
        data = row['image']['bytes']
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.load()
                dimensions[str(img.size)] += 1
                digest = hashlib.sha256(img.convert('RGB').tobytes()).hexdigest()
                hashes[digest].append({'task': task, 'row': i, 'label': label})
        except Exception as exc:
            errors.append({'row': i, 'error': str(exc)})
            continue
        if samples[label] < 3:
            folder = ROOT / 'dataset' / 'public' / task / 'review' / label
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f'row-{i}.jpg').write_bytes(data)
            samples[label] += 1
    report[task] = {'rows': table.num_rows, 'labels': counts, 'dimensions': dimensions, 'decodeErrors': errors}
duplicates = [group for group in hashes.values() if len(group) > 1]
report['duplicatePixelGroups'] = len(duplicates)
report['uniquePixelImages'] = len(hashes)
report['withinTaskConflictingLabelGroups'] = sum(
    any(len({r['label'] for r in group if r['task'] == task}) > 1 for task in ('quality', 'maturity'))
    for group in hashes.values()
)
report['duplicateExamples'] = duplicates[:20]
(ROOT / 'research' / 'public-image-groups.json').write_text(
    json.dumps([{'pixelSha256': digest, 'records': records} for digest, records in hashes.items()], indent=2) + '\n', encoding='utf-8')
report['limitations'] = [
    'Pixel-identical check only; source fruit/video identity and visual near-duplicates remain unverified.',
    'Original source labels retained; no Grade A/B/C or disease diagnoses inferred.',
    'Dataset train partition is a source container, not an approved research train/test split.'
]
(ROOT / 'research' / 'public-data-inspection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
