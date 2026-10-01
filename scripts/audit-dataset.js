// Read-only dataset audit. Does not relabel, move, or split research data.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
function files(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e =>
    e.isDirectory() ? files(path.join(dir, e.name)) : [path.join(dir, e.name)]);
}
const image = p => /\.(jpg|jpeg|png|bmp|webp)$/i.test(p);
const relative = p => path.relative(root, p).replaceAll('\\', '/');
const counts = {};
const hashes = new Map();
const frames = {};
for (const split of ['train', 'val', 'test']) {
  counts[split] = {};
  for (const p of files(path.join(root, 'dataset_prepared', split)).filter(image)) {
    const label = path.relative(path.join(root, 'dataset_prepared', split), p).split(path.sep)[0];
    counts[split][label] = (counts[split][label] || 0) + 1;
    const hash = crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
    if (!hashes.has(hash)) hashes.set(hash, []);
    hashes.get(hash).push({ split, label, path: relative(p) });
    if (/^frame_\d+/i.test(path.basename(p))) {
      frames[label] ||= {};
      frames[label][split] = (frames[label][split] || 0) + 1;
    }
  }
}
const crossSplit = [...hashes.values()].filter(g => new Set(g.map(x => x.split)).size > 1);
const conflicting = [...hashes.values()].filter(g => new Set(g.map(x => x.label)).size > 1);
const annotation = { files: 0, rows: 0, fixedBoxRows: 0, segmentationRows: 0, malformedRows: 0, classes: {} };
for (const p of files(path.join(root, 'yolo_dataset', 'labels')).filter(p => p.endsWith('.txt'))) {
  annotation.files++;
  for (const row of fs.readFileSync(p, 'utf8').trim().split(/\r?\n/).filter(Boolean)) {
    const nums = row.trim().split(/\s+/).map(Number);
    annotation.rows++;
    if (nums.some(n => !Number.isFinite(n)) || nums.length < 5) { annotation.malformedRows++; continue; }
    annotation.classes[nums[0]] = (annotation.classes[nums[0]] || 0) + 1;
    if (nums.length === 5 && nums.slice(1).every((n, i) => n === [0.5, 0.5, 0.88, 0.88][i])) annotation.fixedBoxRows++;
    if (nums.length >= 7 && nums.length % 2 === 1) annotation.segmentationRows++;
  }
}
const report = {
  generatedAt: new Date().toISOString(),
  scope: 'Existing prepared classification images and YOLO label files; byte-exact hashing only.',
  counts, uniqueImageHashes: hashes.size,
  crossSplitDuplicateGroups: crossSplit.length,
  crossSplitExamples: crossSplit.slice(0, 10),
  conflictingLabelGroups: conflicting.length,
  conflictingLabelExamples: conflicting.slice(0, 10),
  frameNamedImages: frames,
  annotation,
  limitations: [
    'No exact duplicates does not establish independence: adjacent video frames and transformed copies can differ in bytes.',
    'Frame names do not establish source video or fruit identity. Source-group metadata and expert labels are still required.',
    'Counts do not verify grade correctness, disease diagnosis, collection location, consent, licensing, or measured accuracy.',
    'Segmentation row counts check structure only, not annotation correctness.'
  ]
};
fs.mkdirSync(path.join(root, 'research'), { recursive: true });
fs.writeFileSync(path.join(root, 'research/dataset-audit.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report, null, 2));
