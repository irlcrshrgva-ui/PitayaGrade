# Review data before model training

## Excel-friendly review worksheet

Do not edit the large JSON manifest by hand. Export only the task being reviewed:

```powershell
python -m scripts.review_manifest export research/public-review-manifest.json `
  research/quality-review.csv --task quality
```

Open the CSV in Excel or another spreadsheet editor. For every reviewed row, fill
`reviewedLabel`, `reviewedSourceGroup`, `reviewer` and timezone-aware `reviewedAt`
(for example `2026-10-04T18:30:00+08:00`). Leave all four blank when a row has not
been reviewed. Preserve the `id` column and do not change image/source fields.

Merge the worksheet into a new manifest without overwriting the source:

```powershell
python -m scripts.review_manifest import research/public-review-manifest.json `
  research/quality-review.csv research/quality-reviewed.json `
  --target manuscript-quality
python scripts/validate-research-data.py research/quality-reviewed.json `
  --target manuscript-quality
```

The importer rejects duplicate/unknown IDs, incomplete review evidence, incompatible
labels, timestamps without a timezone and attempts to overwrite existing reviews.
The validator remains the authority for file hashes, class coverage and split leakage.

The owner retained the manuscript's Grade A/B/C/Reject outputs on 2026-09-20.
Fresh/Defective and Mature/Immature remain original source labels only.

## Generated files

- `dataset/public/prepared/`: original image bytes, one image per task/pixel hash.
- `research/public-review-manifest.json`: file paths, source rows, checksums,
  original labels, candidate partitions and empty review fields.
- `research/public-preparation.json`: exported counts and limitations.
- `research/public-image-groups.json`: all original row memberships per pixel hash.

Run `python scripts/prepare-public-data.py` after the inspection script to
reproduce exports. It refuses to overwrite a manifest with populated review work.
Python requires pyarrow and Pillow for the preparation/inspection workflow.

## Required review

A qualified reviewer must supply accurate target labels and the evidence needed
for the manuscript criteria, including size measurements where applicable.
`reviewedSourceGroup` identifies related images of the same fruit or video/source
sequence. It must come from provenance or actual review, not a unique value
invented per file. Record `reviewer` and `reviewedAt` honestly. Related groups must
remain in one partition; review partitions before any model tuning.

The public photographs alone do not provide reliable physical diameter measurements
or all disease diagnoses. Do not fill those gaps by relabeling ripeness categories.
This review cannot substitute for independent field evaluation or UAT.

Run:

```text
python scripts/validate-research-data.py research/public-review-manifest.json --target manuscript-quality
```

The current manifest is expected to fail. A passing metadata check verifies only
the recorded structure and file integrity; it does not prove the reviewer is
qualified, the labels are true, or all related images have been found.

File and raw-pixel checksums remain checks of the original files. The validator
also computes an upright RGB digest after EXIF correction, including image
dimensions, to reject pixel-identical upright images across partitions even if
their original stored pixels differ. This is an exact-image check, not a
near-duplicate or same-fruit detector; genuine source-group review is still needed.

## Reviewed quality training

`train_models.py` now runs this gate before importing ML frameworks or downloading
weights. It also decodes images to verify pixel hashes. After genuine review:

```text
python train_models.py --manifest research/reviewed-quality.json --run-dir training_results/reviewed-quality-run-001
```

The manifest uses the same fields as `public-review-manifest.json`. The command
trains only manuscript EfficientNet-B3, preserves reviewed partitions, and requires
a new output directory. It saves a manifest snapshot, copied input data, checkpoints,
metrics and figures there. It never resumes historical experiments or reuses the
legacy `dataset_prepared` folder. Review the manuscript's 70/15/15 proportions while
keeping source groups intact; the gate checks disjointness and class coverage,
not exact proportions or research validity. Package versions for the verified
training environment are in `requirements-training.txt` (Python 3.12).

All quality loaders apply EXIF orientation before resizing, augmentation and
normalization. This covers rotations and mirrored orientations. Original files
remain unchanged, and the run context records this input convention.

Quality training selects the checkpoint with the lowest validation loss across
both phases, starts phase two from the best phase-one weights, and stops a phase
after ten epochs without loss improvement. Both phases use ReduceLROnPlateau
(patience 5, factor 0.5) and Adam with weight decay 1e-4. Lower feature blocks and
their BatchNorm statistics remain frozen while the upper three EfficientNet
feature blocks are fine-tuned. History records loss, accuracy, learning rates and
the selected epoch; `training-context.json` records the configuration and versions.
Fruit-crop provenance and the manuscript's full preprocessing sequence still need
verification; these training corrections do not establish full pipeline alignment.

