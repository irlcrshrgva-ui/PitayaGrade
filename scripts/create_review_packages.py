"""Create balanced, non-overlapping at-home dataset review packages."""
import argparse
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def build_bundles(rows, suggestions):
    by_id = {row['id']: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError('Manifest IDs must be unique')
    assigned = set()
    bundles = []
    for group in suggestions.get('groups', []):
        ids = [member.get('id') for member in group.get('members', [])]
        if len(ids) < 2 or any(ident not in by_id for ident in ids):
            raise ValueError('Suggestion group contains unknown or insufficient members')
        if assigned.intersection(ids):
            raise ValueError('Suggestion groups must not overlap')
        assigned.update(ids)
        bundles.append({
            'candidateSourceGroup': group['suggestedSourceGroup'],
            'rows': [by_id[ident] for ident in ids],
        })
    for row in rows:
        if row['id'] not in assigned:
            bundles.append({'candidateSourceGroup': None, 'rows': [row]})
    return bundles


def assign_bundles(bundles, reviewer_count):
    if reviewer_count < 2:
        raise ValueError('At least two reviewers are required for workload splitting')
    assignments = [{'rows': [], 'candidateSourceGroups': []} for _ in range(reviewer_count)]
    task_counts = [Counter() for _ in range(reviewer_count)]
    totals = [0] * reviewer_count
    ordered = sorted(bundles, key=lambda bundle: (-len(bundle['rows']), bundle['rows'][0]['id']))
    for bundle in ordered:
        bundle_tasks = Counter(row['task'] for row in bundle['rows'])
        reviewer = min(
            range(reviewer_count),
            key=lambda index: (
                totals[index],
                sum(task_counts[index][task] for task in bundle_tasks),
                index,
            ),
        )
        assignments[reviewer]['rows'].extend(bundle['rows'])
        if bundle['candidateSourceGroup']:
            assignments[reviewer]['candidateSourceGroups'].append(bundle['candidateSourceGroup'])
        totals[reviewer] += len(bundle['rows'])
        task_counts[reviewer].update(bundle_tasks)
    for assignment in assignments:
        assignment['rows'].sort(key=lambda row: row['id'])
    return assignments


def verify_assignments(rows, assignments, suggestions):
    expected = {row['id'] for row in rows}
    actual = [row['id'] for assignment in assignments for row in assignment['rows']]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('Every manifest record must occur in exactly one assignment')
    owner = {}
    for index, assignment in enumerate(assignments):
        for row in assignment['rows']:
            owner[row['id']] = index
    for group in suggestions.get('groups', []):
        owners = {owner[member['id']] for member in group['members']}
        if len(owners) != 1:
            raise ValueError(f"Candidate group {group['suggestedSourceGroup']} was split")


def relative_prepared(image):
    prefix = 'dataset/public/prepared/'
    normalized = str(image).replace('\\', '/')
    if not normalized.startswith(prefix):
        raise ValueError(f'Image path is outside the prepared dataset: {image}')
    return normalized[len(prefix):]


def package_assignment(output, reviewer_id, rows, candidate_groups):
    archive = output / f'{reviewer_id}-pitayagrade-review.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    assignment = {
        'schemaVersion': 1,
        'reviewerId': reviewer_id,
        'recordCount': len(rows),
        'taskCounts': dict(sorted(Counter(row['task'] for row in rows).items())),
        'candidateSourceGroupsKeptTogether': candidate_groups,
        'rows': rows,
    }
    instructions = f"""PitayaGrade at-home review package: {reviewer_id}

1. Extract this ZIP file.
2. Open https://irlcrshrgva-ui.github.io/PitayaGrade/review-tool/index.html
3. Choose assignment {reviewer_id}.
4. Click Load local dataset folder and select this extracted package folder.
5. Confirm each image using the adviser-approved grading guide.
6. Use the assigned reviewer ID: {reviewer_id}
7. Export the reviewed manifest at the end of every session.

Do not exchange assignments or copy the source label without inspecting the image.
The candidate source-group suggestions are review aids, not confirmed source identities.
"""
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.writestr('assignment.json', json.dumps(assignment, indent=2, ensure_ascii=False) + '\n')
        bundle.writestr('INSTRUCTIONS.txt', instructions)
        for row in rows:
            source = ROOT / row['image']
            if not source.is_file():
                raise FileNotFoundError(f'Missing prepared image: {source}')
            expected_hash = row.get('fileSha256')
            if expected_hash:
                actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
                if actual_hash != expected_hash:
                    raise ValueError(f'Checksum mismatch: {source}')
            bundle.write(source, f"prepared/{relative_prepared(row['image'])}")
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviewers', type=int, default=3)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'research/public-review-manifest.json')
    parser.add_argument('--suggestions', type=Path, default=ROOT / 'research/source-group-suggestions-2026-10-10.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'local-review/three-member-packages-2026-10-11')
    parser.add_argument('--assignments-output', type=Path, default=ROOT / 'research/review-assignments-3.json')
    args = parser.parse_args()

    rows = load_json(args.manifest)
    suggestions = load_json(args.suggestions)
    bundles = build_bundles(rows, suggestions)
    assignments = assign_bundles(bundles, args.reviewers)
    verify_assignments(rows, assignments, suggestions)
    args.output.mkdir(parents=True, exist_ok=True)

    public = {'schemaVersion': 1, 'manifestRowCount': len(rows), 'assignments': []}
    archives = []
    for index, assignment in enumerate(assignments, 1):
        reviewer_id = f'reviewer-{index:02d}'
        public['assignments'].append({
            'reviewerId': reviewer_id,
            'recordCount': len(assignment['rows']),
            'taskCounts': dict(sorted(Counter(row['task'] for row in assignment['rows']).items())),
            'recordIds': [row['id'] for row in assignment['rows']],
        })
        archives.append(package_assignment(
            args.output, reviewer_id, assignment['rows'], assignment['candidateSourceGroups']))

    if args.assignments_output.exists():
        raise FileExistsError(f'Refusing to overwrite {args.assignments_output}')
    args.assignments_output.write_text(json.dumps(public, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({
        'assignments': [{
            'reviewerId': item['reviewerId'],
            'recordCount': item['recordCount'],
            'taskCounts': item['taskCounts'],
        } for item in public['assignments']],
        'archives': [str(path) for path in archives],
        'assignmentIndex': str(args.assignments_output),
    }, indent=2))


if __name__ == '__main__':
    main()
