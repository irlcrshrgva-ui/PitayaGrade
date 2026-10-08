const { test } = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { buildReport } = require('../scripts/release-readiness');

test('release gate reports evidence blockers without treating templates as results', () => {
  const report = buildReport(path.resolve(__dirname, '..'));
  const checks = Object.fromEntries(report.checks.map(check => [check.id, check]));
  assert.equal(checks['model-catalog'].passed, true);
  assert.equal(checks['android-debug-build'].passed, true);
  assert.equal(checks['model-assets'].passed, false);
  assert.match(checks['model-assets'].observed, /mobilenetv2-quality/);
  assert.equal(checks['reviewed-labels'].passed, false);
  assert.match(checks['reviewed-labels'].observed, /^0\/3050/);
  assert.equal(checks['evaluation-evidence'].passed, false);
  assert.equal(checks['android-release-signing'].passed, false);
  assert.equal(report.ready, false);
});