`PitayaGrade_Colab_Training.py` delegates to this same reviewed workflow. Upload
the repository (including `scripts/`) and reviewed images to the Colab runtime,
install training dependencies separately, and invoke it with the same arguments.
It no longer writes Kaggle credentials or relabels downloaded ripeness folders.

## Reviewed fruit-localization preparation

`train_yolo.py` now accepts actual reviewed fruit boxes, not grade-folder labels
or an assumed centered box. Use a separate detection manifest with the common
image/checksum/group/reviewer fields, `reviewedLabel` set to `Dragon Fruit`,
`annotationReviewer`, `annotationReviewedAt`, and `boundingBoxes`.

Each box is `[center_x, center_y, width, height]`, normalized to the image dimensions.
For example, `[0.3, 0.4, 0.2, 0.4]` is a coordinate illustration only, not an
annotation to copy onto images. Supply every visible fruit's reviewed box. Boxes
must have positive area and stay within the image. For any image whose EXIF
orientation is not 1, explicitly set `boxCoordinateSpace` to one of:

- `raw`: the reviewer drew boxes against the stored pixels before EXIF correction.
- `upright`: the reviewer drew boxes against the orientation-corrected view.

Do not guess this field. The exporter rejects ambiguous orientation/coordinates.
For orientation 1 or absent metadata, the two coordinate systems coincide and the
field is optional. Invalid orientation metadata is rejected for review.

Detection preparation writes rotated/mirrored images as upright, lossless PNGs
and transforms only boxes declared `raw`. Boxes already in `upright` space are
preserved. Unrotated source bytes are copied unchanged. The original manifest and
source files remain intact. `prepared-images.json` records output paths, dimensions,
source/output checksums, original orientation and exported boxes for traceability.

```text
python train_yolo.py --manifest research/reviewed-detection.json --run-dir yolo_results/reviewed-detection-001 --prepare-only
```

Preparation requires Pillow but does not import Ultralytics or install packages.
It preserves reviewed splits, exports one-class YOLO labels, and saves a manifest
snapshot. It rejects absent review evidence, missing/invalid boxes, image changes,
cross-split duplicate/source groups, and existing run directories. A passing
check proves structure and integrity only; it cannot establish annotation truth.
The current format covers positive fruit images; negative-background evaluation
and field validation still need to be designed/documented before claiming reliable
non-fruit rejection.

For training, install PyTorch and Ultralytics separately, omit `--prepare-only`,
and choose another **new** run directory. The script uses 128-pixel inputs and
batch size 32, with 10 frozen-backbone epochs followed by 30 epochs that unfreeze
upper backbone layers, at learning rates 1e-3 and 1e-5. It evaluates the held-out
test split after both phases and stores artifacts and framework versions in that
run directory. Pretrained YOLOv8n weights may download when training starts.

The version-tested trainer adapter uses the sum of validation box, class and DFL
losses for checkpoint selection and early stopping (patience 10). It uses
ReduceLROnPlateau (patience 5, factor 0.5) in both phases and Adam beta_1=0.9.
Ultralytics' routine pre-epoch scheduler call cannot reset reduced learning rates.
Training rejects missing/nonfinite validation losses and unsupported framework
versions. The adapter supports fresh single-device runs; resume and multi-device
training have not been implemented. Disease segmentation, full preprocessing
alignment and field evaluation remain unfinished.

The resulting one-class detector is **not compatible** with the deployed
four-grade detector interface. It is not automatically exported or copied into
the app. Detection-to-crop-to-EfficientNet integration needs separate verification
and the outstanding deployment architecture decision.

