const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function digest(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function readRegistry(registryFile) {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(registryFile, 'utf8') + '\nthis.registry = PitayaModelRegistry;', context);
  return Array.from(context.registry, model => JSON.parse(JSON.stringify(model)));
}

function verifyModelRegistry(webRoot) {
  const registryFile = path.join(webRoot, 'js', 'model-registry.js');
  const models = readRegistry(registryFile);
  if (!models.length) throw new Error('Model registry is empty');
  const ids = new Set();
  for (const model of models) {
    if (!/^[a-z0-9][a-z0-9._-]*$/.test(model.id || '')) throw new Error('Invalid model id');
    if (ids.has(model.id)) throw new Error(`Duplicate model id: ${model.id}`);
    ids.add(model.id);
    if (!model.name || !model.role || !model.status || !model.outputContract ||
        !Number.isInteger(model.inputSize) || model.inputSize < 1 || !Array.isArray(model.classes) ||
        !model.classes.length || new Set(model.classes).size !== model.classes.length) {
      throw new Error(`Incomplete model contract: ${model.id}`);
    }
    if (model.available) {
      if (model.status !== 'bundled' || !model.modelPath || !/^[a-f0-9]{64}$/.test(model.sha256 || '')) {
        throw new Error(`Selectable model lacks a bundled asset contract: ${model.id}`);
      }
      const file = path.resolve(webRoot, model.modelPath);
      if (!file.startsWith(path.resolve(webRoot) + path.sep) || !fs.existsSync(file)) {
        throw new Error(`Selectable model asset is missing: ${model.id}`);
      }
      if (digest(file) !== model.sha256) throw new Error(`Model checksum mismatch: ${model.id}`);
    } else if (model.modelPath || model.sha256 || model.status === 'bundled') {
      throw new Error(`Unavailable model must not claim a bundled asset: ${model.id}`);
    }
  }
  if (!models.some(model => model.available)) throw new Error('No selectable models are bundled');
  return models;
}

module.exports = { readRegistry, verifyModelRegistry };
if (require.main === module) console.log(JSON.stringify(verifyModelRegistry(process.argv[2] || 'www'), null, 2));

