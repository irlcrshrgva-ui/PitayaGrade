# Mendeley image-label integration

Verified against the live publisher pages and file API on 2026-10-21 (Asia/Shanghai).

## Sources, attribution and actual labels

Both version 1 dataset pages explicitly list **CC BY 4.0**. Retain author credit,
dataset links, the [license link](https://creativecommons.org/licenses/by/4.0/)
and an indication of modifications when sharing images or derived packages.
The project does not imply publisher endorsement. Local images remain ignored
by Git; the download script records publisher file hashes and original names.

* Pronob Sarkar, Gourab Kumar Pranta and Mayen Uddin Mojumdar (2024),
  [Dragon fruit & leaf Dataset from Bangladesh for Classification and Ecological Research](https://data.mendeley.com/datasets/cfchfdpfw5/1),
  DOI 10.17632/cfchfdpfw5.1. The landing page describes 4,518 images and named
  diseases, but the actual ZIP has **4,497 original images**, in four folders:
  Good fruit (333), Bad fruit (307), Good leaf (2,242), Bad leaf (1,615).
  It also contains 11,024 augmented images, excluded from preparation.
  **The actual folders do not identify particular diseases.** Good/Bad labels
  remain source health-status labels, not manuscript grades or diagnoses.
  ZIP SHA-256: `4432c6dee30cd08839a17de0179d1dd2c59ded98b8847eaf7522293080b7cbcd`.
* MD. Fahiz Siddikur Pranto, Anamika Dhar and Rokonozzaman Ayon (2026),
  [DragonFruit-MultiOrgan Dataset](https://data.mendeley.com/datasets/kpsywfwkrf/1),
  DOI 10.17632/kpsywfwkrf.1. Original tree: Black_Rot (675), Fungi (640),
  Healthy_fruit (650), Healthy_leaf (944), Rust (582), Scab (837),
  Stem_Canker (553), Sunburn (587), totaling **5,468**. The separate
  “Dragon Fruit Balanced” tree is excluded. The publisher places Healthy_leaf
  under Stem; the mapping preserves that ambiguity as healthy_stem_leaf.

The explicit mapping is in `mendeley-disease-mapping.json`. The two sources are
prepared together for cross-source duplicate detection, then trained as separate
tasks: `health` for the four broad Good/Bad source labels and `disease` for the
eight multi-organ condition labels. Mixing unspecified “Bad” with specific
diseases as mutually exclusive targets would create overlapping categories.
No one needs to manually assign the existing folder labels again. Those labels
do not replace expert verification, manuscript grade review or mask annotation.

## Reproduce

Use the repository's pinned `requirements-training.txt` environment. From the
repository root (Windows: `.venv/Scripts/python.exe` instead of `python`):

```sh
python -m scripts.mendeley_disease --workers 12
python -m scripts.prepare_disease --root dataset/mendeley-disease --mapping research/mendeley-disease-mapping.json --output dataset/mendeley-disease/manifest-v1.json
python -m scripts.train_disease --manifest dataset/mendeley-disease/manifest-v1.json --run-dir training_results/mendeley-disease-v1 --task disease --epochs 40
python -m scripts.train_disease --manifest dataset/mendeley-disease/manifest-v1.json --run-dir training_results/mendeley-health-v1 --task health --epochs 40
```

Preparation checks publisher hashes, EXIF-upright decoded-pixel hashes and
64-bit difference hashes. Near duplicates within Hamming distance 4 are joined
transitively across sources. One representative is retained with all origins;
groups with conflicting targets are quarantined. Each class's unique groups
are assigned deterministically to approximately 70/15/15 train/validation/test
with seed 42. Augmentation is excluded before splitting. Original source paths,
labels, hashes, groups, mappings, partitions and exclusions remain in the local
manifest. Existing output files/run directories are never silently reused.
The committed `mendeley-split-audit-v1.json.gz` contains the portable full split
and quarantine audit (JSON after decompression), with the local training
manifest's original fingerprint. `mendeley-split-summary.json` provides counts.

This is an **image-group split**, not a verified plant/farm/session split:
those identifiers are unavailable. dHash cannot guarantee removal of every
near duplicate. Field generalization needs a separately collected test set.

Training freezes an ImageNet MobileNetV3-small encoder, fits a class-weighted
linear head on training images, selects its epoch by validation cross-entropy,
then evaluates once on held-out test images. The report includes per-class
precision/recall/F1, confusion matrices, macro F1, seed, manifest fingerprint,
model fingerprint, preprocessing and ONNX/PyTorch numerical parity.
This CPU baseline is independent of the manuscript's planned segmentation model.

## Desktop integration

`npm start` serves the existing browser-based desktop app. In Settings choose
**Disease label lab**. The page loads only an experimental ONNX asset whose
SHA-256 agrees with its evaluation report. Predictions stay on this page and
do not change quality grades, disease masks, affected area or treatments.
Image selection and inference happen locally; model/runtime assets are served
by the same app. Browser resizing can differ slightly from PIL bilinear resize.

An evaluated disease run can be installed by copying its `classifier.onnx` and
`evaluation.json` into `www/model/disease/`, then rebuilding web assets. The lab
also loads the health run from `www/model/health/` through its task selector. It
reports a missing model if these files are absent. Do not register this classifier
as the production `disease-segmenter`: image labels cannot train lesion masks.

Torchvision code is BSD-3-Clause; see
[upstream license](https://github.com/pytorch/vision/blob/main/LICENSE).
The ImageNet pretrained backbone is identified explicitly in each experiment;
dataset licenses do not confer rights over unrelated pretrained data.

## Run evidence

Actual preparation, training, validation, test and browser checks are recorded
in the separate run report. Code availability alone is not evidence of training.
