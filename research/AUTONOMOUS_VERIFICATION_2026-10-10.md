# Autonomous verification — 10 October 2026

This record documents checks that can be repeated from the repository without
adviser judgment, human labeling, physical-device access or UAT participants.
It does not claim agricultural accuracy.

## Dataset integrity

### Prepared classification/YOLO snapshot

Command: `node scripts/audit-dataset.js`

- 3,501 unique image hashes.
- 0 byte-exact cross-split duplicate groups.
- 0 conflicting labels among byte-identical files.
- 3,501 YOLO label files and rows.
- 0 malformed YOLO rows.
- 0 segmentation rows; disease masks are still pending.

The result is retained in `research/dataset-audit.json`. This check cannot detect
different frames of the same fruit or source video. Human source grouping remains
required before the split can be frozen.

### Public-source snapshot

Command: `python scripts/inspect-public-data.py`

- 1,652 quality-source rows and 2,127 maturity-source rows decoded successfully.
- 3,047 unique pixel images after considering both public-source tasks.
- 509 pixel-identical duplicate groups were detected and are already accounted
  for by the deduplicated review preparation.
- 0 within-task conflicting-label duplicate groups.

The result is retained in `research/public-data-inspection.json`. Original public
labels are not equivalent to the manuscript's Grade A/B/C/Reject targets.

### Review readiness

Command:
`python scripts/validate-research-data.py research/public-review-manifest.json --target manuscript-quality`

Expected result: blocked. The validator reports missing source-group review
evidence and missing approved target labels. These failures are intentionally not
auto-filled.

## Application integration

The automated suite verifies that:

- the model catalog exposes the five planned entries;
- only checksum-verified bundled models are selectable;
- unavailable models cannot be selected;
- the bundled YOLOv8-Nano ONNX detector executes through the packaged WASM runtime;
- photo analysis releases its processing state on failure;
- face-like pixels fail the fruit-signature gate;
- an unrecognized result is not stored as a graded fruit;
- history displays the retained model/method metadata;
- reports and CSV exports now include the retained `modelUsed` value;
- editable and packaged web modules remain synchronized.

Live-camera behavior is covered only at the application-logic level, including
late camera-stream cleanup. A real camera/device test is still required.

## Automated verification result

- JavaScript: 72 passed, 0 failed.
- Python: 80 passed, 0 failed.
- Dataset/public inspection dependency: `pyarrow==26.0.0` is now pinned in
  `requirements-training.txt`.

## Manuscript consistency

The implementation description and Chapter 5 were audited against the active
application. Unsupported legacy accuracy, UAT, device-speed, reliability,
resource-use and manual-comparison numbers were removed instead of being retained
as placeholders. Chapter 5 now reports only the verified software-test counts and
measured package sizes, while clearly leaving model, device and UAT findings empty.

Chapter 4 now distinguishes the deployed YOLOv8-Nano ONNX plus heuristic workflow
from the proposed EfficientNet-B3 and disease-segmentation stages. It also states
that physical size, early disease detection and superiority to manual inspection
have not been established.

## Items deliberately left open

- Approval of labels, masks, class definitions and source groups.
- Real faces, hands, empty scenes and unrelated-object image evaluation.
- Live-camera inference on physical Android devices.
- Formal held-out metrics for the four missing models.
- UAT, adviser approval, release signing and signed-build installation.

