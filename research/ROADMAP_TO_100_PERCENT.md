# PitayaGrade roadmap from 80% to 100%

**Status date:** 24 October 2026
**Current retained-deliverable score:** **80/100**
**Fast but defensible estimate:** **12–23 active workdays (about 3–4 calendar weeks)**

This roadmap is the controlling procedure for finishing the capstone. A task is
complete only when its evidence is retained and the relevant validation gate
passes. Preliminary model accuracy, generated text, screenshots alone, and
AI-assisted labels do not count as final research evidence.

## Current position

- The web/PWA and Android application workflows are implemented and tested.
- The public five-model catalog and runtime contracts are implemented.
- The 3,050-record quality/maturity manifest is complete but still provisional:
  791 rows retain AI-assisted attribution (292 quality and 499 maturity).
- Three private recheck packages are ready: `recheck-01` (264 records),
  `recheck-02` (264), and `recheck-03` (263).
- Provisional quality baselines were run on one frozen split. MobileNetV2 reached
  74.8% test accuracy, EfficientNet-B3 69.0%, and ResNet50 65.9%. All three ONNX
  exports passed the browser-runtime contract check. These are engineering
  baselines, not final capstone findings.
- Disease-region masks, formal device-test rows, UAT responses, and release
  signing evidence are still missing.

## Definition of 100%

PitayaGrade reaches 100% only when all of the following are true:

1. Every retained label and annotation is human-reviewed under an approved guide.
2. Related images cannot leak between train, validation, and test partitions.
3. Every enabled model has a retained checkpoint, ONNX asset, checksum, runtime
   verification, and held-out evaluation.
4. The exact candidate application passes photo, live-camera, negative-case,
   offline, Android-device, and UAT checks.
5. The manuscript and defense deck contain only measured, traceable results.
6. The signed release build passes the final demonstration and adviser gate.

## Critical path and score gates

| Gate | Target score | Owner | Required evidence | Stop condition |
|---|---:|---|---|---|
| A. Approvals and human review | 85% | Team + adviser | Approved class/annotation guide, three recheck exports, final reviewed manifests, clean audit | Any assisted reviewer, missing label, unresolved conflict, or split leak remains |
| B. Final models and integration | 88% | Technical workflow | Final checkpoints, ONNX files, contracts, hashes, registry entries | A model lacks evaluated data, compatible output, or acceptable class behavior |
| C. Formal evaluation | 95% | Technical workflow + adviser | Predictions, metrics, confusion matrices, segmentation results, latency and sign-off | Test data was used for tuning or any result lacks a source prediction |
| D. Device/UAT/manuscript/release | 100% | Team + technical workflow + adviser | Device and UAT records, revised manuscript/deck, signed build, checksum, tag and backups | Critical defect, missing approval, unsigned build, or manuscript placeholder remains |

The score must stay at 80 until Gate A genuinely passes.

## Procedure

### Phase 1 — Freeze decisions and calibrate (Day 1–2)

The adviser approves in writing:

- Grade A, Grade B, Grade C, and Reject definitions with visual examples;
- Mature and Immature definitions;
- disease/symptom classes and polygon/mask rules;
- uncertain-image and disagreement rules;
- approved reviewers, test metrics, Android-device count, UAT participants,
  consent/privacy procedure, and acceptance thresholds.

The three members review the same five calibration images and resolve differences
before production work. Save the approval and calibration record in controlled
team storage.

### Phase 2 — Replace all assisted labels (Day 2–4)

Assignments:

- Member 1: `recheck-01-pitayagrade-assisted-recheck.zip` — 264 records.
- Member 2: `recheck-02-pitayagrade-assisted-recheck.zip` — 264 records.
- Member 3: `recheck-03-pitayagrade-assisted-recheck.zip` — 263 records.

Each member extracts one ZIP, opens the hosted Review Desk, loads the ZIP's
`assignment-index.json` with **Load recheck assignment**, selects the matching
`recheck-XX` assignment, restores `draft-backup.json`, loads the extracted folder,
and chooses **All AI-assisted labels**. The member inspects and saves every record,
exports backups after each work block, and sends one final reviewed-manifest JSON
when both task queues reach zero.

