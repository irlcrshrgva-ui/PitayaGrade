# PitayaGrade quality target attempt — 7 November 2026

## Outcome

The 85% target was not reached on the unchanged 226-record held-out split. The
best retained development result remains the validation-selected accuracy-first
ensemble at **77.43% (175/226)**. Reaching 85% on this split would require at
least **193/226** correct predictions, a gap of 18.

These are reused internal held-out results, not fresh field-accuracy estimates.
No model was promoted solely because it performed well on validation data.

## Human fast recheck intake

Two non-test packages supplied 80 returned records. The derived candidate
manifest passed the full quality-manifest validator with zero frozen test rows.
The audit records:

- 80 records validated;
- 61 labels changed;
- 28 changed labels accepted without review notes under an explicit operator
  waiver;
- four label strings normalized without altering their intended class; and
- zero final validation errors.

The raw returned CSV files remain unchanged. The candidate and immutable audit
are stored under `local-review/finalized-fast-quality-recheck-2026-11-07/`.

## Experiments

| Experiment | Validation accuracy | Held-out accuracy | Decision |
| --- | ---: | ---: | --- |
| Accuracy-first retained-model ensemble | 76.19% | **77.43%** | Retain as best development result |
| Cross-validated score stacker | 74.03% refit | 68.14% | Reject |
| Horizontal-flip TTA ensemble | 75.76% | 73.89% | Reject |
| ConvNeXt-Tiny candidate | 74.89% best epoch | 72.57% | Reject |
| Recheck-trained MobileNetV2 | 78.35% observed; loss-selected checkpoint | 71.68% | Reject |
| Recheck-trained ResNet50 | 75.76% observed; loss-selected checkpoint | 73.01% | Reject |
| Recheck-trained EfficientNet-B3 | 74.46% observed; loss-selected checkpoint | 73.45% | Reject |
| Old/new five-model ensemble | **80.52%** | 75.22% | Reject; validation gain did not generalize |

## Evidence-based conclusion

The remaining errors are concentrated in visually adjacent Grade A, B and C
boundaries. The new human decisions changed many development labels but did not
improve generalization to the frozen test set. Model-size increases, score
stacking, test-time augmentation and old/new ensembles did not close the gap.

An honest 85% claim now requires stronger evidence, not more tuning against the
reused split. The next defensible route is an adviser-approved grading rubric,
independent adjudication of ambiguous source-fruit groups, additional balanced
expert-reviewed Grade A/B/C fruit groups, and a new source-group-held-out test
set evaluated once after the revised training protocol is frozen.
