const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const modelPath = path.join(root, 'www', 'model', 'quality', 'efficientnet-b3.onnx');
const partPaths = [
  `${modelPath}.part-01`,
  `${modelPath}.part-02`,
];
const expectedSha256 = '89046c5a92df279b7cd81f3251d0de102b4742db9fa2cb72728bbd63344c722a';
const expectedBytes = 43535591;

function digest(buffer) {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

if (partPaths.every(file => fs.existsSync(file))) {
  const model = Buffer.concat(partPaths.map(file => fs.readFileSync(file)));
  const actualSha256 = digest(model);
  if (model.length !== expectedBytes || actualSha256 !== expectedSha256) {
    throw new Error(`EfficientNet-B3 parts failed verification (bytes=${model.length}, sha256=${actualSha256})`);
  }
  fs.writeFileSync(modelPath, model);
} else if (!fs.existsSync(modelPath)) {
  throw new Error('EfficientNet-B3 ONNX is absent and its two upload parts are unavailable.');
}

const bundled = fs.readFileSync(modelPath);
const actualSha256 = digest(bundled);
if (bundled.length !== expectedBytes || actualSha256 !== expectedSha256) {
  throw new Error(`Bundled EfficientNet-B3 failed verification (bytes=${bundled.length}, sha256=${actualSha256})`);
}
console.log(`Verified EfficientNet-B3 v7 (${bundled.length} bytes, sha256 ${actualSha256}).`);
