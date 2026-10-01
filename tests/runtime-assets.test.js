const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { verifyRuntime } = require('../scripts/verify-runtime');
const { smokeInference } = require('../scripts/smoke-inference');
const www = path.resolve(__dirname, '..', 'www');

test('the bundled ONNX backend contains the matching JS, MJS and WASM files', () => {
  assert.equal(verifyRuntime(www).version, '1.19.0');
});

test('the actual bundled WASM backend executes the shipped detector', async () => {
  const result = await smokeInference();
  assert.deepEqual(result.input, [1, 3, 640, 640]);
  assert.deepEqual(result.output, [1, 8, 8400]);
  assert.equal(result.accuracyValidated, false);
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
