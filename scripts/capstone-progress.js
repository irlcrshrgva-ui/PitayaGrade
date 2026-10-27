const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const exists = relative => fs.existsSync(path.join(root, relative));
const checks = [
  ['Scope and requirements', 10, 10, ['PitayaGrade_Capstone_Paper.md', 'research/SCOPE_ALIGNMENT.md']],
  ['Repository and repeatable builds', 10, 10, ['package-lock.json', '.github/workflows/verify.yml', 'scripts/release-readiness.js']],
  ['Application functionality', 20, 20, ['js/scanner.js', 'js/live-scanner.js', 'js/reports.js', 'js/history.js']],
  ['Model infrastructure', 15, 13, ['js/model-registry.js', 'js/model-inference.js', 'www/model/best.onnx', 'research/FINAL_QUALITY_MODEL_EVALUATION_2026-10-27.md']],
  ['Data governance and preparation', 15, 15, ['research/dataset-audit.json', 'research/public-review-manifest.json', 'review-tool/index.html', 'training_results/final-quality-2026-10-27/reviewed-manifest.json']],
  ['Formal evaluation and UAT', 10, 5, ['scripts/summarize_model_evaluation.py', 'research/week4/uat-template.csv', 'training_results/final-quality-2026-10-27/held-out-summary/evaluation.json']],
  ['Manuscript and defense materials', 15, 15, ['PitayaGrade_Capstone_Paper.md', 'deliverables/PitayaGrade_Defense_Deck_v1.pptx']],
  ['Release readiness', 5, 0, ['android/app/build/outputs/apk/debug/app-debug.apk']]
];

let score = 0;
for (const [name, weight, earned, evidence] of checks) {
  const missing = evidence.filter(item => !exists(item));
  if (missing.length) {
    console.error(`[BLOCK] ${name}: missing ${missing.join(', ')}`);
    process.exitCode = 1;
    continue;
  }
  score += earned;
  console.log(`[${earned}/${weight}] ${name}`);
}
console.log(`PitayaGrade completion estimate: ${score}/100`);
console.log('Project-management readiness only; this is not model accuracy.');
if (score > 88) {
  console.error('Score cannot exceed 88 before reviewed disease masks, device/UAT evidence and release gates exist.');
  process.exitCode = 1;
}
