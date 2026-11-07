"""Validate three full grade-repair exports and apply them without touching test rows."""
import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))

from scripts.merge_review_exports import IDENTITY_FIELDS, LABELS, REVIEW_FIELDS, load_list

VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    'pitayagrade_research_validator', ROOT / 'scripts' / 'validate-research-data.py')
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)

GRADES = {'Grade A', 'Grade B', 'Grade C'}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def eligible_ids(rows):
    return {
        row['id'] for row in rows
        if row.get('task') == 'quality'
        and row.get('candidateSplit') in {'train', 'val'}
        and row.get('reviewedLabel') in GRADES
    }


def conflicts(rows):
    grouped = defaultdict(set)
    for row in rows:
        grouped[(row.get('task'), str(row.get('reviewedSourceGroup') or '').strip())].add(
            row.get('reviewedLabel'))
    return {key: labels for key, labels in grouped.items() if key[1] and len(labels) > 1}


def apply_repairs(base_rows, assignment_index, exports, base_sha256):
    base = {row['id']: row for row in base_rows}
    if len(base) != len(base_rows):
        raise ValueError('Base manifest contains duplicate IDs')
    if assignment_index.get('sourceManifestSha256') != base_sha256:
        raise ValueError('Assignment index is not bound to this base manifest checksum')
    if assignment_index.get('frozenTestSetExcluded') is not True:
        raise ValueError('Assignment index does not certify that the test set was excluded')
    expected = {item['reviewerId']: set(item['recordIds'])
                for item in assignment_index.get('assignments', [])}
    if len(expected) != 3:
        raise ValueError('Exactly three grade-repair assignments are required')
    assigned = [ident for ids in expected.values() for ident in ids]
    if len(assigned) != len(set(assigned)):
        raise ValueError('Grade-repair assignments overlap')
    if set(assigned) != eligible_ids(base_rows):
        raise ValueError('Assignments must exactly cover every non-test A/B/C record')
    if any(base[ident].get('candidateSplit') == 'test' for ident in assigned):
        raise ValueError('Frozen test records must never be assigned for repair')

    patches = {}
    received = set()
    for path, rows in exports:
        ids = [row.get('id') for row in rows]
        matches = [reviewer for reviewer, expected_ids in expected.items()
                   if set(ids) == expected_ids]
        if len(ids) != len(set(ids)) or len(matches) != 1:
            raise ValueError(f'{path}: rows do not exactly match one assignment')
        reviewer = matches[0]
        if reviewer in received:
            raise ValueError(f'Duplicate export for {reviewer}')
        received.add(reviewer)
        for row in rows:
            original = base[row['id']]
            for field in IDENTITY_FIELDS:
                if row.get(field) != original.get(field):
                    raise ValueError(f'{path}: {row["id"]} changed protected field {field}')
            if row.get('reviewer') != reviewer:
                raise ValueError(f'{path}: {row["id"]} must be saved by {reviewer}')
            if row.get('reviewedLabel') not in LABELS['quality']:
                raise ValueError(f'{path}: {row["id"]} has an invalid quality label')
            original_group = str(original.get('reviewedSourceGroup') or '').strip()
            returned_group = str(row.get('reviewedSourceGroup') or '').strip()
            if returned_group != original_group:
                raise ValueError(f'{path}: {row["id"]} changed protected source-fruit group')
            try:
                timestamp = datetime.fromisoformat(str(row.get('reviewedAt')).replace('Z', '+00:00'))
            except (TypeError, ValueError) as error:
                raise ValueError(f'{path}: {row["id"]} has an invalid review time') from error
            if timestamp.tzinfo is None:
                raise ValueError(f'{path}: {row["id"]} review time needs a timezone')
            patches[row['id']] = {field: row[field] for field in REVIEW_FIELDS}
    missing = set(expected) - received
    if missing:
        raise ValueError(f'Missing completed exports: {", ".join(sorted(missing))}')

    repaired = [{**row, **patches.get(row['id'], {})} for row in base_rows]
    group_conflicts = conflicts(repaired)
    if group_conflicts:
        examples = ', '.join(
            f'{task}/{group}: {sorted(labels)}'
            for (task, group), labels in sorted(group_conflicts.items())[:10])
        raise ValueError(f'Returned labels conflict inside source-fruit groups: {examples}')
    errors = VALIDATOR.validate(repaired, 'manuscript-quality', root=ROOT)
    if errors:
        raise ValueError('Repaired manifest failed validation:\n' + '\n'.join(errors[:30]))
    return repaired


def finalize(base_path, assignment_path, export_paths, output_dir):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite {output_dir}')
    base_path = Path(base_path)
    assignment_path = Path(assignment_path)
    base_rows = load_list(base_path)
    base_hash = sha256(base_path)
    assignments = json.loads(assignment_path.read_text(encoding='utf-8'))
    exports = [(Path(path), load_list(Path(path))) for path in export_paths]
    repaired = apply_repairs(base_rows, assignments, exports, base_hash)

    old_test = [row for row in base_rows if row.get('candidateSplit') == 'test']
    new_test = [row for row in repaired if row.get('candidateSplit') == 'test']
    if old_test != new_test:
        raise ValueError('Frozen test evidence changed during grade repair')

    output_dir.mkdir(parents=True, exist_ok=False)
    repaired_path = output_dir / 'repaired-quality-manifest.json'
    repaired_path.write_text(json.dumps(repaired, indent=2, ensure_ascii=False) + '\n',
                             encoding='utf-8')
    test_path = output_dir / 'unchanged-frozen-test-manifest.json'
    test_path.write_text(json.dumps(new_test, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    changed = [
        row['id'] for row, original in zip(repaired, base_rows)
        if row.get('reviewedLabel') != original.get('reviewedLabel')
    ]
    audit = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'human-grade-repair-validated',
        'baseManifest': {'path': str(base_path), 'sha256': base_hash},
        'assignmentIndex': {'path': str(assignment_path), 'sha256': sha256(assignment_path)},
        'exports': [{'path': str(path), 'sha256': sha256(path)} for path in export_paths],
        'rowCount': len(repaired),
        'recheckedRows': sum(item['recordCount'] for item in assignments['assignments']),
        'changedLabels': len(changed),
        'changedRecordIds': changed,
        'labelCounts': dict(sorted(Counter(row['reviewedLabel'] for row in repaired).items())),
        'frozenTestRows': len(new_test),
        'frozenTestUnchanged': True,
        'validationErrors': 0,
        'repairedManifestSha256': sha256(repaired_path),
        'frozenTestManifestSha256': sha256(test_path),
    }
    (output_dir / 'grade-repair-audit.json').write_text(
        json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs=3, type=Path)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--assignments', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        audit = finalize(args.base, args.assignments, args.exports, args.output_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
