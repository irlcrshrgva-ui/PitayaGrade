"""Split AI-assisted review rows into private human recheck packages."""
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
REVIEW_FIELDS = ('reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt')


def assisted_bundles(rows):
    assisted = [row for row in rows if str(row.get('reviewer') or '').startswith('AI-assisted-')]
    if not assisted:
        raise ValueError('Manifest contains no AI-assisted records')
    grouped = defaultdict(list)
    for row in assisted:
        group = str(row.get('reviewedSourceGroup') or '').strip()
        if not group:
            raise ValueError(f'{row.get("id")}: missing reviewed source group')
        grouped[(row.get('task'), group)].append(row)
    return [
        {'candidateSourceGroup': group, 'rows': sorted(group_rows, key=lambda row: row['id'])}
        for (_, group), group_rows in sorted(grouped.items())
    ]


def assignment_index(assignments):
    records = []
    for index, assignment in enumerate(assignments, 1):
        reviewer = f'recheck-{index:02d}'
        records.append({
            'reviewerId': reviewer,
            'recordCount': len(assignment['rows']),
            'taskCounts': dict(sorted(Counter(row['task'] for row in assignment['rows']).items())),
            'recordIds': [row['id'] for row in assignment['rows']],
        })
    return {
        'schemaVersion': 1,
        'purpose': 'human confirmation of AI-assisted labels',
        'manifestRowCount': sum(item['recordCount'] for item in records),
        'assignments': records,
    }


def write_package(output, assignment, public_index):
    reviewer = assignment['reviewerId']
    row_by_id = {row['id']: row for row in assignment['rows']}
    public_assignment = next(item for item in public_index['assignments']
                             if item['reviewerId'] == reviewer)
    drafts = {
        ident: {field: row[field] for field in REVIEW_FIELDS}
        for ident, row in row_by_id.items()
    }
    archive = output / f'{reviewer}-pitayagrade-assisted-recheck.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    instructions = f"""PitayaGrade AI-assisted label recheck: {reviewer}

1. Extract this ZIP permanently.
2. Open the Review Desk URL supplied by the coordinator.
3. Load assignment-index.json using Load recheck assignment.
4. Select assignment {reviewer}.
5. Load draft-backup.json using Restore draft backup.
6. Load this extracted folder using Load local dataset folder.
7. Choose All AI-assisted labels under Show.
8. Inspect every image, correct the label/group when needed, and click Save review & next.
9. The AI-assisted queue must reach zero for both Quality grading and Maturity.
10. Export the reviewed manifest and return it to the coordinator.

Do not accept a proposed label without inspecting the image.
"""
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.writestr('assignment-index.json', json.dumps(public_index, indent=2) + '\n')
        bundle.writestr('draft-backup.json', json.dumps(drafts, indent=2) + '\n')
        bundle.writestr('INSTRUCTIONS.txt', instructions)
        for row in assignment['rows']:
            source = ROOT / row['image']
            if not source.is_file():
                raise FileNotFoundError(f'Missing prepared image: {source}')
            if hashlib.sha256(source.read_bytes()).hexdigest() != row.get('fileSha256'):
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
        raise SystemExit('At least two recheck reviewers are required')
    try:
        rows = json.loads(args.manifest.read_text(encoding='utf-8'))
        bundles = assisted_bundles(rows)
        assignments = assign_bundles(bundles, args.reviewers)
        public = assignment_index(assignments)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / 'assignment-index.json').write_text(
            json.dumps(public, indent=2) + '\n', encoding='utf-8'
        )
        archives = []
        for index, assignment in enumerate(assignments, 1):
            assignment['reviewerId'] = f'recheck-{index:02d}'
            archives.append(write_package(args.output, assignment, public))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({
        'records': public['manifestRowCount'],
        'assignments': [{key: item[key] for key in ('reviewerId', 'recordCount', 'taskCounts')}
                        for item in public['assignments']],
        'archives': [str(path) for path in archives],
    }, indent=2))


if __name__ == '__main__':
    main()
