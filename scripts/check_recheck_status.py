"""Report three-member AI-assisted recheck progress without changing evidence."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))

from scripts.merge_review_exports import IDENTITY_FIELDS, LABELS, load_list


def inspect_exports(base_rows, assignment_index, export_paths):
    base = {row['id']: row for row in base_rows}
    if len(base) != len(base_rows):
        raise ValueError('Base manifest contains duplicate IDs')
    assignments = assignment_index.get('assignments', [])
    expected = {item['reviewerId']: set(item['recordIds']) for item in assignments}
    if not expected:
        raise ValueError('Recheck assignment index has no assignments')
    assigned_ids = [ident for ids in expected.values() for ident in ids]
    if len(assigned_ids) != len(set(assigned_ids)):
        raise ValueError('Recheck assignments overlap')
    unknown = set(assigned_ids) - set(base)
    if unknown:
        raise ValueError(f'Assignments contain unknown records: {sorted(unknown)[:5]}')

    reports = {reviewer: {
        'reviewerId': reviewer,
        'assigned': len(ids),
        'received': 0,
        'validHumanReviews': 0,
        'remaining': len(ids),
        'complete': False,
        'file': None,
        'errors': [],
    } for reviewer, ids in expected.items()}

    for export_path in export_paths:
        rows = load_list(Path(export_path))
        ids = [row.get('id') for row in rows]
        id_set = set(ids)
        overlaps = sorted(
            ((len(id_set & assigned), reviewer) for reviewer, assigned in expected.items()),
            reverse=True,
        )
        if not overlaps or overlaps[0][0] == 0:
            raise ValueError(f'{export_path}: no records belong to a recheck assignment')
        best_count, reviewer = overlaps[0]
        if len(overlaps) > 1 and overlaps[1][0] == best_count:
            raise ValueError(f'{export_path}: cannot identify one reviewer assignment')
        report = reports[reviewer]
        if report['file'] is not None:
            report['errors'].append(f'duplicate export supplied: {export_path}')
            continue
        report['file'] = str(export_path)
        report['received'] = len(rows)
        if len(ids) != len(id_set):
            report['errors'].append('export contains duplicate record IDs')
        missing = expected[reviewer] - id_set
        extra = id_set - expected[reviewer]
        if missing:
            report['errors'].append(f'{len(missing)} assigned records are missing')
        if extra:
            report['errors'].append(f'{len(extra)} records are outside this assignment')

        valid_ids = set()
        for row in rows:
            ident = row.get('id')
            original = base.get(ident)
            row_errors = []
            if original is None:
                row_errors.append('unknown record')
            else:
                for field in IDENTITY_FIELDS:
                    if row.get(field) != original.get(field):
                        row_errors.append(f'changed protected field {field}')
                        break
            if row.get('reviewer') != reviewer:
                row_errors.append(f'reviewer must be {reviewer}')
            if row.get('reviewedLabel') not in LABELS.get(row.get('task'), set()):
                row_errors.append('invalid reviewed label')
            if not str(row.get('reviewedSourceGroup') or '').strip():
                row_errors.append('missing source-fruit group')
            try:
                timestamp = datetime.fromisoformat(str(row.get('reviewedAt')).replace('Z', '+00:00'))
                if timestamp.tzinfo is None:
                    row_errors.append('review time needs a timezone')
            except (TypeError, ValueError):
                row_errors.append('invalid review time')
            if row_errors:
                if len(report['errors']) < 12:
                    report['errors'].append(f'{ident}: {"; ".join(row_errors)}')
            elif ident in expected[reviewer]:
                valid_ids.add(ident)
        report['validHumanReviews'] = len(valid_ids)
        report['remaining'] = len(expected[reviewer] - valid_ids)
        report['complete'] = not report['errors'] and valid_ids == expected[reviewer]

    ordered = [reports[item['reviewerId']] for item in assignments]
    for report in ordered:
        if report['file'] is None:
            report['errors'].append('no export supplied')
    assigned_total = sum(item['assigned'] for item in ordered)
    valid_total = sum(item['validHumanReviews'] for item in ordered)
    return {
        'status': 'complete' if ordered and all(item['complete'] for item in ordered) else 'incomplete',
        'assigned': assigned_total,
        'validHumanReviews': valid_total,
        'remaining': assigned_total - valid_total,
        'percentComplete': round(valid_total * 100 / assigned_total, 1) if assigned_total else 0,
        'assignments': ordered,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs='*', type=Path, help='Returned Review Desk JSON exports')
    parser.add_argument('--base', required=True, type=Path, help='Validated provisional full manifest')
    parser.add_argument('--assignments', required=True, type=Path, help='Recheck assignment-index.json')
    parser.add_argument('--strict', action='store_true', help='Exit unsuccessfully unless all assignments are complete')
    args = parser.parse_args()
    try:
        result = inspect_exports(
            load_list(args.base),
            json.loads(args.assignments.read_text(encoding='utf-8')),
            args.exports,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))
    if args.strict and result['status'] != 'complete':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
