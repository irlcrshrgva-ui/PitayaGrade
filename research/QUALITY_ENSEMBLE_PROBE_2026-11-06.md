# Quality ensemble development probe — 6 November 2026

## Outcome

A validation-selected probability ensemble improved the frozen internal held-out
quality result from the promoted single-model baseline of **74.78% accuracy and
58.51% macro F1** to **76.99% accuracy and 62.10% macro F1**.

This is a development result, not field accuracy and not evidence of an 85–90%
model. The existing test partition has also been used by earlier development
experiments, so it cannot be presented as a newly untouched external benchmark.

## Selection policy

- Input models: MobileNetV2, ResNet50, bundled EfficientNet-B3 and the externally
  pretrained EfficientNet-B3.
- Ensemble weights were selected only from the 231-image validation split.
- The selection objective was validation macro F1, then validation accuracy.
- The frozen 226-image test split was evaluated only after weights were selected.
- Manifest SHA-256:
  `18dcad57010432323a52f2dff08cf70803fa1676239de9b301dd87c241da447a`.

## Selected weights

| Candidate | Weight |
|---|---:|
| MobileNetV2 | 0.30 |
| ResNet50 | 0.15 |
| Bundled EfficientNet-B3 | 0.00 |
| Externally pretrained EfficientNet-B3 | 0.55 |

## Results

| Partition | Accuracy | Macro F1 |
|---|---:|---:|
| Validation | 76.19% | 59.70% |
| Frozen internal test | 76.99% | 62.10% |

The test confusion matrix, in `Grade A`, `Grade B`, `Grade C`, `Reject` order,
was:

```text
13 12  3  0
13 45  2  1
 5 10  7  0
 1  4  1 109
```

The model family already handles Reject comparatively well. Most remaining
errors are disagreements among Grades A, B and C. Additional architecture-only
experiments (balanced EfficientNet-B3, DINOv2 probing/fine-tuning and crop-aligned
probing) did not establish an 85–90% result.

## Promotion decision

Do not replace the current single-model mobile runtime with this ensemble yet.
It requires three ONNX inference passes, adds mobile latency and package size,
and remains below the requested accuracy range. Preserve it as reproducible
development evidence and use it to guide a qualified A/B/C label-adjudication
round or a new independently labeled evaluation set.
