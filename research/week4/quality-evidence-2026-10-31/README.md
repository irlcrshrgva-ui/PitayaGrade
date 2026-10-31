# Verified quality-model evidence

This package is the portable, checksum-bound comparison for the three selectable
quality classifiers. All models were evaluated on the same 226-image test split
from the frozen, human-reviewed quality manifest.

| Model | Accuracy | Macro F1 | Mean CPU latency |
| --- | ---: | ---: | ---: |
| MobileNetV2 | 72.12% | 55.31% | 7.27 ms |
| ResNet50 | 74.34% | 54.83% | 24.74 ms |
| EfficientNet-B3 | 74.78% | 58.51% | 17.85 ms |

EfficientNet-B3 is the selected default because it has the highest measured
accuracy and macro F1 among these three runtime assets. These are held-out results,
not a claim of 85–90% field accuracy.

`quality-evidence-audit.json` binds the package files and deployed ONNX assets to
SHA-256 hashes. `model-evaluation.csv` contains one row per model, while the
per-model prediction and confusion files retain the evidence behind each metric.

This package is intentionally **not** final release evidence. It contains no
disease-segmentation evaluation, physical Android device results, UAT results or
signed-release audit. The main release gate must remain blocked until those items
are supplied or the adviser formally approves a narrower scope.
