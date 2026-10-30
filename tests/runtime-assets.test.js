const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { verifyRuntime } = require('../scripts/verify-runtime');
const { smokeInference } = require('../scripts/smoke-inference');
const { verifyModelRegistry } = require('../scripts/verify-model-registry');
const { validateContract, verifyCandidate, writeVerification } = require('../scripts/verify-model-candidate');
const www = path.resolve(__dirname, '..', 'www');

test('the bundled ONNX backend contains the matching JS, MJS and WASM files', () => {
  assert.equal(verifyRuntime(www).version, '1.19.0');
});

test('the model catalog exposes only checksum-verified bundled assets', () => {
  const models = verifyModelRegistry(www);
  assert.equal(models.length, 6);
  assert.deepEqual(models.filter(model => model.available).map(model => model.id), [
    'dragonfruit-presence-gate', 'yolov8-nano', 'mobilenetv2-quality', 'resnet50-quality', 'efficientnet-b3-quality'
  ]);
  const gate = models.find(model => model.id === 'dragonfruit-presence-gate');
  assert.equal(gate.outputContract, 'binary-presence-logits-v1');
  assert.equal(gate.evaluation.specificity, 0.996);
  assert.equal(models.find(model => model.id === 'efficientnet-b3-quality').inputSize, 224);
  assert.equal(models.find(model => model.id === 'efficientnet-b3-quality').preprocessing, 'rgb-imagenet-normalized');
  assert.equal(models.find(model => model.id === 'resnet50-quality').evaluation.sampleCount, 226);
  assert.equal(models.find(model => model.id === 'resnet50-quality').evaluation.accuracy, 0.7433628319);
  assert.equal(models.find(model => model.id === 'yolov8n-disease-seg').available, false);
});

test('model registry validation rejects a forged bundled checksum', t => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pitaya-models-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  fs.mkdirSync(path.join(temp, 'js'), { recursive: true });
  fs.mkdirSync(path.join(temp, 'model'), { recursive: true });
  fs.mkdirSync(path.join(temp, 'model', 'gate'), { recursive: true });
  const registry = fs.readFileSync(path.join(www, 'js', 'model-registry.js'), 'utf8')
    .replace(/sha256: '[a-f0-9]{64}'/, `sha256: '${'0'.repeat(64)}'`);
  fs.writeFileSync(path.join(temp, 'js', 'model-registry.js'), registry);
  fs.copyFileSync(path.join(www, 'model', 'best.onnx'), path.join(temp, 'model', 'best.onnx'));
  fs.copyFileSync(path.join(www, 'model', 'gate', 'dragonfruit-presence-gate.onnx'),
    path.join(temp, 'model', 'gate', 'dragonfruit-presence-gate.onnx'));
  assert.throws(() => verifyModelRegistry(temp), /checksum mismatch/);
});

test('the actual bundled WASM backend executes the shipped detector', async () => {
  const result = await smokeInference();
  assert.deepEqual(result.input, [1, 3, 640, 640]);
  assert.deepEqual(result.output, [1, 8, 8400]);
  assert.deepEqual(result.presenceInput, [1, 3, 160, 160]);
  assert.deepEqual(result.presenceOutput, [1, 2]);
  assert.equal(result.accuracyValidated, false);
});

test('candidate verifier checks the actual bundled model contract', async () => {
  const result = await verifyCandidate('yolov8-nano', path.join(www, 'model', 'best.onnx'));
  assert.deepEqual(result.inputShape, [1, 3, 640, 640]);
  assert.deepEqual(result.outputShapes, [[1, 8, 8400]]);
  assert.equal(result.runtimeCompatible, true);
  assert.equal(result.accuracyValidated, false);
});

test('candidate verifier writes one immutable runtime report', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitaya-verification-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const output = path.join(directory, 'verification.json');
  const result = {modelId:'model', sha256:'a'.repeat(64), runtimeCompatible:true};
  writeVerification(output, result);
  assert.deepEqual(JSON.parse(fs.readFileSync(output, 'utf8')), result);
  assert.throws(() => writeVerification(output, result), /EEXIST/);
});

test('candidate verifier rejects incompatible quality and segmentation outputs', () => {
  const quality = { outputContract:'quality-softmax-v1', classes:['A','B','C','D'] };
  assert.deepEqual(validateContract(quality, { output:{ dims:[1,4], data:new Float32Array(4) } }), [[1,4]]);
  assert.throws(() => validateContract(quality, { output:{ dims:[1,3], data:new Float32Array(3) } }), /Expected quality/);
  const segmenter = { outputContract:'yolov8-disease-segmentation-v1',
    classes:['Anthracnose','Stem Canker','Soft Rot','Pest Damage','Sunburn','Fungal Spots'] };
  assert.deepEqual(validateContract(segmenter, {
    detections:{ dims:[1,42,336], data:new Float32Array(42 * 336) },
    prototypes:{ dims:[1,32,32,32], data:new Float32Array(32 * 32 * 32) }
  }), [[1,42,336], [1,32,32,32]]);
  assert.throws(() => validateContract(segmenter, {
    output:{ dims:[1,43,336], data:new Float32Array(43 * 336) }
  }), /mask prototypes/);
});

test('build validation rejects the missing MJS dependency and corrupt runtime files', t => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pitaya-runtime-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const record = verifyRuntime(www);
  fs.copyFileSync(path.join(www, 'runtime-assets.json'), path.join(temp, 'runtime-assets.json'));
  for (const name of Object.keys(record.files)) fs.copyFileSync(path.join(www, name), path.join(temp, name));
  fs.unlinkSync(path.join(temp, 'ort-wasm-simd-threaded.mjs'));
  assert.throws(() => verifyRuntime(temp), /ENOENT/);
  fs.writeFileSync(path.join(temp, 'ort-wasm-simd-threaded.mjs'), 'incomplete module');
  assert.throws(() => verifyRuntime(temp), /checksum mismatch/);
});

test('invalid WASM headers cannot pass even with a matching manifest hash', t => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'pitaya-runtime-'));
  t.after(() => fs.rmSync(temp, { recursive: true, force: true }));
  const record = verifyRuntime(www);
  for (const name of Object.keys(record.files)) fs.copyFileSync(path.join(www, name), path.join(temp, name));
  const data = Buffer.from('this is not wasm');
  fs.writeFileSync(path.join(temp, 'ort-wasm-simd-threaded.wasm'), data);
  record.files['ort-wasm-simd-threaded.wasm'] = crypto.createHash('sha256').update(data).digest('hex');
  fs.writeFileSync(path.join(temp, 'runtime-assets.json'), JSON.stringify(record));
  assert.throws(() => verifyRuntime(temp), /WebAssembly binary/);
});
