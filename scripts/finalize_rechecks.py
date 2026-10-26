"""Apply completed recheck patches, reconcile splits, and freeze validated manifests."""
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
from scripts.reconcile_review_splits import reconcile_splits

VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    'pitayagrade_research_validator', ROOT / 'scripts' / 'validate-research-data.py')
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def apply_rechecks(base_rows, assignment_index, exports):
    if not isinstance(base_rows, list) or not base_rows:
        raise ValueError('Base manifest must be a non-empty JSON array')
    base = {row['id']: row for row in base_rows}
    if len(base) != len(base_rows):
        raise ValueError('Base manifest contains duplicate IDs')
    expected = {item['reviewerId']: set(item['recordIds'])
                for item in assignment_index.get('assignments', [])}
    if not expected:
        raise ValueError('Recheck assignment index has no assignments')
    assigned = [ident for values in expected.values() for ident in values]
    if len(assigned) != len(set(assigned)):
        raise ValueError('Recheck assignments overlap')
    unknown = set(assigned) - set(base)
    if unknown:
        raise ValueError(f'Recheck assignments contain unknown records: {sorted(unknown)[:5]}')
    for ident in assigned:
        if not str(base[ident].get('reviewer') or '').startswith('AI-assisted-'):
            raise ValueError(f'{ident}: recheck assignment does not target an AI-assisted row')

    patches = {}
    received = set()
    for path, rows in exports:
        ids = [row.get('id') for row in rows]
        matches = [reviewer for reviewer, record_ids in expected.items() if set(ids) == record_ids]
        if len(ids) != len(set(ids)) or len(matches) != 1:
            raise ValueError(f'{path}: records do not exactly match one non-overlapping recheck assignment')
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
            if row.get('reviewedLabel') not in LABELS.get(row.get('task'), set()):
                raise ValueError(f'{path}: {row["id"]} has an invalid reviewed label')
            if not str(row.get('reviewedSourceGroup') or '').strip():
                raise ValueError(f'{path}: {row["id"]} is missing a source-fruit group')
            try:
                timestamp = datetime.fromisoformat(str(row.get('reviewedAt')).replace('Z', '+00:00'))
            except (TypeError, ValueError) as error:
                raise ValueError(f'{path}: {row["id"]} has an invalid review time') from error
            if timestamp.tzinfo is None:
                raise ValueError(f'{path}: {row["id"]} review time needs a timezone')
            patches[row['id']] = {field: row[field] for field in REVIEW_FIELDS}
    missing = set(expected) - received
    if missing:
        raise ValueError(f'Missing completed recheck exports: {", ".join(sorted(missing))}')

    output = [{**row, **patches.get(row['id'], {})} for row in base_rows]
    assisted = [row['id'] for row in output if str(row.get('reviewer') or '').startswith('AI-assisted-')]
    if assisted:
        raise ValueError(f'AI-assisted attribution remains after recheck: {assisted[:5]}')
    return output


def conflicting_source_groups(rows):
    grouped = defaultdict(set)
    for row in rows:
        grouped[(row.get('task'), row.get('reviewedSourceGroup'))].add(row.get('reviewedLabel'))
    return {key: labels for key, labels in grouped.items() if len(labels) > 1}


def apply_adjudications(rows, document):
    conflicts = conflicting_source_groups(rows)
    decisions = document.get('decisions') if isinstance(document, dict) else None
    if document.get('schemaVersion') != 1 or not isinstance(decisions, list):
        raise ValueError('Adjudication file must use schemaVersion 1 with a decisions array')
    indexed = {}
    normalized = []
    for decision in decisions:
        key = (decision.get('task'), decision.get('reviewedSourceGroup'))
        if key in indexed:
            raise ValueError(f'Duplicate adjudication decision for {key[0]} / {key[1]}')
        indexed[key] = decision
    missing = set(conflicts) - set(indexed)
    unexpected = set(indexed) - set(conflicts)
    if missing:
        names = ', '.join(f'{task}/{group}' for task, group in sorted(missing))
        raise ValueError(f'Missing adjudication decisions: {names}')
    if unexpected:
        names = ', '.join(f'{task}/{group}' for task, group in sorted(unexpected))
        raise ValueError(f'Adjudication file targets non-conflicting groups: {names}')
    for key, conflict_labels in conflicts.items():
        decision = indexed[key]
        label = decision.get('reviewedLabel')
        adjudicator = str(decision.get('adjudicator') or '').strip()
        reviewed_at = decision.get('adjudicatedAt')
        if label not in LABELS.get(key[0], set()) or label not in conflict_labels:
            raise ValueError(f'{key[0]} / {key[1]}: adjudicated label must be one of {sorted(conflict_labels)}')
        if not adjudicator or adjudicator.startswith('AI-assisted-'):
            raise ValueError(f'{key[0]} / {key[1]}: a genuine human adjudicator ID is required')
        try:
            timestamp = datetime.fromisoformat(str(reviewed_at).replace('Z', '+00:00'))
        except (TypeError, ValueError) as error:
            raise ValueError(f'{key[0]} / {key[1]}: invalid adjudication time') from error
        if timestamp.tzinfo is None:
            raise ValueError(f'{key[0]} / {key[1]}: adjudication time needs a timezone')
        normalized.append({
            'task': key[0], 'reviewedSourceGroup': key[1], 'reviewedLabel': label,
            'adjudicator': adjudicator, 'adjudicatedAt': reviewed_at,
            'previousLabels': sorted(conflict_labels),
            'rationale': str(decision.get('rationale') or '').strip(),
        })
    patched = []
    by_key = {(item['task'], item['reviewedSourceGroup']): item for item in normalized}
    for row in rows:
        decision = by_key.get((row.get('task'), row.get('reviewedSourceGroup')))
        patched.append({**row, **({
            'reviewedLabel': decision['reviewedLabel'],
            'reviewer': decision['adjudicator'],
            'reviewedAt': decision['adjudicatedAt'],
        } if decision else {})})
    if conflicting_source_groups(patched):
        raise ValueError('Adjudication did not resolve every conflicting source group')
    return patched, sorted(normalized, key=lambda item: (item['task'], item['reviewedSourceGroup']))


