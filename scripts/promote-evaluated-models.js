#!/usr/bin/env node
/* Promote only models bound to a passing final-evidence audit into the web registry. */
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { readRegistry, verifyModelRegistry } = require('./verify-model-registry');

function digest(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function quote(value) {
  return `'${String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

function renderRegistry(models) {
  const lines = ['/* Evaluated model assets become selectable only after this registry is updated. */',
    'const PitayaModelRegistry = Object.freeze(['];
  for (const model of models) {
    lines.push('  Object.freeze({');
    for (const [key, value] of Object.entries(model)) {
      if (key === 'classes') lines.push(`    classes: Object.freeze([${value.map(quote).join(', ')}])`);
      else if (typeof value === 'string') lines.push(`    ${key}: ${quote(value)},`);
      else if (value === null) lines.push(`    ${key}: null,`);
      else lines.push(`    ${key}: ${JSON.stringify(value)},`);
    }
    // Remove the last property comma for tidy, deterministic output.
    lines[lines.length - 1] = lines[lines.length - 1].replace(/,$/, '');
    lines.push('  }),');
  }
  lines[lines.length - 1] = lines[lines.length - 1].replace(/,$/, '');
  lines.push(']);', '');
  return lines.join('\n');
}

function validatedAssets(evidenceAudit, registry) {
  if (evidenceAudit.status !== 'pass' || !Array.isArray(evidenceAudit.errors) || evidenceAudit.errors.length) {
    throw new Error('Evidence audit must have passing status and no errors');
  }
  const expected = new Set(registry.map(model => model.id));
  const assets = evidenceAudit.modelAssets || {};
  const runtime = evidenceAudit.runtimeVerifications || {};
  if (Object.keys(assets).length !== expected.size || Object.keys(runtime).length !== expected.size ||
      [...expected].some(id => !assets[id] || !runtime[id])) {
    throw new Error('Evidence audit must contain one model asset and runtime verification for every registry entry');
  }
  return registry.map(model => {
    const asset = assets[model.id];
    const verification = runtime[model.id];
    const assetPath = path.resolve(asset.path || '');
    const verificationPath = path.resolve(verification.path || '');
    if (!fs.statSync(assetPath).isFile() || path.extname(assetPath).toLowerCase() !== '.onnx' ||
        digest(assetPath) !== asset.sha256) throw new Error(`${model.id}: evaluated model file/hash mismatch`);
    if (!fs.statSync(verificationPath).isFile() || digest(verificationPath) !== verification.sha256) {
      throw new Error(`${model.id}: runtime verification file/hash mismatch`);
    }
    const report = JSON.parse(fs.readFileSync(verificationPath, 'utf8'));
    if (report.modelId !== model.id || report.sha256 !== asset.sha256 || report.runtimeCompatible !== true ||
        report.outputContract !== model.outputContract || report.preprocessing !== model.preprocessing ||
        JSON.stringify(report.inputShape) !== JSON.stringify([1, 3, model.inputSize, model.inputSize]) ||
        !Array.isArray(report.outputShapes) || !report.outputShapes.length) {
      throw new Error(`${model.id}: runtime verification does not match the evaluated model`);
    }
    return { model, assetPath, sha256:asset.sha256, verificationPath, verificationSha256:verification.sha256 };
  });
}

function promote(evidenceAuditPath, outputAuditPath, projectRoot = path.resolve(__dirname, '..')) {
  evidenceAuditPath = path.resolve(evidenceAuditPath);
  outputAuditPath = path.resolve(outputAuditPath);
  if (fs.existsSync(outputAuditPath)) throw new Error('Promotion audit already exists; choose a new path');
  const sourceRegistry = path.join(projectRoot, 'js', 'model-registry.js');
  const webRegistry = path.join(projectRoot, 'www', 'js', 'model-registry.js');
  const modelDirectory = path.join(projectRoot, 'www', 'model');
  const registry = readRegistry(sourceRegistry);
  const evidenceAudit = JSON.parse(fs.readFileSync(evidenceAuditPath, 'utf8'));
  const candidates = validatedAssets(evidenceAudit, registry);
  const promoted = candidates.map(({ model, sha256 }) => ({ ...model, available:true, status:'bundled',
    modelPath:`model/${model.id}.onnx`, sha256 }));
  const registryText = renderRegistry(promoted);
  const registryBackup = fs.readFileSync(sourceRegistry);
  const webRegistryBackup = fs.readFileSync(webRegistry);
  const created = [];
  fs.mkdirSync(modelDirectory, { recursive:true });
  for (const candidate of candidates) {
    const destination = path.join(modelDirectory, `${candidate.model.id}.onnx`);
    if (fs.existsSync(destination) && digest(destination) !== candidate.sha256) {
      throw new Error(`${candidate.model.id}: destination already contains a different model`);
    }
  }
  try {
    for (const candidate of candidates) {
      const destination = path.join(modelDirectory, `${candidate.model.id}.onnx`);
      if (!fs.existsSync(destination)) {
        fs.copyFileSync(candidate.assetPath, destination, fs.constants.COPYFILE_EXCL);
        created.push(destination);
      }
    }
    fs.writeFileSync(sourceRegistry, registryText);
    fs.writeFileSync(webRegistry, registryText);
    verifyModelRegistry(path.join(projectRoot, 'www'));
    const result = {
      generatedAt: new Date().toISOString(), status:'evaluated-models-promoted',
      evidenceAudit:{ path:evidenceAuditPath, sha256:digest(evidenceAuditPath) },
      models:candidates.map(item => ({ id:item.model.id, sha256:item.sha256,
        runtimeVerificationSha256:item.verificationSha256,
        appPath:`www/model/${item.model.id}.onnx` })),
      sourceRegistrySha256:digest(sourceRegistry), webRegistrySha256:digest(webRegistry)
    };
    fs.mkdirSync(path.dirname(outputAuditPath), { recursive:true });
    fs.writeFileSync(outputAuditPath, JSON.stringify(result, null, 2) + '\n', { flag:'wx' });
    return result;
  } catch (error) {
    fs.writeFileSync(sourceRegistry, registryBackup);
    fs.writeFileSync(webRegistry, webRegistryBackup);
    for (const file of created) fs.rmSync(file, { force:true });
    throw error;
  }
}

function argumentsOf(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) values[argv[index]] = argv[index + 1];
  if (!values['--evidence-audit'] || !values['--output-audit'] || argv.length !== 4) {
    throw new Error('Usage: node scripts/promote-evaluated-models.js --evidence-audit <evidence-audit.json> --output-audit <promotion-audit.json>');
  }
  return values;
}

module.exports = { promote, renderRegistry, validatedAssets };
if (require.main === module) {
  try {
    const args = argumentsOf(process.argv.slice(2));
    console.log(JSON.stringify(promote(args['--evidence-audit'], args['--output-audit']), null, 2));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
