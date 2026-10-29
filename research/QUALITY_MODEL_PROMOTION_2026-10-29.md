# Quality-model deployment addendum — 29 October 2026

## Decision

The three evaluated quality-classification candidates are bundled as selectable
models in PitayaGrade. This is a quality-pipeline deployment only. It does not
promote, validate, or imply completion of the separately declared disease
segmentation model, which remains unavailable in the registry.

## Evidence boundary

All three candidates were evaluated on the same untouched 226-image test split
from the frozen human-reviewed quality manifest. The manifest SHA-256 is
`18dcad57010432323a52f2dff08cf70803fa1676239de9b301dd87c241da447a`.
Their ONNX predictions matched their corresponding PyTorch predictions on all
226 images. The retained evaluation is in
`training_results/final-quality-2026-10-27/held-out-summary/evaluation.json`.

| Model | Held-out accuracy | Macro F1 | Bundled asset SHA-256 |
|---|---:|---:|---|
| MobileNetV2 | 72.12% | 55.31% | `72b2dab116a59cf5e45ddff0408e256c019683d5880e897e504fbf32e110f971` |
| ResNet50 | 74.34% | 54.83% | `b87a808465b27203a9ce735f0840ce1d03e6ada2d1cc2f4a9a110548866a5673` |
| EfficientNet-B3 | 72.57% | 57.80% | `8461dc36ee59e26111ea7a205095db44e5bc0d77114a1c75258761a262c2b390` |

Each ONNX candidate has a retained runtime-contract report in
`training_results/final-quality-2026-10-27/runtime-verification/`. The packaged
registry independently checks every bundled file against the SHA-256 above at
build time.

## Limitations

- These are internal held-out quality-grading results, not field-accuracy claims.
- Grade A and Grade C remain weaker classes and must remain visible in reporting.
- The quality classifiers do not localize fruit; the application keeps its
  visual input gate before accepting a classification.
- Physical-device model switching, scan timing, UAT, release signing, and the
  disease-segmentation scope remain separate unfinished evidence requirements.

