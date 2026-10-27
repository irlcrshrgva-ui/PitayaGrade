# PitayaGrade completion scorecard

**Status date:** 27 October 2026
**Overall project-readiness estimate:** **88 / 100**

This is a project-management estimate based on retained deliverables. It is not
a model-accuracy score. The remaining work has the highest research risk and
cannot be replaced by source code, simulated values or generated evidence.

| Workstream | Weight | Earned | Evidence and remaining work |
|---|---:|---:|---|
| Scope and requirements | 10 | 10 | Scope, limitations, users, planned model catalog and architecture are documented. |
| Repository and repeatable builds | 10 | 10 | Git history, CI, dependency lock, data-validation scripts and release-readiness gate are present. |
| Application functionality | 20 | 20 | Photo/live scanning, model selection, local records, validation feedback, analytics, reports, notifications and PWA delivery are implemented and regression-tested. Physical-device validation is scored under release readiness. |
| Model infrastructure | 15 | 13 | Five-model registry, ONNX contracts, checksum validation and separate quality/disease loading paths are implemented. Final MobileNetV2, ResNet50 and EfficientNet-B3 candidates have checksum-bound runtime reports and held-out ONNX results. Promotion remains blocked by the missing reviewed disease-segmentation asset and the all-model audit. |
| Data governance and preparation | 15 | 15 | All 3,050 quality/maturity rows were human-reviewed, conflicts were adjudicated, validation returned zero errors, and frozen quality, maturity and combined manifests are retained with checksums. Reviewed disease-region masks remain outside this workstream and are still missing. |
| Formal evaluation and UAT | 10 | 5 | All three final quality ONNX candidates were evaluated on the same untouched 226-image split with retained predictions, per-class metrics, confusion matrices, mistakes and latency. Disease segmentation evaluation, adviser sign-off, device tests and UAT remain missing. |
| Manuscript and defense materials | 15 | 15 | Six-chapter manuscript, figures, architecture diagrams, evaluation plan and a validated 15-slide defense deck are prepared. Measured Chapter 5 findings remain governed by the formal-evaluation workstream. |
| Release readiness | 5 | 0 | Debug APK and automated verification pass. Release signing, target-phone verification and a signed release build remain incomplete. |
| **Total** | **100** | **88** | **Human-reviewed quality data and final quality-model evaluation are complete; disease evidence, real-device/UAT results and release work remain the critical path.** |

## Definition of the remaining 12%

Use `research/ROADMAP_TO_100_PERCENT.md` as the dependency-ordered plan and
`research/FINAL_20_PERCENT_CHECKLIST.md` as the evidence checklist.

1. Complete reviewed disease-region masks and freeze the segmentation dataset.
2. Train, export, verify and evaluate the YOLOv8-Nano disease-segmentation model.
3. Obtain adviser review of the retained quality and disease results, then run
   the all-model evidence audit and promote only the exact passing hashes.
4. Run the Android device matrix and approved user acceptance testing.
5. Replace manuscript placeholders with approved measured results and figures.
6. Configure the team-controlled signing key and produce the signed release.

## Completion rule

The score reached 88 only after human-review finalization and exact ONNX held-out
evaluation were retained. It must not increase for missing disease annotations,
physical-device tests, UAT, adviser approval or signing, and it must not reach
100 until every release-readiness gate passes.
