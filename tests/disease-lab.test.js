const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function lab({missing = false, corrupt = false} = {}) {
  const nodes = Object.fromEntries(['load', 'task', 'photo', 'preview', 'analyze', 'status', 'model-status', 'evaluation', 'results']
    .map(id => [id, {disabled: ['photo', 'analyze'].includes(id), children: [],
      replaceChildren() { this.children = []; }, append(x) { this.children.push(x); }, decode: async () => {}}]));
  nodes.task.value = 'disease'; nodes.photo.files = [{}];
  const bytes = new Uint8Array([1, 2, 3]);
  const report = {task: 'disease', modelSha256: corrupt ? 'bad' : crypto.createHash('sha256').update(bytes).digest('hex'),
    status: 'experimental-evaluated-image-classifier', classes: ['healthy_fruit', '<img onerror=alert(1)>', 'fruit_fungi'],
    preprocessing: {size: 160, mean: [.485, .456, .406], std: [.229, .224, .225]},
    test: {count: 30, metrics: {accuracy: .8, 'macro avg': {'f1-score': .79}}}};
  let created = 0, input;
  const context = {document: {getElementById: id => nodes[id], createElement: tag => tag === 'canvas' ?
    {getContext: () => ({drawImage() {}, getImageData: () => ({data: new Uint8ClampedArray(160 * 160 * 4).fill(255)})})} : {textContent: ''}},
    crypto: crypto.webcrypto, URL: {createObjectURL: () => 'blob:local', revokeObjectURL() {}},
    fetch: async url => ({ok: !missing, json: async () => report, arrayBuffer: async () => bytes.buffer}),
    ort: {env: {wasm: {}}, Tensor: class {constructor(type, data, dims) {Object.assign(this, {type, data, dims});} dispose() {}},
      InferenceSession: {create: async () => {created++; return {run: async feeds => {
        input = feeds.images; return {logits: {data: new Float32Array([0, 1000, 999]), dispose() {}}};
      }};}}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../js/disease-lab.js'), 'utf8'), context);
  return {nodes, created: () => created, input: () => input};
}

test('disease lab refuses missing or checksum-mismatched models', async () => {
  for (const options of [{missing: true}, {corrupt: true}]) {
    const page = lab(options);
    await page.nodes.load.onclick();
    assert.equal(page.created(), 0);
    assert.equal(page.nodes.photo.disabled, true);
    assert.equal(page.nodes.load.disabled, false);
    assert.match(page.nodes.status.textContent, /No evaluated model|contract mismatch/);
  }
});

test('disease lab normalizes RGB planes and renders stable scores as text', async () => {
  const page = lab();
  await page.nodes.load.onclick();
  await page.nodes.photo.onchange();
  await page.nodes.analyze.onclick();
  const input = page.input();
  assert.deepEqual(Array.from(input.dims), [1, 3, 160, 160]);
  assert.ok(Math.abs(input.data[0] - (1 - .485) / .229) < 1e-5);
  assert.ok(Math.abs(input.data[160 * 160] - (1 - .456) / .224) < 1e-5);
  assert.equal(page.nodes.results.children.length, 3);
  assert.match(page.nodes.results.children[0].textContent, /<img onerror=alert\(1\)>.*73.1% model score/);
  assert.match(page.nodes.status.textContent, /not a diagnosis/);
  assert.equal(page.nodes.analyze.disabled, false);
});
