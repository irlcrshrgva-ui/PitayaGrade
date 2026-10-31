# PitayaGrade Final 20% Checklist

**Starting status:** 80% project readiness
**Current evidence-based status (31 October 2026):** 88% project readiness
**Rule:** Check an item only when its required evidence has been saved in the repository or approved team storage.

## 1. Freeze the evaluation setup

- [ ] Confirm the final quality-grade names and definitions with the adviser.
- [ ] Confirm the final disease classes and annotation rules.
- [ ] Assign a reviewer for every label and disease mask.
- [ ] Confirm that images from the same fruit, farm, session or source stay in only one dataset split.
- [ ] Record the approved evaluation protocol and acceptance criteria.

Review aid prepared: `research/source-group-suggestions-2026-10-10.json` flags
possible same-source images, including cross-split candidates, but does not approve
or apply any group.

**Evidence required:** approved class guide, reviewer list, source-grouping record and evaluation protocol.

## 2. Complete dataset review

- [x] Review all 3,050 rows in the public review manifest.
- [x] Add reviewer name or ID, review time and approved target label to every retained row.
- [x] Resolve uncertain, conflicting or unusable images.
- [ ] Review or create disease-segmentation masks.
- [x] Re-run the dataset audit after corrections.
- [x] Confirm there are no cross-split duplicates or source-group leaks.
- [x] Freeze the final train, validation and test manifests.

**Evidence required:** completed review manifest, reviewed masks, clean audit report and frozen split manifests.

## 3. Train and export the missing models

- [x] Train MobileNetV2 for quality classification.
- [x] Train ResNet50 for quality classification.
- [x] Train EfficientNet-B3 for quality classification.
- [ ] Train YOLOv8-Nano segmentation for visible disease regions.
- [x] Save training configuration, random seed, dataset version and checkpoints for every quality run.
- [x] Export the selected quality checkpoints to ONNX.
- [x] Verify input shape, output shape, class order and preprocessing contract for every quality ONNX file.
- [x] Generate and record SHA-256 checksums for every quality candidate.
- [ ] Add only evaluated assets to the application model registry.

**Evidence required:** training records, selected checkpoints, ONNX files, verification reports and checksums.

## 4. Perform formal held-out evaluation

- [x] Run each quality model on the untouched test set.
- [x] Save one prediction row per test image.
- [x] Calculate accuracy, precision, recall and F1-score per class and overall.
- [x] Generate confusion matrices for the quality models.
- [ ] Calculate the approved segmentation metrics for the disease model.
- [x] Compare all quality candidate models using the same test set and rules.
- [x] Record quality-model size and inference time alongside predictive performance.
- [ ] Have the results reviewed and approved before using them in the manuscript.

**Evidence required:** `predictions.csv`, `model-evaluation.csv`, confusion matrices, segmentation results and signed-off comparison summary.

## 5. Verify application integration

- [x] Confirm every enabled model appears in the correct selector.
- [x] Confirm unavailable models remain disabled and clearly explained.
- [x] Test photo-mode inference for every enabled model.
- [ ] Test live-camera inference for every enabled model.
- [ ] Test clear dragon-fruit images under varied backgrounds and lighting.
- [ ] Test faces, hands, empty scenes and unrelated objects as negative cases.
- [x] Confirm rejected images are not saved as graded dragon fruit.
- [x] Confirm history, analytics, reports and CSV exports identify the selected model and method.
- [x] Re-run all automated JavaScript and Python tests.

**Evidence required:** passing test logs, negative-case results, screenshots and integration test records.

Repository verification evidence: `research/AUTONOMOUS_VERIFICATION_2026-10-10.md`.

## 6. Test on physical Android devices

- [ ] Select at least the adviser-approved minimum number of Android devices.
- [ ] Test camera permission, photo upload and live scanning on each device.
- [ ] Test portrait and landscape behavior where applicable.
- [ ] Test offline launch and offline inference after required assets are cached or bundled.
- [ ] Record inference time, crashes, memory problems and device details.
- [ ] Test history, notification, report and CSV-export workflows.
- [ ] Fix critical defects and repeat the affected tests.

**Evidence required:** completed `device-test.csv`, device screenshots and resolved defect records.

## 7. Conduct user acceptance testing

- [ ] Obtain adviser approval for participants and test procedure.
- [ ] Prepare consent and privacy materials if required.
- [ ] Recruit the approved farmers, agricultural workers or evaluators.
- [ ] Run the complete UAT scenarios without coaching the participant through the interface.
- [ ] Record task completion, usability ratings, comments and observed issues.
- [ ] Summarize results without inventing or replacing missing responses.
- [ ] Address critical usability problems and document the changes.

**Evidence required:** completed `uat.csv`, approved questionnaires, consent records where applicable and UAT summary.

## 8. Finish the manuscript and defense materials

- [ ] Replace every placeholder result with approved measured evidence.
- [x] Add the final quality-model comparison table and EfficientNet-B3 confusion matrix.
- [ ] Add segmentation and device-testing results.
- [ ] Add UAT findings and limitations.
- [x] Update the abstract and conclusions to match the measured quality results and remaining limitations.
- [x] Verify that the manuscript describes the implemented application accurately.
- [x] Update the defense deck with the final charts and selected model.
- [ ] Proofread references, captions, numbering and formatting.
- [ ] Obtain adviser approval for the final manuscript and presentation.

**Evidence required:** approved manuscript, final figures and final defense deck.

## 9. Produce the final release

- [ ] Obtain a team-controlled Android release-signing key.
- [ ] Store the signing key and passwords outside version control.
- [ ] Build the signed release APK or AAB.
- [ ] Install and test the exact signed build on target devices.
- [ ] Record the release version and SHA-256 checksum.
- [ ] Tag the final Git commit and archive the approved source, models and evidence.
- [ ] Prepare a backup copy for the defense and submission.

**Evidence required:** signed release, checksum, final Git tag and submission archive.

## Final completion gate

- [ ] Every enabled model has an evaluated, checksum-verified runtime asset.
- [ ] Every research result is traceable to retained predictions and reviewed labels.
- [ ] Physical-device and UAT records are complete.
- [ ] The manuscript contains no pending or fabricated result.
- [ ] The signed release passes the final demonstration flow.
- [ ] The adviser confirms that the submission requirements are complete.

When every final-gate item is checked, run:

```text
npm run progress
npm run readiness
npm test
```

