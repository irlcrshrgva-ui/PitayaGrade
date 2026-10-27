# Final quality-model evaluation — 27 October 2026

## Evidence status

The final quality run used the frozen, human-reviewed quality manifest at
`local-review/finalized-human-review-2026-10-27/frozen-quality-manifest.json`.
Its SHA-256 is
`18dcad57010432323a52f2dff08cf70803fa1676239de9b301dd87c241da447a`.
The finalization audit reports 3,050 reviewed quality/maturity records, zero
validation errors, and 1,553 quality records. The untouched quality test split
contains 226 images.

All three exported ONNX files passed the saved WebAssembly runtime-contract
check and produced exactly one prediction for every test image. Their ONNX
predictions matched the corresponding PyTorch predictions on all 226 images.

## Held-out ONNX results

| Model | Accuracy | Macro precision | Macro recall | Macro F1 | Mean latency | P95 latency | ONNX size |
|---|---:|---:|---:|---:|---:|---:|---:|
| MobileNetV2 | 72.12% | 56.95% | 56.07% | 55.31% | 7.27 ms | 15.07 ms | 9.78 MB |
| ResNet50 | **74.34%** | 57.75% | 54.84% | 54.83% | 24.74 ms | 33.65 ms | 95.25 MB |
| EfficientNet-B3 | 72.57% | **59.42%** | **57.22%** | **57.80%** | 12.94 ms | **15.00 ms** | 44.52 MB |

ResNet50 has the highest overall accuracy. EfficientNet-B3 has the strongest
macro-averaged precision, recall and F1 and is substantially smaller and faster
than ResNet50. MobileNetV2 is the smallest and fastest candidate. Class-level
results and all mistakes remain in the immutable evaluation outputs; the weaker
Grade A and Grade C results must remain visible in the manuscript and defense.

## Traceability

- Training directory: `training_results/final-quality-2026-10-27`
- Frozen copy of reviewed manifest: `reviewed-manifest.json`
- ONNX prediction exports: `*_onnx_predictions.csv`
- ONNX evaluation bindings: `*_onnx_predictions.evaluation.json`
- Comparison: `held-out-summary/evaluation.json` and `held-out-summary/summary.csv`
- Confusion matrices: `held-out-summary/confusion-*.csv`
- Failure lists: `held-out-summary/mistakes-*.csv`
- Runtime reports: `runtime-verification/*.json`

Model SHA-256 values:

- MobileNetV2: `72b2dab116a59cf5e45ddff0408e256c019683d5880e897e504fbf32e110f971`
- ResNet50: `b87a808465b27203a9ce735f0840ce1d03e6ada2d1cc2f4a9a110548866a5673`
- EfficientNet-B3: `8461dc36ee59e26111ea7a205095db44e5bc0d77114a1c75258761a262c2b390`

## Promotion decision

The candidates are evaluated quality-model assets, but they were **not promoted
into the application registry**. The fail-closed promotion gate requires a
passing audit for all five declared models, including the still-missing reviewed
disease-segmentation model, plus the required Week 4 evidence. Physical-device
testing, UAT, adviser sign-off and release signing also remain pending. Enabling
only these quality files by bypassing that audit would misrepresent overall
release readiness.

