# External quality feature pretraining — 2026-10-30

## Approved source

- Repository: <https://github.com/codernayeem/fruit-classification-dataset>
- Published collection: 1,667 processed dragon-fruit images
- Publisher labels: `good` (560), `medium` (528), and `bad` (579)
- Publisher license claim: CC BY 4.0
- Local source archive SHA-256: `092cd165f4175a4e61476d0a6da2b8d0db45cf3f3562fc6a6defa6f257a54e75`

The repository states that students curated images from online sources. The repository's
CC BY 4.0 statement is retained as publisher-supplied provenance, but it does not by
itself independently verify the rights for every underlying online image. Any public
release or manuscript citation must preserve this limitation and attribution.

## Leakage and duplicate audit

The downloaded archive was audited against all 1,553 images in
`local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json` before
training. The audit compared file bytes, decoded pixels, dHash, and aHash. It also
grouped exact and conservative near-duplicates inside the external collection.

| Audit result | Count |
| --- | ---: |
| External images inspected | 1,667 |
| Frozen PitayaGrade images inspected | 1,553 |
| External records matching frozen evidence | 583 |
| Internal external duplicates removed | 4 |
| Safe independent external records | 1,080 |
| Safe `good` records | 560 |
| Safe `medium` records | 520 |
| Safe `bad` records | 0 |

All 579 `bad` images overlap with the Mendeley-derived evidence already used by
PitayaGrade. Four `medium` images also matched frozen evidence. Those records were
excluded. The resulting 1,080-image set is genuinely additional Good/Medium material,
but it supplies no new independent Reject evidence.

Machine-readable evidence is stored in
`training_results/external-quality-pretrain-2026-10-30/audit.json`.

## Training contract

1. Good/Medium labels are used only to initialize dragon-fruit quality features.
2. They are never mapped to Grade A, Grade B, Grade C, or Reject.
3. After pretraining, the two-class head is discarded.
4. A fresh four-class head is trained and fine-tuned only with the frozen
   human-reviewed PitayaGrade train and validation partitions.
5. Every external image matching any frozen image—including a frozen test image—is
   excluded before pretraining.
6. The unchanged 226-image PitayaGrade test partition is used once for final
   comparison with the previous 74.3% ResNet50 baseline.
7. A new model is promoted only if the exact ONNX export passes runtime verification
   and improves the audited promotion metrics. No target accuracy is fabricated or
   guaranteed.

## Interpretation

High validation accuracy on the public Good/Medium task is not capstone accuracy. It
only indicates that the auxiliary source labels are separable. Capstone accuracy is
the result measured on the unchanged human-reviewed Grade A/B/C/Reject test set.

## Audited candidate results

Both candidates used the same frozen 226-image test partition exactly once after
training. Their exported ONNX predictions were evaluated independently with
ONNX Runtime and retained beside each training run.

| Candidate | Accuracy | Macro precision | Macro recall | Macro F1 | ONNX mean / P95 CPU latency | Decision |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| ResNet50 | 73.45% | 63.34% | 60.31% | 60.23% | 27.14 / 31.31 ms | Not promoted; accuracy was below the bundled ResNet50 baseline. |
| EfficientNet-B3 | **74.78%** | 58.86% | 58.97% | 58.51% | 17.85 / 21.28 ms | Promoted as the updated selectable EfficientNet-B3 quality asset. |

The promoted EfficientNet-B3 ONNX SHA-256 is
`c2dbd10f72932b871e49679f07b5134a0e8de75f973084651850d61673d0c3a3`.
Its ONNX predictions matched its PyTorch predictions for all 226 test images.
Compared with the previously bundled EfficientNet-B3, accuracy increased from
72.57% to 74.78% and macro F1 increased from 57.80% to 58.51%. Compared with the
previous highest-accuracy ResNet50, accuracy increased from 74.34% to 74.78% and
macro F1 increased from 54.83% to 58.51%.

This is a small internal held-out improvement, not an 85% or 90% field-accuracy
claim. Grade A and Grade C remain the weakest classes. The separate dragon-fruit
presence gate, physical-device tests, UAT, disease-model scope, and signed release
gate remain independent requirements.

Evidence paths:

- `training_results/external-pretrained-quality-2026-10-30-resnet50`
- `training_results/external-pretrained-quality-2026-10-30-efficientnetb3`
- `training_results/external-pretrained-quality-2026-10-30-efficientnetb3/held-out-summary/evaluation.json`
- `training_results/external-pretrained-quality-2026-10-30-efficientnetb3/runtime-verification/efficientnet-b3-quality.json`
