"""Create deterministic, leakage-safe splits from a completed review manifest."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

SPLITS = ('train', 'val', 'test')


def reconcile_splits(rows):
    """Keep linked records together while changing as few split values as possible."""
    output = [dict(row) for row in rows]
    parent = list(range(len(output)))

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left, right):
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    linked = {}
    for index, row in enumerate(output):
        if row.get('candidateSplit') not in SPLITS:
            raise ValueError(f'{row.get("id", index)}: invalid candidate split')
        task = str(row.get('task') or '').strip()
        group = str(row.get('reviewedSourceGroup') or '').strip()
        if not task or not group:
            raise ValueError(f'{row.get("id", index)}: missing task or reviewed source group')
        keys = [('group', task, group)]
        for field in ('pixelSha256', 'roiSourceId'):
            value = str(row.get(field) or '').strip()
            if value:
                keys.append((field, task, value))
        for key in keys:
            previous = linked.setdefault(key, index)
            union(index, previous)

    components = defaultdict(list)
    for index in range(len(output)):
        components[find(index)].append(index)

    moved = 0
    changed_components = 0
    for indices in components.values():
        counts = Counter(output[index]['candidateSplit'] for index in indices)
        if len(counts) == 1:
            continue
        changed_components += 1
        best_count = max(counts.values())
        tied = sorted(split for split, count in counts.items() if count == best_count)
        if len(tied) == 1:
            selected = tied[0]
        else:
            identity = '\n'.join(sorted(str(output[index].get('id')) for index in indices))
            selected = tied[int(hashlib.sha256(identity.encode()).hexdigest(), 16) % len(tied)]
        for index in indices:
            if output[index]['candidateSplit'] != selected:
                output[index]['candidateSplit'] = selected
                moved += 1

    return output, {'linkedComponentsChanged': changed_components, 'rowsMoved': moved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'Refusing to overwrite {args.output}')
    try:
        rows = json.loads(args.manifest.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or not rows:
            raise ValueError('Manifest must be a non-empty JSON array')
        reconciled, summary = reconcile_splits(rows)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(reconciled, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({**summary, 'rows': len(reconciled), 'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
