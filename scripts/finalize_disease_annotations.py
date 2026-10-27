"""Merge complete disease-annotation assignments into one validated frozen manifest."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.reviewed_segmentation import SYMPTOMS, validate_segmentation

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_FIELDS = (
    'id', 'candidateSplit', 'fileSha256', 'pixelSha256', 'reviewedSourceGroup',
    'imageRole', 'roiSourceId', 'maskCoordinateSpace',
)
ANNOTATION_FIELDS = (
    'task', 'reviewedLabel', 'reviewer', 'reviewedAt', 'annotationsComplete',
    'annotationReviewer', 'annotationReviewedAt', 'maskCoordinateSpace', 'regions',
    'cropReviewStatus', 'cropReviewer', 'cropReviewedAt', 'excludedFromTraining',
    'exclusionReason',
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_list(path):
    value = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value, list):
        raise ValueError(f'{path}: expected a JSON array')
    return value


def aware_timestamp(value, context):
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (TypeError, ValueError) as error:
        raise ValueError(f'{context}: invalid annotation time') from error
    if parsed.tzinfo is None:
        raise ValueError(f'{context}: annotation time needs a timezone')


def apply_annotations(base_rows, assignment_index, exports):
    if not isinstance(base_rows, list) or not base_rows:
        raise ValueError('Base crop manifest must be a non-empty JSON array')
    base = {row.get('id'): row for row in base_rows}
    if None in base or len(base) != len(base_rows):
        raise ValueError('Base crop manifest contains missing or duplicate IDs')
    expected = {item['reviewerId']: set(item['recordIds'])
                for item in assignment_index.get('assignments', [])}
    if not expected:
        raise ValueError('Annotation assignment index has no assignments')
    assigned = [ident for values in expected.values() for ident in values]
    if len(assigned) != len(set(assigned)):
        raise ValueError('Annotation assignments overlap')
    if set(assigned) != set(base):
        missing = sorted(set(base) - set(assigned))[:5]
        unknown = sorted(set(assigned) - set(base))[:5]
        raise ValueError(f'Assignments must cover the base manifest exactly; missing={missing}, unknown={unknown}')

    patches, received = {}, set()
    for path, rows in exports:
        ids = [row.get('id') for row in rows]
        matches = [reviewer for reviewer, record_ids in expected.items() if set(ids) == record_ids]
        if len(ids) != len(set(ids)) or len(matches) != 1:
            raise ValueError(f'{path}: records do not exactly match one annotation assignment')
        reviewer = matches[0]
        if reviewer in received:
            raise ValueError(f'Duplicate export for {reviewer}')
        received.add(reviewer)
        for row in rows:
            ident = row['id']
            original = base[ident]
            # Package-local image paths intentionally differ, so the canonical base path wins.
            for field in PROTECTED_FIELDS:
                if row.get(field) != original.get(field):
                    raise ValueError(f'{path}: {ident} changed protected field {field}')
            if row.get('task') != 'disease' or row.get('annotationsComplete') is not True:
                raise ValueError(f'{path}: {ident} is not a completed disease annotation')
            if row.get('reviewer') != reviewer or row.get('annotationReviewer') != reviewer:
                raise ValueError(f'{path}: {ident} must be annotated by {reviewer}')
            if row.get('reviewedAt') != row.get('annotationReviewedAt'):
                raise ValueError(f'{path}: {ident} has inconsistent review timestamps')
            aware_timestamp(row.get('annotationReviewedAt'), f'{path}: {ident}')
            if row.get('cropReviewer') != reviewer or row.get('cropReviewedAt') != row.get('reviewedAt'):
                raise ValueError(f'{path}: {ident} has inconsistent crop-review evidence')
            label, regions = row.get('reviewedLabel'), row.get('regions')
            if row.get('excludedFromTraining') is True:
                if row.get('cropReviewStatus') != 'excluded' or label != 'Excluded' or regions != []:
                    raise ValueError(f'{path}: {ident} has invalid crop-exclusion evidence')
                if not str(row.get('exclusionReason') or '').strip():
                    raise ValueError(f'{path}: {ident} needs an exclusion reason')
                patches[ident] = {field: row.get(field) for field in ANNOTATION_FIELDS}
                continue
            if row.get('cropReviewStatus') != 'human-confirmed' or row.get('excludedFromTraining') is not False:
                raise ValueError(f'{path}: {ident} crop must be human-confirmed or excluded')
            if label == 'Healthy':
                if regions != []:
                    raise ValueError(f'{path}: {ident} Healthy record must have an empty regions list')
            elif label not in SYMPTOMS or not isinstance(regions, list) or not regions:
                raise ValueError(f'{path}: {ident} needs a supported label and polygon evidence')
            patches[ident] = {field: row.get(field) for field in ANNOTATION_FIELDS}

    missing = set(expected) - received
    if missing:
        raise ValueError(f'Missing completed annotation exports: {", ".join(sorted(missing))}')
    return [{**row, **patches[row['id']]} for row in base_rows]


def finalize(base_path, assignment_path, export_paths, output_dir, root=ROOT):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=False)
    base_rows = load_list(base_path)
    assignments = json.loads(Path(assignment_path).read_text(encoding='utf-8'))
    exports = [(Path(path), load_list(path)) for path in export_paths]
    all_merged = apply_annotations(base_rows, assignments, exports)
    excluded = [row for row in all_merged if row.get('excludedFromTraining') is True]
    merged = [row for row in all_merged if row.get('excludedFromTraining') is not True]
    if not merged:
        raise ValueError('Every proposed crop was excluded; no trainable disease annotations remain')
    errors = validate_segmentation(merged, root=root)
    if errors:
        raise ValueError(f'Final disease manifest failed validation ({len(errors)} errors):\n' +
                         '\n'.join(errors[:30]))
    manifest_path = output_dir / 'frozen-disease-annotation-manifest.json'
    manifest_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    audit = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'status': 'human-annotated-and-validated',
        'baseManifest': {'path': str(base_path), 'sha256': sha256(base_path)},
        'assignmentIndex': {'path': str(assignment_path), 'sha256': sha256(assignment_path)},
        'exports': [{'path': str(path), 'sha256': sha256(path)} for path in export_paths],
        'assignedRowCount': len(all_merged),
        'rowCount': len(merged),
        'excludedCount': len(excluded),
        'excludedIds': [row['id'] for row in excluded],
        'reviewerCounts': dict(sorted(Counter(row['annotationReviewer'] for row in merged).items())),
        'splitCounts': dict(sorted(Counter(row['candidateSplit'] for row in merged).items())),
        'labelCounts': dict(sorted(Counter(row['reviewedLabel'] for row in merged).items())),
        'manifestSha256': sha256(manifest_path),
        'validationErrors': 0,
    }
    (output_dir / 'annotation-finalization-audit.json').write_text(
        json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exports', nargs='+', type=Path)
    parser.add_argument('--base', required=True, type=Path, help='Original unannotated crop manifest')
    parser.add_argument('--assignments', required=True, type=Path, help='Annotation assignment-index.json')
    parser.add_argument('--output-dir', required=True, type=Path, help='New private output directory')
    args = parser.parse_args()
    try:
        audit = finalize(args.base, args.assignments, args.exports, args.output_dir)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps(audit, indent=2))


if __name__ == '__main__':
    main()
