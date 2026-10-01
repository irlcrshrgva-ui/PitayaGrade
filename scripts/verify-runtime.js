const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const required = ['ort.min.js', 'ort-wasm-simd-threaded.mjs', 'ort-wasm-simd-threaded.wasm', 'onnxruntime-LICENSE'];

function verifyRuntime(directory) {
  const record = JSON.parse(fs.readFileSync(path.join(directory, 'runtime-assets.json'), 'utf8'));
  if (record.package !== 'onnxruntime-web@1.19.0' || record.version !== '1.19.0') {
    throw new Error('Unsupported bundled ONNX runtime version');
  }
  for (const name of required) {
    const data = fs.readFileSync(path.join(directory, name));
    const digest = crypto.createHash('sha256').update(data).digest('hex');
    if (digest !== record.files?.[name]) throw new Error(`Runtime asset checksum mismatch: ${name}`);
  }
  const wasm = fs.readFileSync(path.join(directory, required[2]));
  if (!wasm.subarray(0, 8).equals(Buffer.from([0, 97, 115, 109, 1, 0, 0, 0]))) {
    throw new Error('Invalid bundled WebAssembly binary');
  }
  return record;
}

module.exports = { verifyRuntime };
if (require.main === module) {
  verifyRuntime(path.resolve(__dirname, '..', 'www'));
  console.log('Verified complete ONNX runtime bundle.');
}
