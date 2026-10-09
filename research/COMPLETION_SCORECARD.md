# PitayaGrade completion scorecard

**Status date:** 9 October 2026  
**Overall project-readiness estimate:** **80 / 100**

This is a project-management estimate based on retained deliverables. It is not
a model-accuracy score. The remaining work has the highest research risk and
cannot be replaced by source code, simulated values or generated evidence.

| Workstream | Weight | Earned | Evidence and remaining work |
|---|---:|---:|---|
| Scope and requirements | 10 | 10 | Scope, limitations, users, planned model catalog and architecture are documented. |
| Repository and repeatable builds | 10 | 10 | Git history, CI, dependency lock, data-validation scripts and release-readiness gate are present. |
| Application functionality | 20 | 20 | Photo/live scanning, model selection, local records, validation feedback, analytics, reports, notifications and PWA delivery are implemented and regression-tested. Physical-device validation is scored under release readiness. |
| Model infrastructure | 15 | 12 | Five-model registry, ONNX contracts, checksum validation and separate quality/disease loading paths are implemented. Only YOLOv8-Nano has a bundled runtime asset; the other four evaluated assets remain pending. |
| Data governance and preparation | 15 | 10 | Dataset audit, manifests, byte-exact split checks, review tool and provenance checks exist. The 3,050-image public review manifest still has zero approved target labels. |
| Formal evaluation and UAT | 10 | 3 | Traceable protocols, calculation scripts and CSV templates exist. Predictions, held-out metrics, device-test records and approved UAT results are missing. |
| Manuscript and defense materials | 15 | 15 | Six-chapter manuscript, figures, architecture diagrams, evaluation plan and a validated 15-slide defense deck are prepared. Measured Chapter 5 findings remain governed by the formal-evaluation workstream. |
| Release readiness | 5 | 0 | Debug APK and automated verification pass. Release signing, target-phone verification and a signed release build remain incomplete. |
| **Total** | **100** | **80** | **Prototype and defense preparation are advanced; research evidence and final release remain the critical path.** |

## Definition of the remaining 20%

1. Complete expert or approved human review of target labels and source groups.
2. Train, export and evaluate MobileNetV2, ResNet50, EfficientNet-B3 and the
   YOLOv8-Nano disease-segmentation model from reviewed data.
3. Produce complete retained prediction files and formal held-out metrics.
4. Run the Android device matrix and approved user acceptance testing.
5. Replace manuscript placeholders with measured results and final figures.
6. Configure the team-controlled signing key and produce the signed release.

## Completion rule

The score must not exceed 80 until genuine reviewed labels exist. It must not
reach 100 until every release-readiness gate passes and the manuscript contains
only retained, traceable results.
