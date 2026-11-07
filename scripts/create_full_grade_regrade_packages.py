"""Create three source-group-safe packages for a fresh A/B/C label repair pass."""
import argparse
import hashlib
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))

from scripts.create_review_packages import assign_bundles, relative_prepared

GRADES = {'Grade A', 'Grade B', 'Grade C'}
REVIEWER_PREFIX = 'grade-repair'


def load_rows(path):
    rows = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or not rows:
        raise ValueError('Manifest must be a non-empty JSON array')
    return rows


def eligible_rows(rows):
    selected = [
        row for row in rows
        if row.get('task') == 'quality'
        and row.get('candidateSplit') in {'train', 'val'}
        and row.get('reviewedLabel') in GRADES
    ]
    ids = [row.get('id') for row in selected]
    if len(ids) != len(set(ids)):
        raise ValueError('Eligible record IDs must be unique')
    if any(not str(row.get('reviewedSourceGroup') or '').strip() for row in selected):
        raise ValueError('Every selected row needs an existing source-fruit group')
    if any(row.get('candidateSplit') == 'test' for row in selected):
        raise ValueError('The frozen test set must not be included')
    return selected


def source_group_bundles(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row['reviewedSourceGroup']).strip()].append(row)
    bundles = []
    for group, group_rows in sorted(grouped.items()):
        splits = {row['candidateSplit'] for row in group_rows}
        if len(splits) != 1:
            raise ValueError(f'Source group {group} crosses train/validation splits')
        bundles.append({
            'candidateSourceGroup': group,
            'rows': sorted(group_rows, key=lambda row: row['id']),
        })
    return bundles


def assignment_index(assignments, manifest_path, manifest_sha256):
    records = []
    for index, assignment in enumerate(assignments, 1):
        reviewer = f'{REVIEWER_PREFIX}-{index:02d}'
        rows = assignment['rows']
        records.append({
            'reviewerId': reviewer,
            'recordCount': len(rows),
            'taskCounts': {'quality': len(rows)},
            'splitCounts': dict(sorted(Counter(row['candidateSplit'] for row in rows).items())),
            'priorLabelCounts': dict(sorted(Counter(row['reviewedLabel'] for row in rows).items())),
            'recordIds': [row['id'] for row in rows],
            'sourceGroups': {
                row['id']: str(row['reviewedSourceGroup']).strip() for row in rows
            },
        })
    return {
        'schemaVersion': 1,
        'purpose': 'fresh human A/B/C label repair; frozen test set excluded',
        'sourceManifest': str(manifest_path).replace('\\', '/'),
        'sourceManifestSha256': manifest_sha256,
        'frozenTestSetExcluded': True,
        'manifestRowCount': sum(item['recordCount'] for item in records),
        'assignments': records,
    }


RUBRIC_TEMPLATE = """PITAYAGRADE A/B/C GRADING RUBRIC — APPROVAL REQUIRED

Do not begin labeling until the capstone adviser or qualified agriculture expert
has completed and approved this page. The project team must not invent criteria.

Approved Grade A visual criteria:
______________________________________________________________________________
______________________________________________________________________________

Approved Grade B visual criteria:
______________________________________________________________________________
______________________________________________________________________________

Approved Grade C visual criteria:
______________________________________________________________________________
______________________________________________________________________________

Boundary rule for A versus B:
______________________________________________________________________________

Boundary rule for B versus C:
______________________________________________________________________________

Cases that cannot be graded from a photograph alone:
______________________________________________________________________________

Approver name and role: ______________________________________________________
Approval date: ____________________  Signature/confirmation: __________________

Important: weight, sweetness, firmness, or internal condition cannot be inferred
from an ordinary photograph unless independently measured and recorded.
"""


def instructions(reviewer, count):
    return f"""PitayaGrade full A/B/C grade repair: {reviewer} ({count} images)

STOP: obtain the completed adviser-approved RUBRIC-APPROVAL-REQUIRED.txt first.

1. Extract this ZIP permanently.
2. Open https://irlcrshrgva-ui.github.io/PitayaGrade/review-tool/index.html
3. Click Load recheck assignment and select assignment-index.json from this folder.
4. Under Member assignment select {reviewer}.
5. Click Load local dataset folder and select this extracted folder.
6. Confirm the page reports {count} assigned records and {count} local images.
7. Select Quality grading and Unreviewed first.
8. Inspect every image using only the approved rubric. The displayed source label
   is not a quality grade and must not be copied as one.
9. Press 1/2/3 for Grade A/B/C, then Ctrl+Enter to save and advance.
10. Do not change the prefilled source-fruit group unless the coordinator confirms
    it is wrong. Photos from one physical fruit must stay in one group.
11. Export a draft backup after every work session.
12. At 100%, click Export reviewed manifest and return the JSON to the coordinator.

Do not load a model-proposal file for this repair pass. This must be a fresh human
decision. Uncertain records must be listed for adviser adjudication, not guessed.
The frozen test set is not included in this package.
"""


def write_package(output, assignment, public_index):
    reviewer = assignment['reviewerId']
    archive = output / f'{reviewer}-pitayagrade-grade-repair.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    row_by_id = {row['id']: row for row in assignment['rows']}
    count = len(row_by_id)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as bundle:
        bundle.writestr('assignment-index.json', json.dumps(public_index, indent=2) + '\n')
        bundle.writestr('INSTRUCTIONS.txt', instructions(reviewer, count))
        bundle.writestr('RUBRIC-APPROVAL-REQUIRED.txt', RUBRIC_TEMPLATE)
        for row in assignment['rows']:
            source = ROOT / row['image']
            if not source.is_file():
                raise FileNotFoundError(f'Missing prepared image: {source}')
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            if actual != row.get('fileSha256'):
                raise ValueError(f'Checksum mismatch: {source}')
            bundle.write(source, f"prepared/{relative_prepared(row['image'])}")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--reviewers', type=int, default=3)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.reviewers < 2:
        raise SystemExit('At least two reviewers are required')
    try:
        manifest_bytes = args.manifest.read_bytes()
        rows = eligible_rows(json.loads(manifest_bytes.decode('utf-8')))
        bundles = source_group_bundles(rows)
        assignments = assign_bundles(bundles, args.reviewers)
        public = assignment_index(assignments, args.manifest,
                                  hashlib.sha256(manifest_bytes).hexdigest())
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'assignment-index.json').write_text(
            json.dumps(public, indent=2) + '\n', encoding='utf-8')
        (args.output / 'RUBRIC-APPROVAL-REQUIRED.txt').write_text(
            RUBRIC_TEMPLATE, encoding='utf-8')
        archives = []
        for index, assignment in enumerate(assignments, 1):
            assignment['reviewerId'] = f'{REVIEWER_PREFIX}-{index:02d}'
            archives.append(write_package(args.output, assignment, public))
        print(json.dumps({
            'records': len(rows),
            'sourceGroups': len(bundles),
            'frozenTestSetExcluded': True,
            'assignments': [{
                'reviewerId': item['reviewerId'],
                'recordCount': item['recordCount'],
                'splitCounts': item['splitCounts'],
                'priorLabelCounts': item['priorLabelCounts'],
            } for item in public['assignments']],
            'archives': [str(path) for path in archives],
        }, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error


if __name__ == '__main__':
    main()
