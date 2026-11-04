# Similar-color object rejection fix — 5 November 2026

The user reported a similarly colored ball being accepted as dragon fruit. The
original photo was not supplied, so that exact case has not been reproduced.

## Changes delivered

- Removed color-only grade assignment when model inference is unavailable.
  Photo, live and the legacy live pixel-analysis entry point now return an
  unrecognized result without a grade in this situation.
- Require valid model grade, confidence and fruit localization before producing
  a graded result. Invalid or missing bounding boxes cannot use a heuristic ROI.
- Run the existing binary presence model a second time on the detector's object
  crop for all four grading models. A fruit-like full scene cannot substitute
  for the detected object. A failed/missing crop check stops grading.
- Enforce the existing 0.50 object-detection floor for the integrated YOLO grader
  as well as the classifiers. Lowering the UI slider cannot bypass this floor.
- Keep rejected images out of graded history, reports and analytics. If recognition
  is unavailable, the app says that no grade was assigned.
- Bump the web cache version so updated browser deployments can load the changes.

The model weights and binary threshold were not changed. Disease heuristics remain
available only after the fruit passes recognition. Yellow-fruit support remains
unavailable. This change does not establish physical presence or reject all
screen-displayed fruit.

## Verification

- Complete JavaScript suite: **118 passed**, zero failures/skips.
- Regression tests cover rejected object crops for all four graders, unavailable
  verification, invalid localization, valid fruit, and removal of the heuristic
  grading fallback in photo and legacy live paths.
- Android synchronization, debug APK build and Android lint: **passed**.
- APK: `android/app/build/outputs/apk/debug/app-debug.apk`.
- APK SHA-256:
  `a4449c00259d1d78d43d4b41ee0d1eae2a33f9a13648769b401c253cdcbaa15c`.

## Image diagnostic

`scripts/benchmark_object_rejection.py` ran the shipped ONNX models on 226 frozen
quality-test fruit photos and 350 non-fruit cases. The latter comprise 175 source
files and their synthetic magenta-tinted variants, including 40 ball files
(80 ball cases), strawberries, flowers, faces and common objects.

| Model-check result | Previous scene + detector checks | Added crop check |
|---|---:|---:|
| Fruit photos passing | 194 / 226 | 194 / 226 |
| Non-fruit cases passing | 1 / 350 | 0 / 350 |
| Ball cases passing | 0 / 80 | 0 / 80 |

The added check removed a strawberry false pass without removing any previously
accepted fruit photo in this diagnostic. The 32 already-rejected fruit photos
remain rejected. The table measures model checks; subsequent color and exposure
checks in the application can reject more images.

Raw predictions and source/model checksums are retained in
`research/OBJECT_REJECTION_DIAGNOSTIC_2026-11-05.json`.

These are regression diagnostics, not field accuracy: negative source files may
overlap the presence model's training data, tinted variants are synthetic, and
Pillow/browser interpolation may differ. Physical phones, the user's actual ball,
varied lighting, distance and real fruit still require testing. The unavailable-
model fallback was a concrete acceptance loophole; it is not proven to be the
cause of the user's particular scan.
