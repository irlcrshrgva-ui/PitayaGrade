const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { buildReport, reviewedEvidence, validEvidenceAudit, validReleaseAudit, validFinalResults,
  validFinalQualityEvaluation } = require('../scripts/release-readiness');

test('release gate reports evidence blockers without treating templates as results', () => {
  const report = buildReport(path.resolve(__dirname, '..'));
  const checks = Object.fromEntries(report.checks.map(check => [check.id, check]));
  assert.equal(checks['model-catalog'].passed, true);
  assert.equal(checks['android-debug-build'].passed,
    fs.existsSync(path.resolve(__dirname, '../android/app/build/outputs/apk/debug/app-debug.apk')));
  assert.equal(checks['model-assets'].passed, false);
  assert.match(checks['model-assets'].observed, /mobilenetv2-quality/);
  assert.equal(checks['reviewed-labels'].passed, false);
  assert.match(checks['reviewed-labels'].observed, /^3050\/3050/);
  assert.match(checks['reviewed-labels'].observed, /"quality":1553/);
  assert.match(checks['reviewed-labels'].observed, /"maturity":1497/);
  assert.equal(checks['evaluation-evidence'].passed, false);
  assert.match(checks['evaluation-evidence'].observed, /quality-onnx-evaluation:valid/);
  assert.equal(checks['android-release-signing'].passed, false);
  assert.equal(report.ready, false);
});

test('retained final quality evaluation is checksum-bound and complete', () => {
  assert.equal(validFinalQualityEvaluation(path.resolve(__dirname, '..')), true);
});

test('release review gate rejects assisted rows and accepts complete human task evidence', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-readiness-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const quality = path.join(directory, 'quality.json');
  const disease = path.join(directory, 'disease.json');
  const rows = [
    ...Array.from({length:1553}, (_, index) => ({id:`q-${index}`, task:'quality', reviewedLabel:'Grade A',
      reviewedSourceGroup:`qg-${index}`, reviewer:'reviewer-01', reviewedAt:'2026-10-25T10:00:00Z'})),
    ...Array.from({length:1497}, (_, index) => ({id:`m-${index}`, task:'maturity', reviewedLabel:'Mature Dragon Fruit',
      reviewedSourceGroup:`mg-${index}`, reviewer:'reviewer-01', reviewedAt:'2026-10-25T10:00:00Z'}))
  ];
  const diseaseRows = [{id:'d-1', task:'disease', reviewedLabel:'Sunburn', reviewedSourceGroup:'dg-1',
    reviewer:'reviewer-02', reviewedAt:'2026-10-25T10:00:00Z', annotationsComplete:true,
    annotationReviewer:'reviewer-02', annotationReviewedAt:'2026-10-25T10:00:00Z',
    regions:[{label:'Sunburn', polygon:[[0,0],[1,0],[1,1]]}]}];
  fs.writeFileSync(quality, JSON.stringify(rows));
  fs.writeFileSync(disease, JSON.stringify(diseaseRows));
  const qualityAudit = path.join(directory, 'quality-audit.json');
  const diseaseAudit = path.join(directory, 'disease-audit.json');
  fs.writeFileSync(qualityAudit, JSON.stringify({status:'human-reviewed-and-validated', validationErrors:0,
    frozenTrainingManifestSha256:crypto.createHash('sha256').update(fs.readFileSync(quality)).digest('hex')}));
  fs.writeFileSync(diseaseAudit, JSON.stringify({status:'human-annotated-and-validated', validationErrors:0,
    manifestSha256:crypto.createHash('sha256').update(fs.readFileSync(disease)).digest('hex')}));
  assert.equal(reviewedEvidence([quality, disease], [qualityAudit, diseaseAudit]).passed, true);
  rows[0].reviewer = 'AI-assisted-reviewer-01';
  fs.writeFileSync(quality, JSON.stringify(rows));
  const result = reviewedEvidence([quality, disease], [qualityAudit, diseaseAudit]);
  assert.equal(result.passed, false);
  assert.equal(result.genuine, 3050);
  assert.equal(result.total, 3051);
  assert.equal(result.auditsValid, false);
});

test('release review gate refuses sample-sized manifests even with valid checksums', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-readiness-small-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const manifest = path.join(directory, 'sample.json');
  fs.writeFileSync(manifest, JSON.stringify([{task:'quality', reviewedLabel:'Grade A',
    reviewedSourceGroup:'one', reviewer:'reviewer-01', reviewedAt:'2026-10-25T10:00:00Z'}]));
  const audit = path.join(directory, 'audit.json');
  fs.writeFileSync(audit, JSON.stringify({status:'human-reviewed-and-validated', validationErrors:0,
    frozenTrainingManifestSha256:crypto.createHash('sha256').update(fs.readFileSync(manifest)).digest('hex')}));
  assert.equal(reviewedEvidence([manifest], [audit]).passed, false);
});

