/* Execute the shipped model with its actual WASM backend. This checks wiring, not accuracy. */
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { verifyRuntime } = require('./verify-runtime');

async function smokeInference() {
  const www = path.resolve(__dirname, '..', 'www');
  verifyRuntime(www);
  const ort = require(path.join(www, 'ort.min.js'));
  ort.env.wasm.wasmPaths = pathToFileURL(www + path.sep).href;
  ort.env.wasm.numThreads = 1;
  const session = await ort.InferenceSession.create(new Uint8Array(fs.readFileSync(path.join(www, 'model', 'best.onnx'))), {
    executionProviders: ['wasm'], graphOptimizationLevel: 'all'
  });
  let input, outputs;
  try {
    input = new ort.Tensor('float32', new Float32Array(3 * 640 * 640), [1, 3, 640, 640]);
    outputs = await session.run({ [session.inputNames[0]]: input });
    const output = outputs[session.outputNames[0]];
    if (output.dims.length !== 3 || output.dims[0] !== 1 || output.dims[1] !== 8 || output.dims[2] < 1 ||
        !output.data.every(Number.isFinite)) throw new Error('Unsupported or invalid deployed detector output');
    const presenceSession = await ort.InferenceSession.create(new Uint8Array(fs.readFileSync(
      path.join(www, 'model', 'gate', 'dragonfruit-presence-gate.onnx'))), {
      executionProviders: ['wasm'], graphOptimizationLevel: 'all'
    });
    let presenceInput, presenceOutputs;
    try {
      presenceInput = new ort.Tensor('float32', new Float32Array(3 * 160 * 160), [1, 3, 160, 160]);
      presenceOutputs = await presenceSession.run({ [presenceSession.inputNames[0]]: presenceInput });
      const presenceOutput = presenceOutputs[presenceSession.outputNames[0]];
      if (presenceOutput.dims.length !== 2 || presenceOutput.dims[0] !== 1 || presenceOutput.dims[1] !== 2 ||
          !presenceOutput.data.every(Number.isFinite)) throw new Error('Invalid presence-gate output');
      return { input: input.dims, output: output.dims, presenceInput: presenceInput.dims,
        presenceOutput: presenceOutput.dims, backend: 'wasm', accuracyValidated: false };
    } finally {
      if (presenceInput) presenceInput.dispose();
      if (presenceOutputs) Object.values(presenceOutputs).forEach(tensor => tensor.dispose());
      await presenceSession.release();
    }
  } finally {
    if (input) input.dispose();
    if (outputs) Object.values(outputs).forEach(tensor => tensor.dispose());
    await session.release();
  }
}

module.exports = { smokeInference };
if (require.main === module) {
  smokeInference().then(result => console.log(JSON.stringify(result)))
    .catch(error => { console.error(error); process.exitCode = 1; });
}
