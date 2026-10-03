const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
function model(url, ort = {}, runtime = 'http://localhost/www/ort.min.js', pixels = [255, 128, 0, 255]) {
  const document = {
    currentScript: { src: url },
    querySelector: () => ({ src: runtime }),
    createElement: () => ({ getContext: () => ({ drawImage() {}, getImageData: () => ({ data: pixels }) }) })
  };
  const context = { URL, document, ort, console, performance };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'js/model-registry.js'), 'utf8'), context);
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
test('only verified bundled models can be selected', () => {
  const instance = model('http://localhost/www/js/model-inference.js');
  assert.equal(instance.getModelCatalog().length, 5);
  assert.deepEqual(Array.from(instance.getAvailableModels(), item => item.id), ['yolov8-nano']);
  assert.equal(instance.selectModel('efficientnet-b3-quality'), false);
  const disease = instance.MODELS.find(item => item.id === 'yolov8n-disease-seg');
  disease.available = true;
  assert.equal(instance.canSelectModel(disease), false);
  assert.equal(instance.selectModel(disease.id), false);
  assert.equal(instance.getSelectedModel().id, 'yolov8-nano');
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
test('quality classifier postprocessing accepts probabilities and logits', () => {
  const instance = model('http://localhost/www/js/model-inference.js');
  const contract = {
    outputContract: 'quality-softmax-v1',
    classes: ['Grade A', 'Grade B', 'Grade C', 'Reject']
  };
  const probabilities = instance._postprocess({
    dims: [1, 4], data: new Float32Array([0.05, 0.75, 0.1, 0.1])
  }, contract);
  assert.equal(probabilities.grade, 'Grade B');
  assert.equal(probabilities.classificationOnly, true);
  const logits = instance._postprocess({
    dims: [1, 4], data: new Float32Array([-2, -1, 4, 0])
  }, contract);
  assert.equal(logits.grade, 'Grade C');
  assert.ok(logits.confidence > 0.95);
  assert.throws(() => instance._postprocess({ dims: [1, 3], data: new Float32Array(3) }, contract), /Unsupported/);
});
test('preprocessing follows zero-to-one and ImageNet registry contracts', () => {
  class Tensor {
    constructor(type, data, dims) { this.type = type; this.data = data; this.dims = dims; }
  }
  const instance = model('http://localhost/www/js/model-inference.js', { Tensor });
  const scaled = instance._preprocess({}, { inputSize:1, preprocessing:'rgb-zero-to-one' });
  assert.equal(scaled.data[0], 1);
  assert.ok(Math.abs(scaled.data[1] - 128 / 255) < 1e-6);
  assert.equal(scaled.data[2], 0);
  const normalized = instance._preprocess({}, { inputSize:1, preprocessing:'rgb-imagenet-normalized' });
  assert.ok(Math.abs(normalized.data[0] - (1 - 0.485) / 0.229) < 1e-6);
  assert.ok(Math.abs(normalized.data[1] - (128 / 255 - 0.456) / 0.224) < 1e-6);
  assert.throws(() => instance._preprocess({}, { inputSize:1, preprocessing:'unknown' }), /Unsupported preprocessing/);
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
