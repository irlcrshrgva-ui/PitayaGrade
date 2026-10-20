# Executed Mendeley experiment — 2026-10-21

Repository: `irlcrshrgva-ui/PitayaGrade`. Work performed on the local checkout.
The active desktop application is the browser-based app served from `www/`;
`pitaya_grade/lib/services/ml_service.dart` belongs to the earlier Flutter
prototype and explicitly simulates its inference. There is no native Windows
application target in that prototype. This change integrates the current web app.

## Data actually processed

Both publisher version 1 records specify CC BY 4.0; full public metadata snapshots
and author/source attribution are retained alongside the class mapping.
Downloaded 5,468 individually checksum-verified MultiOrgan originals, and verified
the 3,187,709,521-byte first-source ZIP against its publisher SHA-256 before
extraction. The ZIP contains 4,497 original images and 11,024 augmented images;
only originals were prepared. Its actual labels are Good/Bad fruit/leaf, not
the named disease labels in its description. The two sources therefore form
separate `health` and `disease` tasks after joint duplicate detection.

Of 9,965 originals, 5,235 representatives were retained, 2,915 duplicate images
were removed, and 1,815 images in conflicting-label duplicate groups were
quarantined. Every retained image has a source path, SHA-256, decoded pixel hash,
dHash, duplicate group, class mapping and split in the saved manifest/audit.
An independent check of all 5,235 retained signatures found no cross-split
dHash neighbors within distance 4. This does not establish plant-level isolation.

| Task | Train | Validation | Test | Selected epoch | Validation accuracy | Test accuracy | Test macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Named conditions, 8 classes | 2,187 | 466 | 466 | 24 | 78.97% | 75.11% | 0.6859 |
| Good/Bad source labels, 4 classes | 1,480 | 318 | 318 | 33 | 89.31% | 86.16% | 0.8588 |

Both runs actually executed 40 epochs of a class-weighted linear head on a frozen
ImageNet MobileNetV3-small encoder, CPU, seed 42. Minimum validation cross-entropy
selected the epoch; held-out test labels did not select checkpoints. JSON reports
contain validation histories, per-class precision/recall/F1 and confusion matrices.
These are experimental source-dataset results, not established field accuracy.
They are not A/B/C/Reject grading results and do not produce segmentation masks.

## Export and desktop checks actually executed

* PyTorch versus ONNX Runtime numerical parity passed on a real held-out image
  for each task.
* Actual shipped ONNX Runtime Web WASM execution passed for both exported models.
  Maximum absolute logit difference from the Python runtime probe was
  0.00004891 (disease) and 0.00003779 (health), below 0.001.
* The desktop browser loaded the model, verified its hash, accepted an image,
  executed inference and rendered ranked source-label predictions. The sample
  black-rot source image produced a top black-rot score of 95.3%; this is a
  wiring demonstration, not an additional accuracy estimate.
* The missing-model path was exercised in the real browser before assets were
  installed. Unit tests also reject missing/checksum-mismatched model assets.
* All 77 JavaScript tests passed, including existing detector/WASM checks and
  the new lab normalization, score-stability and safe-text-rendering checks.
* Four new Python data tests passed for deterministic partitions, decoded-image
  deduplication, conflicting-label quarantine, unknown labels, source corruption,
  output overwrite refusal and duplicate-group rejection.
* Web packaging succeeded and now verifies both experimental asset/report pairs.

The lab is linked from Settings and keeps these tasks separate from quality
grading and the pending manuscript disease-segmentation catalog entry. No
Android device/UAT/field validation or lesion-mask training is claimed.

Model SHA-256 values:

* Disease: `7bbe06f290efd14d472e6da24de81131f8958c9911f01dee30b19b2890e6474e`
* Health: `2c266ebfff10d9659c77f1b19ac04adf689aaf33689d85caead8def41eae994b`
