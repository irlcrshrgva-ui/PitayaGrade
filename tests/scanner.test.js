const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
function model(url, ort = {}, runtime = 'http://localhost/www/ort.min.js') {
  const context = { URL, document: { currentScript: { src: url }, querySelector: () => ({ src: runtime }) }, ort, console, performance };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'js/model-inference.js'), 'utf8') + '\nthis.model = ModelInference;', context);
  return context.model;
}
test('root and packaged pages use bundled assets', () => {
  assert.equal(model('http://localhost/js/model-inference.js').ASSET_BASE, 'http://localhost/www/');
  assert.equal(model('http://localhost/www/js/model-inference.js').ASSET_BASE, 'http://localhost/www/');
  assert.equal(model('https://localhost/js/model-inference.js', {}, 'https://localhost/ort.min.js').ASSET_BASE, 'https://localhost/');
  for (const folder of ['', 'www']) {
    const html = fs.readFileSync(path.join(root, folder, 'index.html'), 'utf8');
    for (const [, src] of html.matchAll(/<script src="([^"]+)"/g)) {
      assert.ok(!src.startsWith('http'), src);
      assert.ok(fs.existsSync(path.join(root, folder, src)), src);
    }
    assert.match(html, /js\/notifications.js/);
    assert.match(html, /js\/model-inference.js/);
  }
});
test('concurrent inference callers wait for one model load', async () => {
  let resolve, calls = 0;
  const pending = new Promise(r => { resolve = r; });
  const instance = model('http://localhost/www/js/model-inference.js', {
    env: { wasm: {} }, InferenceSession: { create: () => { calls++; return pending; } }
  });
  const first = instance.load();
  const second = instance.load();
  resolve({ inputNames: ['images'], outputNames: ['output0'] });
  assert.deepEqual(await Promise.all([first, second]), [true, true]);
  assert.equal(calls, 1);
});
test('postprocessing reads output dimensions and respects rejection threshold', () => {
  const instance = model('http://localhost/www/js/model-inference.js');
  const output = { dims: [1, 8, 2], data: new Float32Array(16) };
  output.data[12] = 0.9;
  output.data[0] = output.data[2] = 320;
  output.data[4] = output.data[6] = 320;
  assert.equal(instance._postprocess(output).grade, 'Grade C');
  assert.equal(instance._postprocess(output).box.x, 0.25);
  assert.equal(instance._postprocess(output).box.bottom, 0.75);
  instance.CONF_THRESHOLD = 0.95;
  assert.equal(instance._postprocess(output).isDragonFruit, false);
  instance.CONF_THRESHOLD = 0.30;
  output.data[12] = 0.1;
  assert.equal(instance._postprocess(output).isDragonFruit, false);
  assert.throws(() => instance._postprocess({ dims: [1, 6, 2] }), /Unsupported/);
});
test('model rejection cannot become a heuristic grade', () => {
  const context = { PitayaApp: { settings: {} } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'js/scanner.js'), 'utf8') + '\nthis.scanner = Scanner;', context);
  assert.equal(context.scanner._generateResult({ isDragonFruit: false }).isDragonFruit, false);
});
test('packaged modules match editable sources', () => {
  for (const name of fs.readdirSync(path.join(root, 'js'))) {
    assert.equal(fs.readFileSync(path.join(root, 'www/js', name), 'utf8'), fs.readFileSync(path.join(root, 'js', name), 'utf8'), name);
  }
});
