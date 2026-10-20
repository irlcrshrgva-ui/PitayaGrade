"""Download checksum-verified Mendeley originals; preserve source labels."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile

BASE = 'https://data.mendeley.com/public-api/datasets/'
ROOT = Path(__file__).resolve().parents[1]


def get_json(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.mendeley-public-dataset.1+json'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(entry, destination):
    destination = Path(destination)
    details = entry['content_details']
    expected = details['sha256_hash']
    if destination.exists() and file_hash(destination) == expected:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    for attempt in range(4):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            headers = {'User-Agent': 'Mozilla/5.0'}
            if offset:
                headers['Range'] = f'bytes={offset}-'
            request = urllib.request.Request(details['download_url'], headers=headers)
            with urllib.request.urlopen(request, timeout=180) as response:
                append = offset and response.status == 206
                if append and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                    raise ValueError('Invalid range response')
                with partial.open('ab' if append else 'wb') as out:
                    for chunk in iter(lambda: response.read(1024 * 1024), b''):
                        out.write(chunk)
            if file_hash(partial) != expected:
                partial.unlink()
                raise ValueError('Checksum mismatch: ' + str(destination))
            partial.replace(destination)
            return
        except (OSError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def files(dataset, folder):
    result = []
    while True:
        page = get_json(f'{BASE}{dataset}/files?folder_id={folder}&version=1&$start={len(result)}&$limit=1000')
        result.extend(page)
        if len(page) < 1000:
            return result


def acquire(root, workers=12):
    root.mkdir(parents=True, exist_ok=True)
    # The publisher's original tree is explicitly distinct from its balanced tree.
    dataset = 'kpsywfwkrf'
    folders = get_json(f'{BASE}{dataset}/folders/1')
    lookup = {f['id']: f for f in folders}
    records = []
    tasks = []
    for folder in folders:
        names = [folder['name']]
        parent = folder.get('parent_id')
        while parent:
            names.insert(0, lookup[parent]['name'])
            parent = lookup[parent].get('parent_id')
        if len(names) != 3 or names[0] != 'Dragon Fruit':
            continue
        entries = files(dataset, folder['id'])
        print('/'.join(names), len(entries), flush=True)
        for entry in entries:
            # Never trust a remote filename as a filesystem path.
            dest = root / dataset / names[1] / names[2] / (entry['id'] + Path(entry['filename']).suffix.lower())
            tasks.append((entry, dest))
            records.append({'dataset': dataset, 'version': 1, 'organ': names[1], 'sourceLabel': names[2],
                            'path': dest.relative_to(root).as_posix(), 'sourceFilename': entry['filename'],
                            'sha256': entry['content_details']['sha256_hash'], 'fileId': entry['id']})
    (root / 'source-files.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(lambda pair: download(*pair), tasks))
    dataset = 'cfchfdpfw5'
    entries = files(dataset, 'root')
    (root / 'archive-files.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')
    for entry in entries:
        archive = root / dataset / (entry['id'] + '.zip')
        download(entry, archive)
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                target = (archive.parent / 'extracted' / member.filename).resolve()
                if not target.is_relative_to((archive.parent / 'extracted').resolve()):
                    raise ValueError('Unsafe archive path')
            for member in zipped.infolist():
                if member.filename.startswith('Dragon fruit and leaf/'):
                    zipped.extract(member, archive.parent / 'extracted')
    print('All publisher checksums verified.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT / 'dataset' / 'mendeley-disease')
    parser.add_argument('--workers', type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.workers <= 48:
        parser.error('workers must be between 1 and 48')
    acquire(args.root.resolve(), args.workers)
