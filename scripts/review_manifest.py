"""Export a review worksheet and safely merge completed reviews into a new manifest."""
import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

from scripts.summarize_model_evaluation import LABELS

FIELDS = ['id', 'image', 'candidateSplit', 'sourceDataset', 'sourceLabel',
          'reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt']
REVIEW_FIELDS = ['reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt']


def load_manifest(path):
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError('Manifest must be a non-empty JSON array of objects')
    ids = [row.get('id') for row in rows]
    if any(not isinstance(ident, str) or not ident for ident in ids) or len(ids) != len(set(ids)):
        raise ValueError('Manifest IDs must be non-empty and unique')
    return rows


def export_reviews(manifest, output, task=None):
    selected = [row for row in manifest if task is None or row.get('task') == task]
    if not selected:
        raise ValueError('No records match the selected task')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', newline='', encoding='utf-8-sig') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(selected)
    return len(selected)


def parse_reviews(path, allowed_labels):
    reviews = {}
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        missing = set(['id', *REVIEW_FIELDS]) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f'Review CSV is missing columns: {", ".join(sorted(missing))}')
        for line, row in enumerate(reader, 2):
            ident = (row.get('id') or '').strip()
            if not ident:
                raise ValueError(f'Line {line}: missing id')
            if ident in reviews:
                raise ValueError(f'Line {line}: duplicate id {ident}')
            values = {field: (row.get(field) or '').strip() for field in REVIEW_FIELDS}
            supplied = [bool(values[field]) for field in REVIEW_FIELDS]
            if any(supplied) and not all(supplied):
                raise ValueError(f'Line {line}: reviewed fields must be all filled or all blank')
            if all(supplied):
                if values['reviewedLabel'] not in allowed_labels:
                    raise ValueError(f'Line {line}: incompatible reviewed label {values["reviewedLabel"]!r}')
                try:
                    parsed = datetime.fromisoformat(values['reviewedAt'].replace('Z', '+00:00'))
                except ValueError as error:
                    raise ValueError(f'Line {line}: reviewedAt must be ISO 8601') from error
                if parsed.tzinfo is None:
                    raise ValueError(f'Line {line}: reviewedAt must include a timezone')
            reviews[ident] = values
    if not reviews:
        raise ValueError('Review CSV contains no records')
    return reviews


def merge_reviews(manifest, reviews):
    known = {row['id'] for row in manifest}
    unknown = sorted(set(reviews) - known)
    if unknown:
        raise ValueError(f'Review CSV contains unknown IDs: {unknown[:5]}')
    output = []
    completed = 0
    for row in manifest:
        merged = dict(row)
        review = reviews.get(row['id'])
        if review and all(review.values()):
            for field in REVIEW_FIELDS:
                current = merged.get(field)
                if current not in (None, '', review[field]):
                    raise ValueError(f'{row["id"]}: refusing to overwrite existing {field}')
                merged[field] = review[field]
            completed += 1
        output.append(merged)
    return output, completed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='command', required=True)
    export_parser = subparsers.add_parser('export', help='Create an Excel-friendly review worksheet')
    export_parser.add_argument('manifest', type=Path)
    export_parser.add_argument('output', type=Path)
    export_parser.add_argument('--task', choices=['quality', 'disease', 'maturity'])
    import_parser = subparsers.add_parser('import', help='Merge reviewed rows into a new manifest')
    import_parser.add_argument('manifest', type=Path)
    import_parser.add_argument('reviews', type=Path)
    import_parser.add_argument('output', type=Path)
    import_parser.add_argument('--target', choices=LABELS, required=True)
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        if args.command == 'export':
            count = export_reviews(manifest, args.output, args.task)
            result = {'exported': count, 'output': str(args.output)}
        else:
            reviews = parse_reviews(args.reviews, LABELS[args.target])
            merged, completed = merge_reviews(manifest, reviews)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
            result = {'reviewedRowsMerged': completed, 'totalRows': len(merged),
                      'output': str(args.output),
                      'next': f'python scripts/validate-research-data.py {args.output} --target {args.target}'}
    except (FileExistsError, OSError, ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

