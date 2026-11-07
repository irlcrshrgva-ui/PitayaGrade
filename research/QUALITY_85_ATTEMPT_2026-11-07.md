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
| Nonlinear score stacker | 80.54% cross-validated; 89.18% refit | 75.22% | Reject; refit result overfit |
| Separate Reject gate + A/B/C grader | 77.49% | 76.99% | Reject; does not beat retained ensemble |

## Evidence-based conclusion

The remaining errors are concentrated in visually adjacent Grade A, B and C
boundaries. The new human decisions changed many development labels but did not
improve generalization to the frozen test set. Model-size increases, score
stacking, test-time augmentation and old/new ensembles did not close the gap.

The hierarchical probe isolated the bottleneck: its Reject gate reached 96.10%
validation accuracy, while the dedicated A/B/C grader reached only 61.26%.
The principal limitation is therefore inconsistent or visually overlapping
grade boundaries, not the ability to reject non-fruit records.

An honest 85% claim now requires stronger evidence, not more tuning against the
reused split. The next defensible route is an adviser-approved grading rubric,
independent adjudication of ambiguous source-fruit groups, additional balanced
expert-reviewed Grade A/B/C fruit groups, and a new source-group-held-out test
set evaluated once after the revised training protocol is frozen.

## Activated recovery plan

The full non-test A/B/C repair workload is now packaged under
`local-review/full-grade-regrade-packages-2026-11-07/`:

- 630 training/validation images across 573 source-fruit groups;
- three balanced assignments of 210 images each;
- existing source-fruit groups are prefilled and kept with one reviewer;
- no frozen test record is present; and
- model proposals are deliberately excluded from the fresh human pass.

The packages must not be used until an adviser or qualified agriculture expert
approves the A/B/C rubric included in each ZIP. After the three exports return,
`scripts/finalize_full_grade_repair.py` verifies assignment completeness,
reviewer attribution, protected fields, source groups, timestamps, conflicts,
manifest validity and exact preservation of the frozen test rows before it
produces a repaired training candidate.

After label repair, the team should add independent fruit groups, prioritizing
the underrepresented Grade C and Grade A classes. The current training data has
about 95 Grade C groups, 162 Grade A groups and 212 Grade B groups. A practical
first balance target is roughly 200 unique groups per grade, which means about
105 additional Grade C groups and 38 Grade A groups. Multiple views of one fruit
may be collected, but every view of that fruit must remain in one split.

The final accuracy claim must be made on a newly collected, untouched,
source-group-held-out test set after the revised rubric, labels and training
protocol are frozen. The promotion gate is at least 85% overall accuracy with
macro and per-grade results reported; a high overall score cannot hide weak
Grade A or Grade C performance.
