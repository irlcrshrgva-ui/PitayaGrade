"""Create private three-member packages for reviewed disease-polygon annotation."""
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

from scripts.create_review_packages import assign_bundles


def annotation_bundles(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Crop annotation manifest must be a non-empty JSON array')
    seen = set()
    grouped = defaultdict(list)
    group_splits = defaultdict(set)
    for row in rows:
        ident = row.get('id')
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError(f'Invalid or duplicate record ID: {ident}')
        seen.add(ident)
        if row.get('candidateSplit') not in ('train', 'val', 'test'):
            raise ValueError(f'{ident}: invalid candidate split')
        if row.get('imageRole') != 'fruit-roi' or not row.get('roiSourceId'):
            raise ValueError(f'{ident}: reviewed fruit crop provenance is required')
        if row.get('annotationsComplete') is not False or row.get('regions') is not None:
            raise ValueError(f'{ident}: expected an unannotated crop draft')
        group = str(row.get('reviewedSourceGroup') or row['roiSourceId']).strip()
        if not group:
            raise ValueError(f'{ident}: missing source group')
        grouped[group].append({**row, 'task': 'disease'})
        group_splits[group].add(row['candidateSplit'])
    leaking = [group for group, splits in group_splits.items() if len(splits) != 1]
    if leaking:
        raise ValueError(f'Related crop groups cross candidate splits: {", ".join(leaking[:10])}')
    return [{'candidateSourceGroup': group, 'rows': sorted(items, key=lambda row: row['id'])}
            for group, items in sorted(grouped.items())]


def assignment_index(assignments):
    values = []
    for index, assignment in enumerate(assignments, 1):
        values.append({
            'reviewerId': f'mask-reviewer-{index:02d}',
            'recordCount': len(assignment['rows']),
            'splitCounts': dict(sorted(Counter(row['candidateSplit'] for row in assignment['rows']).items())),
            'recordIds': [row['id'] for row in assignment['rows']],
        })
    return {'schemaVersion': 1, 'purpose': 'human disease polygon annotation',
            'manifestRowCount': sum(item['recordCount'] for item in values), 'assignments': values}


def write_package(output, assignment, public, root=ROOT):
    reviewer = assignment['reviewerId']
    archive = output / f'{reviewer}-pitayagrade-disease-annotation.zip'
    if archive.exists():
        raise FileExistsError(f'Refusing to overwrite {archive}')
    package_rows = []
    image_sources = []
    for row in assignment['rows']:
        source = (Path(root) / row['image']).resolve()
        root_resolved = Path(root).resolve()
        if not source.is_relative_to(root_resolved) or not source.is_file():
            raise FileNotFoundError(f'{row["id"]}: missing crop image')
        if hashlib.sha256(source.read_bytes()).hexdigest() != row.get('fileSha256'):
            raise ValueError(f'{row["id"]}: crop checksum mismatch')
        relative = f'images/{row["candidateSplit"]}/{source.name}'
        package_rows.append({**row, 'image': relative})
        image_sources.append((source, relative))
    instructions = f"""PitayaGrade disease polygon assignment: {reviewer}

1. Extract this ZIP permanently.
2. Open the Disease Annotation Desk URL supplied by the coordinator.
3. Load annotation-manifest.json.
4. Load this extracted folder as the local image folder.
5. Enter reviewer ID {reviewer}.
6. Follow the adviser-approved symptom and polygon guide.
7. Click around each visible symptom, select its class, and save the polygon.
8. Select the primary reviewed result, then Save annotation & next.
9. For an approved healthy crop, use Mark Healthy; do not draw a symptom region.
10. Export a draft after every work block and the completed manifest at 100%.

Folder names and model output do not prove a diagnosis or lesion boundary.
"""
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        bundle.writestr('annotation-manifest.json', json.dumps(package_rows, indent=2) + '\n')
        bundle.writestr('assignment-index.json', json.dumps(public, indent=2) + '\n')
        bundle.writestr('INSTRUCTIONS.txt', instructions)
        for source, relative in image_sources:
            bundle.write(source, relative)
    return archive


def create_packages(manifest, output, reviewers=3, root=ROOT):
    rows = json.loads(Path(manifest).read_text(encoding='utf-8'))
    assignments = assign_bundles(annotation_bundles(rows), reviewers)
    public = assignment_index(assignments)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output / 'assignment-index.json').write_text(json.dumps(public, indent=2) + '\n', encoding='utf-8')
    archives = []
    for index, assignment in enumerate(assignments, 1):
        assignment['reviewerId'] = f'mask-reviewer-{index:02d}'
        archives.append(write_package(output, assignment, public, root))
    return public, archives


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--reviewers', type=int, default=3)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.reviewers < 2:
        parser.error('At least two annotation reviewers are required')
    try:
        public, archives = create_packages(args.manifest, args.output, args.reviewers)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(json.dumps({'records': public['manifestRowCount'],
                      'assignments': [{key: item[key] for key in ('reviewerId', 'recordCount', 'splitCounts')}
                                      for item in public['assignments']],
                      'archives': [str(path) for path in archives]}, indent=2))


if __name__ == '__main__':
    main()