Format and training API references: [Ultralytics detection datasets](https://docs.ultralytics.com/datasets/detect/),
[training settings](https://docs.ultralytics.com/modes/train/), and
[YOLOv8 backbone layout](https://github.com/ultralytics/ultralytics/blob/main/ultralytics/cfg/models/v8/yolov8.yaml).

## Traceable fruit crops for review

After fruit boxes have been genuinely reviewed, export one crop per box:

```text
python -m scripts.reviewed_crops --manifest research/reviewed-detection.json --run-dir dataset/reviewed-crops/run-001
```

Choose a new directory inside this workspace. The command uses the detection
manifest gate, preserves original images and saves `source-manifest.json` plus
`crop-review-manifest.json`. Each crop is an upright, lossless PNG at its original
pixel scale. Raw-space boxes follow EXIF orientation; upright boxes are not
transformed again. Fractional bounds round outward to whole pixels, with exclusive
right/bottom edges. No background removal, enhancement or resizing is applied.

Crop records retain source ID, source image/hash, box index, reviewer, upright box,
pixel bounds, output hashes, source group and partition. These records make the
operation reproducible; they do not independently prove that the box identifies
the correct fruit. Retain the snapshot with any derived manifest.

The output intentionally has empty grade/disease review fields and no masks, and
will fail both training gates until reviewed. Make separate quality and disease
review manifests from it. A qualified reviewer must assign each crop's actual
label and review evidence; disease review additionally requires complete polygons
or an explicitly reviewed Healthy empty list. Keep inherited source groups and
partitions together; do not treat crops as independent source photographs.
Physical measurements for grade criteria still require genuine evidence.

Crop provenance can now be independently reproduced:

```text
python -m scripts.verify_crop_provenance --manifest dataset/reviewed-crops/run-001/crop-review-manifest.json
```

New exports retain a workspace-relative `sourceManifest` path and its SHA-256
inside each `cropProvenance`. Keep that snapshot and original source images with
derived review manifests. The verifier reconstructs EXIF-corrected crop pixels
from the retained box and checks identifiers, bounds, dimensions, review evidence,
source/crop hashes and inherited groups/partitions. Editing downstream grade/mask
review fields does not invalidate pixel provenance. Replacing a crop and updating
its hashes does: the reproduced pixels must still match its source box.

Quality/disease validation verifies any supplied `cropProvenance` before preparing
training data. Older generated crops without the snapshot pointer must be
re-exported from retained reviewed sources; do not invent snapshot fields. Inputs
without generated provenance retain the existing review contract, and their crop
origin still requires independent review. Pixel verification cannot prove the box
identifies a fruit, labels are true, or source grouping is complete.

## Visible symptom coverage

`python -m scripts.disease_coverage --manifest <mask-manifest.json> --output <new-result.json>`
measures aligned upright binary masks of the same fruit ROI. Its manifest requires
`coordinateSpace: "upright-roi"`, a `fruitMask` file and an explicit `regions` list
of `{ "label": "Sunburn", "mask": "symptom.png" }` records (use `[]` when no
regions are present). Labels use the six segmentation symptoms. Masks must contain
only 0/1/255; explicitly threshold model probabilities upstream. Relative mask
paths resolve beside the manifest. Original inputs and existing outputs are preserved.

The denominator is the nonzero fruit mask; overlapping symptom instances count
once in the total union. Per-class areas may overlap. Output records hashes,
outside-fruit symptom pixels and limitations. This is visible two-dimensional
coverage, not whole-fruit surface severity or a diagnosis. Zero area does not
establish Healthy status, and an unvalidated fruit mask is not a ground-truth
denominator. The software measurement exists; mask validation and calibrated
clinical/agronomic severity still need research evidence.

## Reviewed disease-region segmentation

`train_segmentation.py` prepares reviewed fruit crops for YOLOv8n-seg. Use a
separate manifest with the common image/checksum, partition, source-group and
review fields above. Each row additionally requires:

- `imageRole`: `fruit-roi`, and `roiSourceId`: the actual source image identifier.
  All crops of that source must stay in one split, even if their group IDs differ.
  Related fruits/video frames still need shared `reviewedSourceGroup` values.
- `annotationsComplete`: true, `annotationReviewer`, and `annotationReviewedAt`.
- `maskCoordinateSpace`: explicitly `raw` or `upright`.
- `regions`: a list of objects with `label` and `polygon`. Labels are Anthracnose,
  Stem Canker, Soft Rot, Pest Damage, Sunburn or Fungal Spots. Each polygon is a
  list of normalized `[x, y]` vertices, with at least three distinct vertices;
  omit a repeated closing point. Invalid, zero-area, self-intersecting polygons
  and polygons with holes are rejected rather than silently altered.

A reviewed `Healthy` crop must have an explicit empty `regions` list. It becomes
a negative segmentation sample, not a seventh mask class. A diseased row must
include a region matching its `reviewedLabel`; additional reviewed symptom classes
may coexist. Every partition must cover all six symptoms plus reviewed Healthy
crops. These structural checks cannot establish diagnosis or review quality.

```text
python train_segmentation.py --manifest research/reviewed-segmentation.json --run-dir segmentation_results/reviewed-001 --prepare-only
```

This command is the mask-aware validation/preparation gate; the generic
`validate-research-data.py --target manuscript-disease` checks label metadata only.
Preparation needs Pillow, preserves source files, and writes upright PNGs, YOLO
polygon labels, a manifest snapshot and `prepared-images.json` traceability.
Raw-coordinate polygons follow EXIF transformations; upright polygons stay fixed.
No masks are inferred from disease labels, boxes or image heuristics.

Omit `--prepare-only` with a fresh run directory to train using the pinned ML
dependencies. Training uses 128-pixel inputs, batch 32, the same 10/30-epoch phases
and validation-loss scheduler as detection. Its loss includes box, mask, class,
DFL and semantic components. Held-out evaluation runs after training; no exported
model is installed in the application. No predicted regions does not by itself
establish a Healthy diagnosis. Fruit-surface coverage/severity, verified crop
provenance, preprocessing, field evaluation and deployment remain unfinished.

## Research preprocessing previews

The preview tool implements HSV-seeded GrabCut, LAB-luminance CLAHE and conditional
3x3 Gaussian blur. It is separate from training and app inference so unvalidated
settings do not silently alter model inputs. Install the pinned dependencies,
then run:

```text
python -m scripts.preprocessing_preview --image dataset/path/to/crop.png --config research/preprocessing-settings.json --output-dir dataset/preprocessing-previews/run-001
```

The JSON configuration must contain exactly these fields; no research defaults
are assumed:

| Field | Required value |
| --- | --- |
| `hsvRanges` | Nonempty list of `[lower, upper]` HSV triples. OpenCV uint8 hue is 0–179, saturation/value 0–255. Use two ranges for hue wraparound. |
| `grabcutIterations` | Positive integer iteration count. |
| `claheClipLimit` | Positive finite number. |
| `claheGrid` | Two positive integers specifying horizontal/vertical tile counts, no larger than image dimensions. |
| `laplacianThreshold` | Finite nonnegative variance threshold; blur applies only when variance exceeds it. |
| `seed` | Integer 0–2147483647 for GrabCut initialization reproducibility. |

Choose settings through research review and training/validation data, keeping
the test set untouched for final evaluation. Synthetic test settings are not
recommended settings for dragon fruit. The manuscript does not supply these
parameters, so none is labeled validated.

Each new output directory contains `upright.png`, `hsv-seed.png`, `fruit-mask.png`,
`lighting.png`, `processed.png` and `preview.json`. The record includes exact
settings, dependency versions, source/output hashes, foreground fraction,
Laplacian variance, blur decision and operation order. Originals are unchanged
and existing directories are rejected. Failed segmentation stops processing.

The explicit preview convention is: correct orientation first, initialize GrabCut
from HSV at native resolution, correct LAB luminance, measure Laplacian variance
inside the eroded fruit mask, optionally blur, then set background pixels to
black. CLAHE operates on the original image's luminance before output masking.
This avoids adding black mask boundaries to the noise statistic. Native-size
processing and orientation-first differ from the manuscript's listed sequence;
the preview does not claim complete alignment or include model-specific resizing
and normalization. Training/deployment order and parameter validation remain work.

Inspect whether segmentation removes green bracts or diseased tissue and whether
lighting/blur changes relevant color or texture. A generated foreground mask is
not a reviewed disease mask or a validated fruit-surface denominator. Laplacian
variance alone cannot distinguish noise from genuine detail. No preview output
is automatically promoted to training data or a diagnosis.

Implementation references: [OpenCV GrabCut API](https://docs.opencv.org/doc/doxygen/html/d3/d47/group__imgproc__segmentation.html)
and [OpenCV CLAHE implementation](https://github.com/opencv/opencv/blob/4.x/modules/imgproc/src/clahe.cpp).

## Reproduce software checks

The local `.venv` contains an isolated CPU test environment. For another machine,
create a Python 3.12 virtual environment, install the appropriate PyTorch and
torchvision wheels (CPU or CUDA) and then `pip install -r requirements-training.txt`.
The detector adapter explicitly requires Ultralytics 8.4.156 because its trainer
extension points were verified against that version. Do not upgrade it without
rerunning the integration tests and reviewing changes.

```text
python -m unittest discover -s tests -p "test_*.py"
python -m unittest discover -s tests/ml -p "test_*.py"
```

The first suite exercises validation/preparation and policy logic. The second
requires the ML dependencies and checks real EfficientNet backpropagation,
frozen statistics, checkpoint restoration, scheduler integration and a two-epoch
YOLO detection and segmentation CPU runs, plus actual quality-loader orientation handling. It uses only
temporary synthetic fixtures and random model weights;
its generated checkpoints are cleaned up and are never research model artifacts.
The detector smoke test uses 64-pixel images and batch 2 for speed, not the
manuscript's full training configuration. Passing does not validate annotation
truth, field accuracy, deployment performance or the entire research methodology.

Orientation correction uses [Pillow's EXIF transpose operation](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose).
HSV/GrabCut, CLAHE and selective noise filtering now have a separate research
preview implementation. Parameter calibration, training/deployment integration
and effects on model performance remain unverified. None are substituted for
reviewed disease masks or quality labels.
