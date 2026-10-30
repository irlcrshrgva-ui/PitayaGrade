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
  assert.match(source, /pathname\.includes\('\/model\/'\)/);
  assert.match(source, /pathname\.endsWith\('\.onnx'\)/);
  assert.match(source, /ort-wasm-simd-threaded\.wasm/);
  assert.match(source, /request\.mode === 'navigate'/);
});

test('packaged web files include exact PWA sources', () => {
  for (const name of ['manifest.webmanifest', 'service-worker.js', 'reset.html']) {
    assert.equal(
      fs.readFileSync(path.join(root, name), 'utf8'),
      fs.readFileSync(path.join(root, 'www', name), 'utf8')
    );
  }
});

test('reset route removes only PitayaGrade caches and preserves user records', () => {
  const source = fs.readFileSync(path.join(root, 'reset.html'), 'utf8');
  assert.match(source, /getRegistrations\(\)/);
  assert.match(source, /startsWith\('pitayagrade-web-'\)/);
  assert.match(source, /location\.replace/);
  assert.doesNotMatch(source, /localStorage\.(?:clear|removeItem)/);
});

test('web UI exposes install readiness and safely applies service-worker updates', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(root, 'js/app.js'), 'utf8');
  assert.match(html, /id="installAppBtn"/);
  assert.match(app, /beforeinstallprompt/);
  assert.match(app, /registration\.waiting/);
  assert.match(app, /update is ready\. Reload the page/);
  assert.match(app, /controllerchange/);
  assert.match(app, /Scanner\.isProcessing \|\| LiveScanner\.isActive/);
  assert.match(app, /window\.location\.reload\(\)/);
});

test('photo mode supports user-controlled crop, zoom and rotation before inference', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const scanner = fs.readFileSync(path.join(root, 'js/scanner.js'), 'utf8');
  const liveScanner = fs.readFileSync(path.join(root, 'js/live-scanner.js'), 'utf8');
  for (const id of ['imageAdjustPanel', 'imageZoom', 'rotateImageLeftBtn', 'rotateImageRightBtn', 'resetImageAdjustBtn']) {
    assert.match(html, new RegExp(`id="${id}"`));
  }
  assert.match(scanner, /pointermove/);
  assert.match(scanner, /_renderAdjustedImage\(\)/);
  assert.match(scanner, /context\.drawImage\(this\.sourceImage/);
  assert.match(scanner, /AI quality suggestion—not a final human grade/);
  assert.match(scanner, /openCurrentValidation/);
  assert.match(liveScanner, /Scanner\.loadDataUrl/);
});
