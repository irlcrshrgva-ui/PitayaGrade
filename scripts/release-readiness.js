#!/usr/bin/env node
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const vm = require('node:vm');

function fileHash(file) {
  return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
}

function csvHasData(file) {
  if (!fs.existsSync(file)) return false;
  return fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(line => line.trim()).length > 1;
}

function loadRegistry(root) {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'js/model-registry.js'), 'utf8') + '\nthis.registry = PitayaModelRegistry;', context);
  return Array.from(context.registry, model => ({ ...model, classes: Array.from(model.classes) }));
}

function buildReport(root = path.resolve(__dirname, '..')) {
  const registry = loadRegistry(root);
  const intended = ['yolov8-nano', 'mobilenetv2-quality', 'resnet50-quality', 'efficientnet-b3-quality', 'yolov8n-disease-seg'];
  const available = registry.filter(model => model.available);
  const missing = intended.filter(id => !available.some(model => model.id === id));
  const verifiedAssets = available.every(model => {
    if (!model.modelPath || !model.sha256) return false;
    const file = path.join(root, 'www', model.modelPath);
    return fs.existsSync(file) && fileHash(file) === model.sha256;
  });

  const reviewFile = path.join(root, 'research/public-review-manifest.json');
  const reviews = fs.existsSync(reviewFile) ? JSON.parse(fs.readFileSync(reviewFile, 'utf8')) : [];
  const reviewed = reviews.filter(row => row.reviewedLabel && row.reviewer && row.reviewedAt);
  const reviewedByTask = reviewed.reduce((counts, row) => {
    counts[row.task] = (counts[row.task] || 0) + 1;
    return counts;
  }, {});

  const evidenceFiles = ['model-evaluation.csv', 'predictions.csv', 'device-test.csv', 'uat.csv'];
  const evidence = evidenceFiles.map(name => ({ name, complete: csvHasData(path.join(root, 'research/week4', name)) }));
  const gradle = fs.readFileSync(path.join(root, 'android/app/build.gradle'), 'utf8');
  const hasReleaseSigning = /signingConfigs\s*\{[\s\S]*?release\s*\{/m.test(gradle) &&
    /buildTypes\s*\{[\s\S]*?release\s*\{[\s\S]*?signingConfig/m.test(gradle);
  const debugApk = path.join(root, 'android/app/build/outputs/apk/debug/app-debug.apk');

  const checks = [
    {
      id: 'model-catalog', passed: intended.every(id => registry.some(model => model.id === id)),
      observed: `${registry.length}/${intended.length} planned entries present`,
      required: 'All manuscript/planned models are represented in the selector.'
    },
    {
      id: 'model-assets', passed: missing.length === 0 && verifiedAssets,
      observed: missing.length ? `Unavailable: ${missing.join(', ')}` : `${available.length} checksum-verified assets`,
      required: 'Every selectable quality and disease model has an evaluated, checksum-verified runtime asset.'
    },
    {
      id: 'reviewed-labels', passed: reviewed.length > 0 && ['quality', 'disease'].every(task => reviewedByTask[task] > 0),
      observed: `${reviewed.length}/${reviews.length} rows have reviewer, time, and target label (${JSON.stringify(reviewedByTask)})`,
      required: 'Genuine reviewed target labels exist for every research task.'
    },
    {
      id: 'evaluation-evidence', passed: evidence.every(item => item.complete),
      observed: evidence.map(item => `${item.name}:${item.complete ? 'complete' : 'missing'}`).join(', '),
      required: 'Completed predictions, held-out metrics, device tests, and UAT records replace the templates.'
    },
    {
      id: 'android-debug-build', passed: fs.existsSync(debugApk),
      observed: fs.existsSync(debugApk) ? `APK present; SHA-256 ${fileHash(debugApk)}` : 'Debug APK missing',
      required: 'A reproducible Android build exists for device testing.'
    },
    {
      id: 'android-release-signing', passed: hasReleaseSigning,
      observed: hasReleaseSigning ? 'Release signing configuration detected' : 'No release signing configuration detected',
      required: 'A team-controlled release key is configured outside version control.'
    }
  ];
  return { generatedAt: new Date().toISOString(), ready: checks.every(check => check.passed), checks };
}

function printReport(report) {
  console.log(`PitayaGrade release readiness: ${report.ready ? 'READY' : 'BLOCKED'}`);
  for (const check of report.checks) {
    console.log(`${check.passed ? '[PASS]' : '[BLOCK]'} ${check.id}: ${check.observed}`);
    if (!check.passed) console.log(`        Required: ${check.required}`);
  }
}

if (require.main === module) {
  const report = buildReport();
  if (process.argv.includes('--json')) console.log(JSON.stringify(report, null, 2));
  else printReport(report);
  process.exitCode = report.ready ? 0 : 2;
}

module.exports = { buildReport };
