# PitayaGrade Week 4 evaluation package

This folder is the evidence handoff for the final evaluation, manuscript revision,
release build and defense. Blank rows are intentional: measured results must come
from the frozen held-out dataset, physical Android devices and actual participants.

The portable `quality-evidence-2026-10-31/` package already contains the exact
frozen manifest, predictions, confusion matrices, runtime reports and held-out
metrics for MobileNetV2, ResNet50 and EfficientNet-B3. Its audit is intentionally
marked `quality-only-verified-release-incomplete`: it is research evidence, but it
does not substitute for disease evidence, physical-device tests, UAT or signing.
Regenerate it with:

```text
python -m scripts.stage_quality_week4_evidence --output <new-empty-folder>
```

## Required order

1. Freeze the model files and record each file path and SHA-256 hash.
2. Freeze the reviewed test manifest. Do not tune models or thresholds on it.
3. Complete `model-evaluation-template.csv` for every selectable model and task.
4. Complete `device-test-template.csv` on at least one physical Android device.
5. Resolve release-blocking defects, rebuild, and repeat affected tests.
6. Complete approved user acceptance testing using `uat-template.csv`.
7. Revise the manuscript using only evidence recorded in this folder.

The published [Test APK page](https://irlcrshrgva-ui.github.io/PitayaGrade/site/testing.html)
provides a device worksheet and UAT worksheet generated for the exact APK currently
offered by the website. The generator is `scripts/create_testing_pack.py`. It
pre-fills test procedures and the APK checksum, but deliberately leaves dates,
devices, actual results, statuses and participant measurements blank. Those files
are execution aids, not evidence until the approved human work is completed.

## Evidence rules

- Use the same held-out samples when comparing models for the same task.
- Record failures and excluded samples; do not silently remove them.
- Keep participant identities outside this repository. Use anonymous participant IDs.
- Do not claim disease diagnosis. The app reports visual estimates that require
  physical or expert verification.
- Passing software tests proves runtime behavior, not research accuracy.
- Store large raw exports outside Git and record their path and checksum here.

Validate completed evidence before running the release gate:

```text
python -m scripts.validate_week4_evidence --evidence-dir <completed-folder> --review-audit <recheck-finalization-audit.json> --review-audit <annotation-finalization-audit.json> --min-devices <approved-count> --min-participants <approved-count> --output <completed-folder/evidence-audit.json>
```

The validator requires one row for every model in the five-model selector. It
checks that model, test-manifest, confusion-matrix and prediction paths exist;
recomputes model and manifest hashes; verifies one unique prediction per declared
test sample; binds each test manifest to the corresponding human-review
finalization audit; verifies the saved WebAssembly runtime-contract report for
each exact model hash; and checks required fields, time zones, numeric ranges, task
coverage, unresolved failures, and approved device/participant counts. The audit
does not generate missing results.

After the evidence audit passes, promote exactly those audited model hashes in
one fail-closed step:

```text
node scripts/promote-evaluated-models.js --evidence-audit <completed-folder/evidence-audit.json> --output-audit <private-folder/model-promotion-audit.json>
```

The command rehashes every ONNX file and saved WebAssembly verification report,
copies only exact matches into the web package, enables all five registry entries,
verifies the resulting registry, and retains a promotion audit. It refuses to
replace a different existing asset.

## Signed Android release

Keep the team keystore and passwords outside Git. In a PowerShell session, set
`PITAYAGRADE_STORE_PASSWORD` and `PITAYAGRADE_KEY_PASSWORD`, then run:

```powershell
./scripts/build-android-release.ps1 -KeystorePath <private-keystore.jks> -KeyAlias <alias> -OutputAudit <private-folder/release-audit.json> -JavaHome <java-21-folder>
```

The script refuses a dirty Git tree, runs the app tests, builds and lints the
release, verifies the APK signature with Android `apksigner`, and records the APK,
certificate and source-commit hashes without writing passwords to the repository.
Supply the audit to the final gate with `--release-audit <release-audit.json>`.

## Manuscript-ready results

After the Week 4 audit passes, generate tables, SVG figures and a checksum map
directly from that locked evidence:

```text
python -m scripts.generate_final_results --evidence-dir <completed-folder> --audit <completed-folder/evidence-audit.json> --output-dir <new-results-folder>
```

The generator refuses changed or unaudited CSV files. Its Markdown summaries and
SVG charts cover quality models, disease segmentation, Android device runs and
UAT aggregates; `traceability.json` binds every output to the evidence hashes.
Supply this folder to the final release gate with `--results-dir
<new-results-folder>`.

Quality-model prediction exports should follow `predictions-template.csv`. Use
`python -m scripts.summarize_model_evaluation --help` for the fail-closed comparison
tool; its generated JSON, summary, confusion matrices and mistake lists provide the
source evidence for `model-evaluation-template.csv`.

## Release gate

The capstone is ready for a final release only when:

- reviewed labels cover every required grade and disease class;
- the final model files match the evaluated file hashes;
- per-class results, confusion matrices and failure cases are documented;
- model selection, scanning, records, reports and notifications pass on Android;
- offline first-run, permissions, background/resume and export behavior are tested;
- UAT findings are resolved or explicitly accepted as limitations;
- every manuscript result and figure can be traced to retained evidence.
