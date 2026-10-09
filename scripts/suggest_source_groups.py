"""Suggest visually similar source groups for human review; never changes labels."""

import argparse
import csv
import json
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]


def _hash_bits(values):
    result = 0
    for value in values:
        result = (result << 1) | int(bool(value))
    return result


def _pixels(image):
    getter = getattr(image, 'get_flattened_data', None)
    return list(getter() if getter else image.getdata())


def perceptual_hashes(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('L')
        difference = image.resize((9, 8), Image.Resampling.LANCZOS)
        pixels = _pixels(difference)
        dhash = _hash_bits(
            pixels[row * 9 + column] > pixels[row * 9 + column + 1]
            for row in range(8) for column in range(8)
        )
        average_image = image.resize((8, 8), Image.Resampling.LANCZOS)
        average_pixels = _pixels(average_image)
        mean = sum(average_pixels) / len(average_pixels)
        ahash = _hash_bits(value >= mean for value in average_pixels)
    return dhash, ahash


def distance(left, right):
    return (left ^ right).bit_count()


class UnionFind:
    def __init__(self, size):
        self.parent = list(range(size))

    def find(self, item):
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def join(self, left, right):
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def safe_path(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f'Image path escapes project root: {relative}')
    if not candidate.is_file():
        raise FileNotFoundError(f'Missing image: {relative}')
    return candidate


def suggest(rows, root=ROOT, dhash_threshold=6, ahash_threshold=8):
    fingerprints = []
    for position, row in enumerate(rows, 1):
        dhash, ahash = perceptual_hashes(safe_path(root, row.get('image', '')))
        fingerprints.append((dhash, ahash))
        if position % 250 == 0:
            print(f'Hashed {position}/{len(rows)} review images')

    groups = UnionFind(len(rows))
    pairs = []
    for left in range(len(rows)):
        left_dhash, left_ahash = fingerprints[left]
        for right in range(left + 1, len(rows)):
            right_dhash, right_ahash = fingerprints[right]
            d_distance = distance(left_dhash, right_dhash)
            if d_distance > dhash_threshold:
                continue
            a_distance = distance(left_ahash, right_ahash)
            if a_distance > ahash_threshold:
                continue
            groups.join(left, right)
            pairs.append({
                'leftId': rows[left].get('id'),
                'rightId': rows[right].get('id'),
                'dHashDistance': d_distance,
                'aHashDistance': a_distance,
            })

    members = {}
    for index in range(len(rows)):
        members.setdefault(groups.find(index), []).append(index)

    suggestions = []
    row_assignments = []
    group_number = 0
    for indices in sorted(members.values(), key=lambda value: rows[value[0]].get('id', '')):
        if len(indices) < 2:
            continue
        group_number += 1
        group_id = f'candidate-source-{group_number:04d}'
        splits = sorted({rows[index].get('candidateSplit') for index in indices})
        record = {
            'suggestedSourceGroup': group_id,
            'humanReviewRequired': True,
            'crossesCandidateSplits': len(splits) > 1,
            'candidateSplits': splits,
            'members': [],
        }
        for index in indices:
            row = rows[index]
            member = {
                'id': row.get('id'),
                'task': row.get('task'),
                'candidateSplit': row.get('candidateSplit'),
                'sourceLabel': row.get('sourceLabel'),
                'image': row.get('image'),
            }
            record['members'].append(member)
            row_assignments.append({
                **member,
                'suggestedSourceGroup': group_id,
                'crossesCandidateSplits': record['crossesCandidateSplits'],
                'status': 'unverified-source-group-suggestion',
            })
        suggestions.append(record)

    return {
        'schemaVersion': 1,
        'purpose': 'review assistance only; perceptual similarity is not source identity',
        'thresholds': {'dHashDistance': dhash_threshold, 'aHashDistance': ahash_threshold},
        'manifestRows': len(rows),
        'candidatePairCount': len(pairs),
        'candidateGroupCount': len(suggestions),
        'crossSplitGroupCount': sum(group['crossesCandidateSplits'] for group in suggestions),
        'groups': suggestions,
        'pairs': pairs,
    }, row_assignments


def write_outputs(output, report, assignments):
    output = Path(output)
    csv_output = output.with_suffix('.csv')
    if output.exists() or csv_output.exists():
        raise FileExistsError('Refusing to overwrite existing source-group suggestions')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    fields = ['id', 'task', 'candidateSplit', 'sourceLabel', 'image',
              'suggestedSourceGroup', 'crossesCandidateSplits', 'status']
    with csv_output.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(assignments)
    return output, csv_output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path,
                        default=ROOT / 'research/public-review-manifest.json')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--dhash-threshold', type=int, default=6)
    parser.add_argument('--ahash-threshold', type=int, default=8)
    args = parser.parse_args(argv)
    if not 0 <= args.dhash_threshold <= 64 or not 0 <= args.ahash_threshold <= 64:
        parser.error('Hash thresholds must be between 0 and 64')
    try:
        rows = json.loads(args.manifest.read_text(encoding='utf-8'))
        if not isinstance(rows, list) or not rows:
            raise ValueError('Manifest must be a non-empty JSON list')
        report, assignments = suggest(rows, ROOT, args.dhash_threshold, args.ahash_threshold)
        json_output, csv_output = write_outputs(args.output, report, assignments)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps({key: report[key] for key in
                      ('manifestRows', 'candidatePairCount', 'candidateGroupCount',
                       'crossSplitGroupCount')}, indent=2))
    print(f'Wrote review-only suggestions to {json_output} and {csv_output}')


if __name__ == '__main__':
    main()

