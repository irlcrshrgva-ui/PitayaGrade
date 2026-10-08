const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');

test('web manifest is installable under the GitHub Pages subpath', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'manifest.webmanifest'), 'utf8'));
  assert.equal(manifest.start_url, './');
  assert.equal(manifest.scope, './');
  assert.equal(manifest.display, 'standalone');
  assert.ok(manifest.icons.some(icon => icon.src === 'assets/logo.png'));
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /rel="manifest" href="manifest\.webmanifest"/);
});

test('service worker parses and versions local shell and inference caches', () => {
  const source = fs.readFileSync(path.join(root, 'service-worker.js'), 'utf8');
  new vm.Script(source, { filename: 'service-worker.js' });
  assert.match(source, /pitayagrade-web-\d{4}-\d{2}-\d{2}-\d+/);
  assert.match(source, /model\/best\.onnx/);
  assert.match(source, /ort-wasm-simd-threaded\.wasm/);
  assert.match(source, /request\.mode === 'navigate'/);
});

test('packaged web files include exact PWA sources', () => {
  for (const name of ['manifest.webmanifest', 'service-worker.js']) {
    assert.equal(
      fs.readFileSync(path.join(root, name), 'utf8'),
      fs.readFileSync(path.join(root, 'www', name), 'utf8')
    );
  }
});
