/* Verify the experimental classifier's asset contract and real WASM execution. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');

function verifyDiseaseAsset(www, task) {
  const directory = path.join(www, 'model', task);
  const report = JSON.parse(fs.readFileSync(path.join(directory, 'evaluation.json'), 'utf8'));
  const bytes = fs.readFileSync(path.join(directory, 'classifier.onnx'));
  if (crypto.createHash('sha256').update(bytes).digest('hex') !== report.modelSha256 ||
      report.status !== 'experimental-evaluated-image-classifier' || report.task !== task ||
      report.classes.length !== (task === 'disease' ? 8 : 4) ||
      report.preprocessing.size !== 160 || !Number.isFinite(report.test.metrics.accuracy) ||
      report.test.count < 1 || report.validation.count < 1)
    throw new Error('Invalid evaluated classifier: ' + task);
  return {report, bytes};
}

async function smokeDisease(www, task) {
  const {report, bytes} = verifyDiseaseAsset(www, task);
  const ort = require(path.join(www, 'ort.min.js'));
  ort.env.wasm.wasmPaths = pathToFileURL(www + path.sep).href;
  ort.env.wasm.numThreads = 1;
  const session = await ort.InferenceSession.create(new Uint8Array(bytes), {executionProviders: ['wasm']});
  let input, output;
  try {
    input = new ort.Tensor('float32', new Float32Array(3 * 160 * 160), [1, 3, 160, 160]);
    output = await session.run({images: input});
    const values = output.logits.data;
    if (values.length !== report.classes.length || !values.every(Number.isFinite))
      throw new Error('Invalid disease output');
    const error = Math.max(...values.map((v, i) => Math.abs(v - report.runtimeProbe.logits[i])));
    if (!(error < report.runtimeProbe.absoluteTolerance)) throw new Error('WASM/Python parity failed: ' + error);
    return {task, backend: 'wasm', maxAbsoluteError: error, classes: values.length};
  } finally {
    input?.dispose();
    if (output) Object.values(output).forEach(t => t.dispose());
    await session.release();
  }
}

module.exports = {verifyDiseaseAsset, smokeDisease};
if (require.main === module) (async () => {
  for (const task of ['disease', 'health'])
    console.log(JSON.stringify(await smokeDisease(path.resolve(__dirname, '..', 'www'), task)));
})().catch(error => { console.error(error); process.exitCode = 1; });
