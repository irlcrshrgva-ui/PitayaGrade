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

function validEvidenceAudit(directory, registry = [], reviewAudits = []) {
  const auditPath = path.join(directory, 'evidence-audit.json');
  if (!fs.existsSync(auditPath)) return false;
  try {
    const audit = JSON.parse(fs.readFileSync(auditPath, 'utf8'));
    if (audit.status !== 'pass' || !Array.isArray(audit.errors) || audit.errors.length) return false;
    const filesValid = ['model-evaluation.csv', 'device-test.csv', 'uat.csv'].every(name => {
      const file = path.join(directory, name);
      return fs.existsSync(file) && audit.files?.[name]?.sha256 === fileHash(file) &&
        Number(audit.files[name].rows) > 0;
    });
    const assetsValid = !registry.length || registry.every(model =>
      model.available && audit.modelAssets?.[model.id]?.sha256 === model.sha256);
    const approvedReviewAudits = new Set((audit.reviewAudits || []).map(item => item.sha256));
    const reviewsValid = !reviewAudits.length || reviewAudits.every(file =>
      fs.existsSync(file) && approvedReviewAudits.has(fileHash(file)));
    return filesValid && assetsValid && reviewsValid;
  } catch {
    return false;
  }
}

function loadRegistry(root) {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(root, 'js/model-registry.js'), 'utf8') + '\nthis.registry = PitayaModelRegistry;', context);
  return Array.from(context.registry, model => ({ ...model, classes: Array.from(model.classes) }));
}

const REQUIRED_REVIEW_COUNTS = Object.freeze({ quality: 1553, maturity: 1497 });

function validReviewAudits(files, auditFiles) {
  if (!files.length || !auditFiles.length) return false;
  const approved = new Set();
  try {
    for (const auditFile of auditFiles) {
      const audit = JSON.parse(fs.readFileSync(auditFile, 'utf8'));
      if (!['human-reviewed-and-validated', 'human-annotated-and-validated'].includes(audit.status) ||
          audit.validationErrors !== 0) return false;
      for (const key of ['frozenTrainingManifestSha256', 'reviewedManifestSha256', 'manifestSha256']) {
        if (/^[a-f0-9]{64}$/.test(audit[key] || '')) approved.add(audit[key]);
      }
    }
  } catch {
    return false;
  }
  return files.every(file => fs.existsSync(file) && approved.has(fileHash(file)));
}

function validReviewedRow(row) {
  const reviewer = String(row.reviewer || '');
  const reviewedAt = String(row.reviewedAt || '');
  if (!row.reviewedLabel || !reviewer || !reviewedAt || reviewer.startsWith('AI-assisted-') ||
      !row.reviewedSourceGroup) return false;
  const timestamp = Date.parse(reviewedAt);
  if (!Number.isFinite(timestamp) || !/(?:Z|[+-]\d\d:\d\d)$/.test(reviewedAt)) return false;
  if (row.task !== 'disease') return ['quality', 'maturity'].includes(row.task);
  const annotationReviewer = String(row.annotationReviewer || '');
  const annotationReviewedAt = String(row.annotationReviewedAt || '');
  return row.annotationsComplete === true && Array.isArray(row.regions) &&
    annotationReviewer === reviewer && annotationReviewedAt === reviewedAt &&
    !annotationReviewer.startsWith('AI-assisted-');
}

function reviewedEvidence(files, auditFiles = []) {
  const rows = files.flatMap(file => fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : []);
  const genuine = rows.filter(validReviewedRow);
  const reviewedByTask = genuine.reduce((counts, row) => {
    counts[row.task] = (counts[row.task] || 0) + 1;
    return counts;
  }, {});
  const auditsValid = validReviewAudits(files, auditFiles);
  return {
    total: rows.length,
    genuine: genuine.length,
    reviewedByTask,
    auditsValid,
    passed: rows.length > 0 && genuine.length === rows.length && auditsValid &&
      Object.entries(REQUIRED_REVIEW_COUNTS).every(([task, count]) => reviewedByTask[task] === count) &&
      reviewedByTask.disease > 0
  };
}

function buildReport(root = path.resolve(__dirname, '..'), options = {}) {
  const registry = loadRegistry(root);
  const intended = ['yolov8-nano', 'mobilenetv2-quality', 'resnet50-quality', 'efficientnet-b3-quality', 'yolov8n-disease-seg'];
  const available = registry.filter(model => model.available);
  const missing = intended.filter(id => !available.some(model => model.id === id));
  const verifiedAssets = available.every(model => {
    if (!model.modelPath || !model.sha256) return false;
    const file = path.join(root, 'www', model.modelPath);
    return fs.existsSync(file) && fileHash(file) === model.sha256;
  });

  const reviewFiles = options.reviewManifests || [path.join(root, 'research/public-review-manifest.json')];
  const review = reviewedEvidence(reviewFiles, options.reviewAudits || []);

  const evidenceFiles = ['model-evaluation.csv', 'predictions.csv', 'device-test.csv', 'uat.csv'];
  const evidenceDir = options.evidenceDir || path.join(root, 'research/week4');
  const evidence = evidenceFiles.map(name => ({ name, complete: csvHasData(path.join(evidenceDir, name)) }));
  const auditValid = validEvidenceAudit(evidenceDir, registry, options.reviewAudits || []);
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
      id: 'reviewed-labels', passed: review.passed,
      observed: `${review.genuine}/${review.total} rows have genuine reviewer, time, target label, and complete annotations where required (${JSON.stringify(review.reviewedByTask)}); finalization audits:${review.auditsValid ? 'valid' : 'missing/invalid'}`,
      required: 'All 1,553 quality and 1,497 maturity rows plus the complete disease manifest are human-reviewed and bound to valid finalization audits.'
    },
    {
      id: 'evaluation-evidence', passed: evidence.every(item => item.complete) && auditValid,
      observed: evidence.map(item => `${item.name}:${item.complete ? 'complete' : 'missing'}`).join(', ') +
        `, evidence-audit.json:${auditValid ? 'valid' : 'missing/invalid'}`,
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
  const args = process.argv.slice(2);
  const reviewManifests = [];
  const reviewAudits = [];
  let evidenceDir;
  for (let index = 0; index < args.length; index += 1) {
    if (args[index] === '--review-manifest') reviewManifests.push(path.resolve(args[++index] || ''));
    else if (args[index] === '--review-audit') reviewAudits.push(path.resolve(args[++index] || ''));
    else if (args[index] === '--evidence-dir') evidenceDir = path.resolve(args[++index] || '');
    else if (args[index] !== '--json') throw new Error(`Unknown argument: ${args[index]}`);
  }
  const report = buildReport(path.resolve(__dirname, '..'), {
    ...(reviewManifests.length ? { reviewManifests } : {}),
    ...(reviewAudits.length ? { reviewAudits } : {}),
    ...(evidenceDir ? { evidenceDir } : {})
  });
  if (args.includes('--json')) console.log(JSON.stringify(report, null, 2));
  else printReport(report);
  process.exitCode = report.ready ? 0 : 2;
}

module.exports = { buildReport, reviewedEvidence, validEvidenceAudit, validReviewAudits };
