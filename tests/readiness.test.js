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
  fs.writeFileSync(quality, JSON.stringify([{task:'quality', reviewedLabel:'Grade A',
    reviewer:'reviewer-01', reviewedAt:'2026-10-25T10:00:00Z'}]));
  fs.writeFileSync(disease, JSON.stringify([{task:'disease', reviewedLabel:'Sunburn',
    reviewer:'reviewer-02', reviewedAt:'2026-10-25T10:00:00Z', annotationsComplete:true}]));
  assert.equal(reviewedEvidence([quality, disease]).passed, true);
  fs.writeFileSync(quality, JSON.stringify([{task:'quality', reviewedLabel:'Grade A',
    reviewer:'AI-assisted-reviewer-01', reviewedAt:'2026-10-25T10:00:00Z'}]));
  const result = reviewedEvidence([quality, disease]);
  assert.equal(result.passed, false);
  assert.equal(result.genuine, 1);
  assert.equal(result.total, 2);
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
  fs.writeFileSync(path.join(directory, 'evidence-audit.json'), JSON.stringify({status:'pass', errors:[], files}));
  assert.equal(validEvidenceAudit(directory), true);
  fs.appendFileSync(path.join(directory, 'uat.csv'), 'changed\n');
  assert.equal(validEvidenceAudit(directory), false);
});
