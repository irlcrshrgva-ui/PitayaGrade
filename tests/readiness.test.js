const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { buildReport, reviewedEvidence, validEvidenceAudit } = require('../scripts/release-readiness');

test('release gate reports evidence blockers without treating templates as results', () => {
  const report = buildReport(path.resolve(__dirname, '..'));
  const checks = Object.fromEntries(report.checks.map(check => [check.id, check]));
  assert.equal(checks['model-catalog'].passed, true);
  assert.equal(checks['android-debug-build'].passed,
    fs.existsSync(path.resolve(__dirname, '../android/app/build/outputs/apk/debug/app-debug.apk')));
  assert.equal(checks['model-assets'].passed, false);
  assert.match(checks['model-assets'].observed, /mobilenetv2-quality/);
  assert.equal(checks['reviewed-labels'].passed, false);
  assert.match(checks['reviewed-labels'].observed, /^0\/3050/);
  assert.equal(checks['evaluation-evidence'].passed, false);
  assert.equal(checks['android-release-signing'].passed, false);
  assert.equal(report.ready, false);
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
  fs.writeFileSync(auditPath, JSON.stringify({status:'pass', errors:[], files,
    modelAssets:{'model-1':{sha256:'a'.repeat(64), path:'private/model.onnx'}}}));
  assert.equal(validEvidenceAudit(directory, registry), true);
  fs.appendFileSync(path.join(directory, 'uat.csv'), 'changed\n');
  assert.equal(validEvidenceAudit(directory), false);
});
