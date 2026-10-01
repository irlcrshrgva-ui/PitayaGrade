// Download approved original images, verifying repository-provided SHA-256 hashes.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { Readable } = require('node:stream');
const { pipeline } = require('node:stream/promises');
const root = path.resolve(__dirname, '..');
async function download(name) {
  const repo = 'Project-AgML/dragonfruit_' + name + '_classification';
  const metadataResponse = await fetch('https://huggingface.co/api/datasets/' + repo + '/tree/main/raw');
  if (!metadataResponse.ok) throw new Error('Metadata HTTP ' + metadataResponse.status);
  const files = await metadataResponse.json();
  const entry = files.find(f => f.path === 'raw/train-00000-of-00001.parquet');
  if (!entry?.lfs?.oid) throw new Error('No verified original file found');
  const folder = path.join(root, 'dataset', 'public', name);
  fs.mkdirSync(folder, { recursive: true });
  const dest = path.join(folder, 'original.parquet');
  async function hash(file) {
    const digest = crypto.createHash('sha256');
    for await (const chunk of fs.createReadStream(file)) digest.update(chunk);
    return digest.digest('hex');
  }
  if (fs.existsSync(dest)) {
    if (await hash(dest) !== entry.lfs.oid) throw new Error('Existing file hash mismatch: ' + dest);
  } else {
    const response = await fetch('https://huggingface.co/datasets/' + repo + '/resolve/main/' + entry.path);
    if (!response.ok) throw new Error('Download HTTP ' + response.status);
    await pipeline(Readable.fromWeb(response.body), fs.createWriteStream(dest + '.partial'));
    if (await hash(dest + '.partial') !== entry.lfs.oid) throw new Error('Downloaded file hash mismatch');
    fs.renameSync(dest + '.partial', dest);
  }
  const record = { repository: repo, source: 'https://data.mendeley.com/datasets/2jpzbx8tm6/1',
    license: 'CC BY 4.0', sourcePath: entry.path, bytes: entry.size, sha256: entry.lfs.oid,
    downloadedAt: new Date().toISOString(), status: 'Downloaded for inspection; not approved ground-truth grades or diagnoses' };
  fs.writeFileSync(path.join(root, 'research', name + '-download.json'), JSON.stringify(record, null, 2) + '\n');
  console.log(name + ': verified ' + entry.size + ' bytes');
}
Promise.all(['quality', 'maturity'].map(download)).catch(error => { console.error(error); process.exitCode = 1; });