test('release evidence audit is bound to the exact CSV files', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-audit-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const files = {};
  for (const name of ['model-evaluation.csv', 'device-test.csv', 'uat.csv']) {
    const content = 'header\nrow\n';
    fs.writeFileSync(path.join(directory, name), content);
    files[name] = { rows:1, sha256:crypto.createHash('sha256').update(content).digest('hex') };
  }
  const auditPath = path.join(directory, 'evidence-audit.json');
  fs.writeFileSync(auditPath, JSON.stringify({status:'pass', errors:[], files}));
  assert.equal(validEvidenceAudit(directory), true);
  const registry = [{id:'model-1', available:true, sha256:'a'.repeat(64)}];
  assert.equal(validEvidenceAudit(directory, registry), false);
  const runtime = path.join(directory, 'model-1-runtime.json');
  registry[0].outputContract = 'quality-softmax-v1';
  registry[0].preprocessing = 'rgb-imagenet-normalized';
  registry[0].inputSize = 224;
  fs.writeFileSync(runtime, JSON.stringify({modelId:'model-1', sha256:'a'.repeat(64), runtimeCompatible:true,
    outputContract:'quality-softmax-v1', preprocessing:'rgb-imagenet-normalized',
    inputShape:[1,3,224,224], outputShapes:[[1,4]]}));
  const runtimeRecord = {path:runtime, sha256:crypto.createHash('sha256').update(fs.readFileSync(runtime)).digest('hex')};
  fs.writeFileSync(auditPath, JSON.stringify({status:'pass', errors:[], files,
    modelAssets:{'model-1':{sha256:'a'.repeat(64), path:'private/model.onnx'}},
    runtimeVerifications:{'model-1':runtimeRecord}}));
  assert.equal(validEvidenceAudit(directory, registry), true);
  const reviewAudit = path.join(directory, 'review-audit.json');
  fs.writeFileSync(reviewAudit, '{}');
  assert.equal(validEvidenceAudit(directory, registry, [reviewAudit]), false);
  const reviewSha = crypto.createHash('sha256').update(fs.readFileSync(reviewAudit)).digest('hex');
  fs.writeFileSync(auditPath, JSON.stringify({status:'pass', errors:[], files,
    modelAssets:{'model-1':{sha256:'a'.repeat(64), path:'private/model.onnx'}},
    runtimeVerifications:{'model-1':runtimeRecord},
    reviewAudits:[{sha256:reviewSha}]}));
  assert.equal(validEvidenceAudit(directory, registry, [reviewAudit]), true);
  fs.appendFileSync(path.join(directory, 'uat.csv'), 'changed\n');
  assert.equal(validEvidenceAudit(directory), false);
});

test('signed release audit is bound to the APK and current source commit', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-release-audit-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const apk = path.join(directory, 'app-release.apk');
  fs.writeFileSync(apk, 'signed-fixture');
  const commit = require('node:child_process').execFileSync('git', ['rev-parse', 'HEAD'],
    {cwd:path.resolve(__dirname, '..'), encoding:'utf8'}).trim();
  const audit = path.join(directory, 'release-audit.json');
  const value = {status:'signed-release-verified', signatureVerified:true, sourceCommit:commit,
    apkPath:apk, apkSha256:crypto.createHash('sha256').update(fs.readFileSync(apk)).digest('hex'),
    certificateSha256:'a'.repeat(64), versionName:'1.0', versionCode:1};
  fs.writeFileSync(audit, JSON.stringify(value));
  assert.equal(validReleaseAudit(audit, path.resolve(__dirname, '..')), true);
  fs.appendFileSync(apk, 'changed');
  assert.equal(validReleaseAudit(audit, path.resolve(__dirname, '..')), false);
});

test('release signing reads secrets from the environment and verifies the APK', () => {
  const gradle = fs.readFileSync(path.resolve(__dirname, '../android/app/build.gradle'), 'utf8');
  const script = fs.readFileSync(path.resolve(__dirname, '../scripts/build-android-release.ps1'), 'utf8');
  for (const name of ['PITAYAGRADE_KEYSTORE_PATH', 'PITAYAGRADE_KEY_ALIAS',
    'PITAYAGRADE_STORE_PASSWORD', 'PITAYAGRADE_KEY_PASSWORD']) {
    assert.match(gradle, new RegExp(`System\\.getenv\\('${name}'\\)`));
  }
  assert.match(script, /apksigner verify --verbose --print-certs/);
  assert.match(script, /git status --porcelain/);
  assert.doesNotMatch(gradle, /storePassword\s+["'][^"']+["']/);
});

test('final result artifacts are bound to their evidence and traceability hashes', t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'pitayagrade-final-results-'));
  t.after(() => fs.rmSync(directory, { recursive:true, force:true }));
  const evidence = path.join(directory, 'evidence');
  const results = path.join(directory, 'results');
  fs.mkdirSync(evidence); fs.mkdirSync(results);
  const inputs = {};
  for (const name of ['model-evaluation.csv', 'device-test.csv', 'uat.csv']) {
    fs.writeFileSync(path.join(evidence, name), 'header\nrow\n');
    inputs[name] = {sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(evidence, name))).digest('hex')};
  }
  const audit = path.join(evidence, 'evidence-audit.json');
  fs.writeFileSync(audit, '{}');
  const outputs = {};
  for (const name of ['model-results.md','quality-model-results.svg','disease-model-results.svg',
    'device-test-summary.md','uat-summary.md','uat-results.svg']) {
    fs.writeFileSync(path.join(results, name), name);
    outputs[name] = crypto.createHash('sha256').update(fs.readFileSync(path.join(results, name))).digest('hex');
  }
  fs.writeFileSync(path.join(results, 'traceability.json'), JSON.stringify({
    status:'generated-from-validated-evidence',
    evidenceAudit:{path:audit, sha256:crypto.createHash('sha256').update(fs.readFileSync(audit)).digest('hex')},
    inputs, outputs
  }));
  assert.equal(validFinalResults(results, evidence), true);
  fs.appendFileSync(path.join(results, 'uat-results.svg'), 'changed');
  assert.equal(validFinalResults(results, evidence), false);
});
