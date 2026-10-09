const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
require('./verify-runtime').verifyRuntime(path.join(root, 'www'));
for (const directory of ['js', 'css']) {
  fs.cpSync(path.join(root, directory), path.join(root, 'www', directory), { recursive: true });
}
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .replace('src="www/ort.min.js"', 'src="ort.min.js"');
fs.writeFileSync(path.join(root, 'www/index.html'), html);
for (const filename of ['manifest.webmanifest', 'service-worker.js']) {
  fs.copyFileSync(path.join(root, filename), path.join(root, 'www', filename));
}
fs.cpSync(path.join(root, 'review-tool'), path.join(root, 'www', 'review-tool'), { recursive: true });
fs.mkdirSync(path.join(root, 'www', 'research'), { recursive: true });
for (const filename of ['public-review-manifest.json', 'source-group-suggestions-2026-10-10.json']) {
  fs.copyFileSync(path.join(root, 'research', filename), path.join(root, 'www', 'research', filename));
}
require('./verify-model-registry').verifyModelRegistry(path.join(root, 'www'));
console.log('Updated Capacitor web assets from existing sources.');
