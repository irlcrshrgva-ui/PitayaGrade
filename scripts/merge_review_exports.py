"""Strictly merge the three completed at-home Review Desk exports."""
import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    'quality': {'Grade A', 'Grade B', 'Grade C', 'Reject'},
    'maturity': {'Mature Dragon Fruit', 'Immature Dragon Fruit'},
}
REVIEW_FIELDS = ('reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt')
IDENTITY_FIELDS = ('id', 'task', 'image', 'candidateSplit', 'sourceDataset', 'sourceLabel',
                   'fileSha256', 'pixelSha256')


def load_list(path):
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, list) or not value:
        raise ValueError(f'{path}: expected a non-empty JSON array')
    return value


def merge_exports(manifest, assignment_index, exports, allow_assisted=False):
    base = {row['id']: row for row in manifest}
    if len(base) != len(manifest):
        raise ValueError('Base manifest contains duplicate IDs')
    expected_by_reviewer = {
        item['reviewerId']: set(item['recordIds']) for item in assignment_index['assignments']
    }
    merged_reviews = {}
    received_reviewers = set()
    for path, rows in exports:
        ids = [row.get('id') for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f'{path}: export contains duplicate record IDs')
        reviewers = {str(row.get('reviewer') or '').strip() for row in rows}
        reviewers.discard('')
        if allow_assisted:
            assignment_matches = [
                reviewer_id for reviewer_id, expected_ids in expected_by_reviewer.items()
                if set(ids) == expected_ids
            ]
            if len(assignment_matches) != 1:
                raise ValueError(f'{path}: records do not exactly match one reviewer assignment')
            reviewer = assignment_matches[0]
            allowed_reviewers = {reviewer, f'AI-assisted-{reviewer}'}
            if not reviewers or not reviewers <= allowed_reviewers:
                unexpected = ', '.join(sorted(reviewers - allowed_reviewers)) or 'blank reviewer ID'
                raise ValueError(f'{path}: reviewer attribution is invalid for {reviewer}: {unexpected}')
        else:
            if len(reviewers) != 1:
                raise ValueError(f'{path}: export must contain one completed reviewer ID')
            reviewer = reviewers.pop()
            if reviewer not in expected_by_reviewer:
                raise ValueError(f'{path}: unknown reviewer assignment {reviewer}')
        if reviewer in received_reviewers:
            raise ValueError(f'Duplicate export for {reviewer}')
        received_reviewers.add(reviewer)
        if set(ids) != expected_by_reviewer[reviewer]:
            raise ValueError(f'{path}: records do not exactly match {reviewer} assignment')
        for row in rows:
            original = base.get(row['id'])
            if original is None:
                raise ValueError(f'{path}: unknown record {row["id"]}')
            for field in IDENTITY_FIELDS:
                if row.get(field) != original.get(field):
                    raise ValueError(f'{path}: {row["id"]} changed protected field {field}')
            allowed_row_reviewers = ({reviewer, f'AI-assisted-{reviewer}'}
                                     if allow_assisted else {reviewer})
            if row.get('reviewer') not in allowed_row_reviewers:
                raise ValueError(f'{path}: {row["id"]} has the wrong reviewer ID')
            if row.get('reviewedLabel') not in LABELS.get(row.get('task'), set()):
                raise ValueError(f'{path}: {row["id"]} has an invalid reviewed label')
            if not str(row.get('reviewedSourceGroup') or '').strip():
                raise ValueError(f'{path}: {row["id"]} is missing a source-fruit group')
            try:
                reviewed_at = datetime.fromisoformat(str(row.get('reviewedAt')).replace('Z', '+00:00'))
            except (TypeError, ValueError) as error:
                raise ValueError(f'{path}: {row["id"]} has an invalid review time') from error
            if reviewed_at.tzinfo is None:
                raise ValueError(f'{path}: {row["id"]} review time needs a timezone')
            merged_reviews[row['id']] = {field: row[field] for field in REVIEW_FIELDS}
    missing_reviewers = set(expected_by_reviewer) - received_reviewers
    if missing_reviewers:
        raise ValueError(f'Missing completed exports: {", ".join(sorted(missing_reviewers))}')
    output = []
    for row in manifest:
        review = merged_reviews.get(row['id'])
        if review is None:
            raise ValueError(f'Missing reviewed record: {row["id"]}')
        output.append({**row, **review})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs='+', type=Path)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'research/public-review-manifest.json')
    parser.add_argument('--assignments', type=Path, default=ROOT / 'research/review-assignments-3.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument(
        '--allow-assisted', action='store_true',
        help='Allow AI-assisted-<reviewer> rows while preserving their provenance. '
             'The result is provisional, not final human ground truth.',
    )
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit(f'Refusing to overwrite {args.output}')
    try:
        manifest = load_list(args.manifest)
        assignment_index = json.loads(args.assignments.read_text(encoding='utf-8'))
        exports = [(path, load_list(path)) for path in args.exports]
        merged = merge_exports(
            manifest, assignment_index, exports, allow_assisted=args.allow_assisted
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({
        'reviewedRowsMerged': len(merged),
        'provisional': args.allow_assisted,
        'output': str(args.output),
    }, indent=2))


if __name__ == '__main__':
    main()
