# Week 4 evaluation and release plan

## Goal

Produce traceable evidence for the final PitayaGrade models and Android workflow,
then revise the manuscript and defense materials to match what was actually tested.

## 1. Freeze evaluated inputs

- Assign stable names and versions to every quality and disease model exposed in
  the application.
- Record SHA-256 hashes for the ONNX files, APK and reviewed test manifest.
- Confirm that the held-out test set is separated by source fruit or capture group,
  not only by filename.
- Reject the evaluation if augmented copies, video neighbors or crops from one
  source appear in more than one split.

## 2. Formal model evaluation

Use `week4/model-evaluation-template.csv`. Evaluate all models for the same task on
the same untouched samples and preprocessing contract.

For quality grading, retain:

- accuracy, macro precision, macro recall and macro F1;
- per-grade precision, recall and F1;
- confusion matrix and every failed sample;
- mean and 95th-percentile inference latency on the target phone.

For detection, retain mAP50, mAP50-95, precision, recall and representative missed
or incorrect boxes. For disease segmentation, retain mask mAP and class-level
results. Do not substitute detection-box results for grading or segmentation
results.

For quality-model comparisons, export one row per model and held-out sample using
`week4/predictions-template.csv`, then run:

```powershell
python -m scripts.summarize_model_evaluation reviewed-manifest.json predictions.csv `
  --target manuscript-quality --output-dir research/week4/runs/evaluation-001
```

The command validates the reviewed manifest and requires exactly one prediction
for every held-out sample from every model. It writes traceable summary metrics,
confusion matrices and mistake lists to a new output directory. Missing samples,
duplicates, incompatible labels and reused output directories stop the run.

## 3. Android verification

Use `week4/device-test-template.csv` and capture screenshots or screen recordings.
At minimum, test:

- clean install and offline first run;
- camera permission denied, granted and revoked;
- gallery upload and live camera capture;
- selection and persistence of each genuinely bundled model;
- recognized and unrecognized images;
- prediction, confidence, method and model identity in saved records;
- save human field validation for tested records and export the resulting CSV;
- history search and notes;
- analytics and date-bounded reports;
- notification preferences and notification read state;
- CSV export, cancellation and retry;
- background/resume, rotation, interrupted scan and repeated taps;
- operation after force-stop and device restart.

Mark a test `Blocked` when its required model, device feature or reviewed input is
missing. A blocked test is not a pass.

Human field-validation entries in the app are observer evidence for this device
workflow. Do not merge them into an expert-reviewed model test set unless the
reviewer, protocol and sample provenance satisfy the approved research method.

## 4. User acceptance testing

Use `week4/uat-template.csv` only after the study procedure and consent process are
approved by the capstone adviser or institution. Use anonymous participant IDs.

Each participant should attempt the same core tasks: choose a model, scan or upload
an image, interpret the result and limitation, find the saved record, add a note,
and produce a report. Record completion, time, errors, assistance and comments.
Do not coach participants unless the test procedure explicitly permits it.

## 5. Manuscript and figure revision

- Replace proposed or simulated performance values with measured results.
- Identify the exact model file, dataset manifest and evaluation date behind every
  table and graph.
- Separate software-test results, model accuracy, device testing and UAT findings.
- State unresolved blocked tests and limitations plainly.
- Ensure the architecture section matches the active Capacitor application rather
  than the separate Flutter prototype.

## 6. Release build and defense check

- Resolve all critical and high-severity defects or document the adviser's written
  acceptance of a limitation.
- Run the complete JavaScript, Python, Android assembly and lint checks.
- Build the release APK with the team's retained signing key.
- Record the release APK hash and confirm that its bundled model hashes equal the
  evaluated model hashes.
- Prepare a short live-demo fallback using retained screenshots and test records.

The current software regression suite may be green while these evidence gates are
still incomplete. Completion requires real reviewed data, a physical device and
approved users; those results must not be inferred from source code or synthetic
tests.
