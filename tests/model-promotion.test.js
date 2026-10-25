const test = require('node:test');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { promote } = require('../scripts/promote-evaluated-models');
const { readRegistry, verifyModelRegistry } = require('../scripts/verify-model-registry');

const root = path.resolve(__dirname, '..');
const hash = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

function fixture(t) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-promotion-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  fs.mkdirSync(path.join(directory, 'js'), { recursive:true });
  fs.mkdirSync(path.join(directory, 'www', 'js'), { recursive:true });
  fs.mkdirSync(path.join(directory, 'www', 'model'), { recursive:true });
  for (const target of [path.join(directory, 'js/model-registry.js'), path.join(directory, 'www/js/model-registry.js')]) {
    fs.copyFileSync(path.join(root, 'js/model-registry.js'), target);
  }
  const registry = readRegistry(path.join(directory, 'js/model-registry.js'));
  const audit = { status:'pass', errors:[], modelAssets:{}, runtimeVerifications:{} };
  for (const model of registry) {
    const asset = path.join(directory, `${model.id}.onnx`);
    fs.writeFileSync(asset, `onnx-${model.id}`);
    const sha256 = hash(asset);
    const report = path.join(directory, `${model.id}-runtime.json`);
    fs.writeFileSync(report, JSON.stringify({modelId:model.id, sha256, runtimeCompatible:true,
      outputContract:model.outputContract, preprocessing:model.preprocessing,
      inputShape:[1,3,model.inputSize,model.inputSize], outputShapes:[[1,4]]}));
    audit.modelAssets[model.id] = {path:asset, sha256};
    audit.runtimeVerifications[model.id] = {path:report, sha256:hash(report)};
  }
  const auditPath = path.join(directory, 'evidence-audit.json');
  fs.writeFileSync(auditPath, JSON.stringify(audit));
  return { directory, audit, auditPath };
}

test('promotion enables every exact audited asset and writes retained evidence', t => {
  const value = fixture(t);
  const output = path.join(value.directory, 'private', 'promotion-audit.json');
  const result = promote(value.auditPath, output, value.directory);
  assert.equal(result.models.length, 5);
  assert.ok(fs.existsSync(output));
  const models = verifyModelRegistry(path.join(value.directory, 'www'));
  assert.ok(models.every(model => model.available && model.status === 'bundled'));
  assert.ok(models.every(model => hash(path.join(value.directory, 'www', model.modelPath)) === model.sha256));
});

test('promotion refuses a runtime report for a different model hash without mutating the registry', t => {
  const value = fixture(t);
  const original = fs.readFileSync(path.join(value.directory, 'js/model-registry.js'), 'utf8');
  const id = Object.keys(value.audit.runtimeVerifications)[0];
  const report = value.audit.runtimeVerifications[id].path;
  fs.writeFileSync(report, JSON.stringify({modelId:id, sha256:'0'.repeat(64), runtimeCompatible:true}));
  value.audit.runtimeVerifications[id].sha256 = hash(report);
  fs.writeFileSync(value.auditPath, JSON.stringify(value.audit));
  assert.throws(() => promote(value.auditPath, path.join(value.directory, 'promotion.json'), value.directory),
    /runtime verification does not match/);
  assert.equal(fs.readFileSync(path.join(value.directory, 'js/model-registry.js'), 'utf8'), original);
  assert.equal(fs.readdirSync(path.join(value.directory, 'www/model')).length, 0);
});