def validate_tasks(rows, root=ROOT):
    errors = []
    for task, target in (('quality', 'manuscript-quality'), ('maturity', 'maturity')):
        subset = [row for row in rows if row.get('task') == task]
        if not subset:
            errors.append(f'Missing {task} records')
            continue
        errors.extend(f'{task}: {error}' for error in VALIDATOR.validate(subset, target, root=root))
    return errors


def finalize(base_path, assignment_path, export_paths, output_dir, root=ROOT,
             adjudication_path=None):
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(f'Refusing to overwrite {output_dir}')
    base_rows = load_list(Path(base_path))
    assignments = json.loads(Path(assignment_path).read_text(encoding='utf-8'))
    exports = [(Path(path), load_list(Path(path))) for path in export_paths]
    reviewed = apply_rechecks(base_rows, assignments, exports)
    adjudications = []
    if adjudication_path:
        document = json.loads(Path(adjudication_path).read_text(encoding='utf-8'))
        reviewed, adjudications = apply_adjudications(reviewed, document)
    reconciled, split_summary = reconcile_splits(reviewed)
    errors = validate_tasks(reconciled, root)
    if errors:
        raise ValueError(f'Final manifest failed validation ({len(errors)} errors):\n' + '\n'.join(errors[:30]))
    output_dir.mkdir(parents=True, exist_ok=False)
    reviewed_path = output_dir / 'human-reviewed-manifest.json'
    reviewed_path.write_text(json.dumps(reviewed, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    training_path = output_dir / 'frozen-training-manifest.json'
    training_path.write_text(json.dumps(reconciled, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    task_paths = {}
    for task in ('quality', 'maturity'):
        task_path = output_dir / f'frozen-{task}-manifest.json'
        task_path.write_text(json.dumps([row for row in reconciled if row.get('task') == task],
                                        indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        task_paths[task] = task_path
    audit = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'human-reviewed-and-validated',
        'baseManifest': {'path': str(base_path), 'sha256': sha256(base_path)},
        'assignmentIndex': {'path': str(assignment_path), 'sha256': sha256(assignment_path)},
        'exports': [{'path': str(path), 'sha256': sha256(path)} for path in export_paths],
        'adjudication': ({
            'path': str(adjudication_path), 'sha256': sha256(adjudication_path),
            'decisions': adjudications,
        } if adjudication_path else None),
        'rowCount': len(reconciled),
        'taskCounts': dict(sorted(Counter(row['task'] for row in reconciled).items())),
        'reviewerCounts': dict(sorted(Counter(row['reviewer'] for row in reconciled).items())),
        'splitReconciliation': split_summary,
        'reviewedManifestSha256': sha256(reviewed_path),
        'frozenTrainingManifestSha256': sha256(training_path),
        'frozenQualityManifestSha256': sha256(task_paths['quality']),
        'frozenMaturityManifestSha256': sha256(task_paths['maturity']),
        'validationTargets': ['manuscript-quality', 'maturity'],
        'validationErrors': 0,
    }
    (output_dir / 'finalization-audit.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs='+', type=Path)
    parser.add_argument('--base', required=True, type=Path, help='Validated provisional full manifest')
    parser.add_argument('--assignments', required=True, type=Path, help='Recheck assignment-index.json')
    parser.add_argument('--adjudications', type=Path,
                        help='Human coordinator/adviser decisions for conflicting source groups')
    parser.add_argument('--output-dir', required=True, type=Path, help='New private output directory')
    args = parser.parse_args()
    try:
        audit = finalize(args.base, args.assignments, args.exports, args.output_dir,
                         adjudication_path=args.adjudications)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
