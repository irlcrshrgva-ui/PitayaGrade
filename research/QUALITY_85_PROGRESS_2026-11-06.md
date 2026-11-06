# PitayaGrade 85% quality target — progress on 6 November 2026

## Current verified development result

- Best retained validation-selected ensemble on the reused internal test split: **76.99%** (174/226).
- At least 193/226 correct predictions are required to reach 85% on the same split.
- Gap: 19 additional correct predictions.
- This reused split is development evidence, not fresh field accuracy.

## Independent experiments completed

### CNN + DINO feature fusion

- Selected only by validation macro F1 and accuracy.
- Selected setup: mean CNN features plus DINO features with a balanced RBF-SVM.
- Validation: 75.76% accuracy, 63.10% macro F1.
- Reused internal test: 75.66% accuracy, 62.58% macro F1.
- Decision: do not integrate; it does not improve the retained result.

### Ordinal A/B/C model with a separate Reject gate

- Model settings and thresholds selected only on validation data.
- Validation: 74.89% accuracy, 62.29% macro F1.
- Reused internal test: 71.24% accuracy, 57.45% macro F1.
- Decision: do not integrate; it performs materially worse.

## Evidence-based conclusion

The remaining errors are dominated by adjacent Grade A/B/C boundaries. Additional model combinations alone did not remove that ceiling. The next safe high-impact action is human adjudication of the 80 most uncertain non-test images, followed by manifest validation and retraining. Model suggestions must not replace the reviewers' visual decisions.

## Required inputs

- `local-review/ultra-fast-quality-recheck-2026-11-06/fast-recheck-01-fast-quality-recheck.zip`
- `local-review/ultra-fast-quality-recheck-2026-11-06/fast-recheck-02-fast-quality-recheck.zip`

Each package contains 40 images. Frozen test records are excluded. Once both completed CSV files are returned, the pipeline can validate and merge corrections, retrain the strongest CNN candidates, run ONNX verification, and perform an audited evaluation.
