/* Check an ONNX candidate against its declared PitayaGrade runtime contract.
   This proves load/shape compatibility only; it never proves model accuracy. */
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { readRegistry } = require('./verify-model-registry');
const { verifyRuntime } = require('./verify-runtime');

function digest(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function validateContract(model, outputs) {
  const tensors = Object.values(outputs || {});
  if (!tensors.length) throw new Error('Model produced no outputs');
  if (tensors.some(tensor => !tensor.data || !Array.from(tensor.data).every(Number.isFinite))) {
    throw new Error('Model produced non-finite output');
  }
  if (model.outputContract === 'quality-softmax-v1') {
    const tensor = tensors[0];
    const dims = Array.from(tensor.dims || []);
    const count = model.classes.length;
    if (!((dims.length === 1 && dims[0] === count) ||
      (dims.length === 2 && dims[0] === 1 && dims[1] === count))) {
      throw new Error(`Expected quality output [1,${count}]`);
    }
  } else if (model.outputContract === 'yolov8-grade-detection-v1') {
    const dims = Array.from(tensors[0].dims || []);
    if (dims.length !== 3 || dims[0] !== 1 || dims[1] !== 4 + model.classes.length || dims[2] < 1) {
      throw new Error(`Expected YOLO grade output [1,${4 + model.classes.length},N]`);
    }
  } else if (model.outputContract === 'yolov8-disease-segmentation-v1') {
    const detection = tensors.find(tensor => tensor.dims && tensor.dims.length === 3 &&
      tensor.dims[0] === 1 && tensor.dims[1] >= 4 + model.classes.length && tensor.dims[2] > 0);
    const prototypes = tensors.find(tensor => tensor.dims && tensor.dims.length === 4 &&
      tensor.dims[0] === 1 && tensor.dims[1] > 0 && tensor.dims[2] > 0 && tensor.dims[3] > 0);
    if (!detection || !prototypes) throw new Error('Expected YOLO segmentation detections and mask prototypes');
  } else {
    throw new Error(`Unsupported output contract: ${model.outputContract}`);
  }
  return tensors.map(tensor => Array.from(tensor.dims));
}

async function verifyCandidate(modelId, candidatePath, projectRoot = path.resolve(__dirname, '..')) {
  if (!modelId || !candidatePath) throw new Error('Usage: node scripts/verify-model-candidate.js <model-id> <candidate.onnx>');
  const registry = readRegistry(path.join(projectRoot, 'js', 'model-registry.js'));
  const model = registry.find(item => item.id === modelId);
  if (!model) throw new Error(`Unknown registry model: ${modelId}`);
  const candidate = path.resolve(candidatePath);
  if (path.extname(candidate).toLowerCase() !== '.onnx' || !fs.statSync(candidate).isFile()) {
    throw new Error('Candidate must be an existing .onnx file');
  }
  const webRoot = path.join(projectRoot, 'www');
  verifyRuntime(webRoot);
  const ort = require(path.join(webRoot, 'ort.min.js'));
  ort.env.wasm.wasmPaths = pathToFileURL(webRoot + path.sep).href;
  ort.env.wasm.numThreads = 1;
  const session = await ort.InferenceSession.create(new Uint8Array(fs.readFileSync(candidate)), {
    executionProviders: ['wasm'], graphOptimizationLevel: 'all'
  });
  let input;
  let outputs;
  try {
    input = new ort.Tensor('float32', new Float32Array(3 * model.inputSize * model.inputSize),
      [1, 3, model.inputSize, model.inputSize]);
    outputs = await session.run({ [session.inputNames[0]]: input });
    const outputShapes = validateContract(model, outputs);
    return {
      modelId: model.id,
      outputContract: model.outputContract,
      inputShape: Array.from(input.dims),
      outputShapes,
      preprocessing: model.preprocessing,
      sha256: digest(candidate),
      runtimeCompatible: true,
      accuracyValidated: false
    };
  } finally {
    if (input) input.dispose();
    if (outputs) Object.values(outputs).forEach(tensor => tensor.dispose());
    await session.release();
  }
}

module.exports = { validateContract, verifyCandidate };
if (require.main === module) {
  verifyCandidate(process.argv[2], process.argv[3]).then(result => console.log(JSON.stringify(result, null, 2)))
    .catch(error => { console.error(error.message); process.exitCode = 1; });
}