The technical workflow then strictly merges the three exports, reconciles linked
source groups, validates quality and maturity separately, and freezes versioned
train/validation/test manifests. It must reject missing assignments, overlaps,
changed image hashes, assisted attribution, conflicting groups, and split leaks.

### Phase 3 — Finish disease and detection annotations (Day 2–8, parallel)

After the adviser freezes the annotation rules, divide disease images into three
non-overlapping packages while keeping related captures together. Reviewers draw
visible disease-region polygons/masks and record Healthy negatives. If fruit
detection retraining is retained in scope, also review the fruit boxes.

Run the disease and detection validators. Do not infer masks from folder names or
convert a broad disease class into a pixel mask. If approved masks cannot be
obtained, the honest alternative is to revise the project scope and manuscript so
the unimplemented segmentation claim is removed; that change requires adviser
approval.

### Phase 4 — Final training and locked evaluation (Day 8–11)

Once Gate A passes, the technical workflow will:

1. Record dataset hashes, split counts, class counts, seed, framework versions,
   augmentations, batch size, and stopping rules.
2. Train MobileNetV2, ResNet50, and EfficientNet-B3 on the same frozen quality
   partitions without inspecting test results during tuning.
3. Train the approved YOLOv8-Nano disease-segmentation model from reviewed masks.
4. Export selected checkpoints to ONNX.
5. Verify input/output shapes, preprocessing, class order, WebAssembly execution,
   and SHA-256 checksums.
6. Save one prediction row per held-out record and calculate per-class and overall
   precision, recall, F1, confusion matrices, segmentation metrics, model size,
   and inference latency.
7. Obtain adviser sign-off on the model comparison before enabling assets.

### Phase 5 — Integrate and regression-test the selected assets (Day 11–14)

Only evaluated models are copied into the app and enabled in the registry. Then:

- test photo and live-camera inference for every enabled model;
- test clear fruit across lighting/backgrounds;
- test faces, hands, empty scenes, printed images, and unrelated objects;
- confirm rejected inputs are not stored as graded fruit;
- verify history, analytics, reports, notifications, and CSV export;
- test offline launch and inference; and
- run all JavaScript, Python, model-contract, build, and Android checks.

Every failed acceptance test becomes a defect record, is fixed, and is repeated.

### Phase 6 — Physical Android testing and UAT (Day 14–19)

The team installs the exact candidate APK on the adviser-approved Android devices
and completes `research/week4/device-test-template.csv`. Record device model,
Android version, APK checksum, permissions, photo/live results, orientation,
offline behavior, latency, memory/crashes, exports, and defects.

Run the approved UAT scenarios with real participants and complete
`research/week4/uat-template.csv`. Preserve consent where required, task outcome,
time/errors, rating, comments, and observed issues. Do not invent missing answers
or coach participants through the interface.

### Phase 7 — Submission and signed release (Day 19–23)

The technical workflow generates final figures and tables from retained evidence,
then updates Chapter 5, the abstract, conclusions, limitations, recommendations,
and defense deck. The team proofreads and obtains adviser approval.

The project owner creates a team-controlled Android signing key and keeps its file
and passwords outside Git. Build and install the signed APK/AAB, repeat the final
demonstration flow, record version and checksum, tag the approved Git commit, and
create two submission backups.

## Responsibility split

### Work the technical workflow can complete

- merge, reconcile, audit, and freeze returned manifests;
- create non-overlapping annotation/review packages;
- train, compare, export, and runtime-check models;
- integrate passing assets and fix application defects;
- produce predictions, metrics, figures, APKs, checksums, and test reports;
- revise the manuscript and deck using retained measured evidence; and
- run the automated release gate and prepare the final archive.

### Work the three members/adviser must complete

- approve label definitions, classes, metrics, participants, and acceptance rules;
- visually confirm labels and draw/approve annotations;
- provide physical Android devices and perform real-world tests;
- recruit approved UAT participants and preserve genuine responses/consent;
- provide release-signing control securely; and
- approve the final findings and submission.

## Final commands

After all evidence is in its approved location, run:

```text
npm test
npm run progress
npm run readiness
```

Completion requires `100/100`, `release readiness: PASS`, a clean Git working
tree, a tagged final commit, the signed-build checksum, and adviser approval.
