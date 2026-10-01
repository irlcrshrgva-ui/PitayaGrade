# Manuscript alignment and completion record

Governing document: `PitayaGrade_Capstone_Paper.md`, explicitly selected by the
project owner on 2026-09-19. Features beyond that document require an explicit
owner request and approval. This audit does not revise the manuscript or approve
changes to the research design.

## Current status — 2026-09-21

An explicit-config research preview now implements HSV/GrabCut background
segmentation, LAB-luminance CLAHE and conditional 3x3 Gaussian blur. Eight
synthetic OpenCV tests pass. It records settings, hashes and measurements, but
does not change training/app inputs. Native-resolution, orientation-first order
is documented as a preview convention. Research calibration and final pipeline
order/integration remain unresolved; older statements that these operators have
no implementation are superseded only for the preview tool.

Reviewed detection boxes can now be exported as upright fruit crops with source
hashes, pixel bounds, box review evidence and inherited groups/partitions. The
export deliberately leaves downstream grade/mask reviews incomplete. This closes
the crop-export traceability gap, but genuine crop/label review and complete
preprocessing remain required.

Disease segmentation now has a reviewed fruit-ROI polygon preparation gate and
a version-tested YOLOv8n-seg training adapter. Healthy crops are reviewed negative
samples; they are not inferred diagnoses. Source-image crops cannot cross splits.
See `PREPARATION_GUIDE.md` for commands and required annotations. Real reviewed
data, evaluated models, severity computation and deployment are still required;
the earlier unfinished-segmentation references below describe the prior state.

Quality-training update: `train_models.py` now requires reviewed manuscript labels,
source-group partitions and verified image hashes, and trains EfficientNet-B3 into
a fresh run directory. It no longer maps ripeness folders into grades. The Colab
launcher uses that same gate. YOLO preparation now requires actual reviewed fruit
boxes and produces a one-class localization dataset. Existing checkpoints remain
unvalidated. Both trainers now use validation-loss checkpoint/stopping policies
and ReduceLROnPlateau, with real-library synthetic CPU checks. Disease segmentation,
complete preprocessing alignment and deployment integration remain unfinished. The initial
audit table below describes the earlier state.

Orientation handling is now implemented for quality inputs and detection exports,
including mirrored EXIF modes, coordinate-safe box conversion and upright duplicate
checks across splits. HSV/GrabCut, CLAHE, selective noise filtering and crop
provenance remain unresolved preprocessing work; no full alignment claim is made.

**Build blocker resolved:** After the owner approved SDK license acceptance and
installation, SDK 36 was installed for the current account and the project path
was corrected. The debug APK builds; Android lint reports 0 errors/28 warnings.
All 37 JavaScript tests pass. No Android device is connected. The current debug
certificate differs from the June APK, preventing an in-place update of that
older installation. Model and architecture decisions below remain unresolved.

In-app notifications, unread/read state, alert preferences and session summaries
are now wired into the active app. English/Filipino switching works for common
controls, assessment details, recommendations and local insights; complete
dynamic-text and populated-device verification remain outstanding. The table
below records the initial audit; these entries supersede its notification and
language implementation descriptions.

The earlier Android debug build attempt reached Gradle configuration with Java 21
but failed because no Android SDK was available at the configured location:
`C:/Users/Administrator/AppData/Local/Android/Sdk`. No new APK was produced.
That setup issue was resolved as recorded above. Actual camera/offline/export
testing remains necessary before release.

The owner has been asked to resolve ONNX/local storage versus Firebase/TFLite
and provide locations of reviewed annotations/evaluation evidence. No answer or
architecture amendment has been assumed. Existing metrics remain unvalidated.

## Initial implementation traceability

| Manuscript requirement | Existing implementation / evidence | Remaining completion work |
| --- | --- | --- |
| Sections 1.5.1, 3.5: YOLOv8-Nano detection / disease segmentation and EfficientNet-B3 grading | One bundled `www/model/best.onnx`; `js/model-inference.js` handles four grade detection classes. EfficientNetB3 checkpoint exists in `training_results`, but is not integrated. | Verify expert labels and independent splits; train/evaluate the stated tasks; export and integrate validated models. A checkpoint alone is not evidence of a validated model. |
| Section 3.3.2: four quality grades and Healthy plus six disease/defect labels | `train_models.py` substitutes ripeness folders for grade labels. YOLO labels use the same four grade classes. | Obtain verified grade and disease annotations. Do not infer the manuscript's grades or diagnoses from ripeness folder names. |
| Sections 3.3.2 and 3.4: annotated fruit regions / segmentation | `train_yolo.py` generates a centered 88% box for every image. | Obtain real boxes and disease masks appropriate to the stated tasks; assumed boxes cannot verify localization accuracy. |
| Section 3.3.3: 70/15/15 evaluation split | Training script randomly partitions individual images, including frame-named images. | Establish source fruit/video groups before splitting; keep related samples together and augment training data only. |
| Sections 4.1 and 4.2: photo capture, assessment and results | Photo/live scan workflows exist. Disease, maturity and size still include image heuristics. | Replace heuristic disease output with validated model output; verify on Android hardware. |
| Sections 1.3 and 4.2.3: in-app disease/quality alerts | Notification module and toast feedback exist; persistent notification list is not wired into active HTML. | Complete in-app notification access and storage handling. Firebase push requires the project service configuration. |
| Section 4.2.1: English / Filipino | English interface; disabled language control. | Complete static and dynamic translations and check both languages. |
| Sections 3.8 and 4.2.4: records | Active app uses localStorage; SQLite belongs to the old Flutter prototype. | Resolve storage implementation against the manuscript before migration; preserve records. |
| Sections 1.5.1, 3.2, 3.8 and 4.3: cloud, offline and storage | Local ONNX inference exists; no active Firebase backend or TFLite runtime. | Manuscript places some features both in scope and under optional advanced features. Owner must resolve required release scope; do not silently substitute architectures. |
| Sections 4.3.3–4.3.4: analytics / reports | Local analytics, date-filtered reports, CSV and browser printing exist. | Verify Android export/printing and final real-data workflows. |
| Chapter 5: accuracy, speed and user evaluation | Historical metrics exist; no verified linkage to the manuscript's exact reported results was established in this audit. | Produce reproducible held-out evaluation, device benchmarks and actual UAT records before accepting numerical claims. |

## Scope decisions still needed

- Selectable MobileNetV2/ResNet50 models appear in the README and earlier proposed
  diagrams. Those are not sufficient evidence of owner approval to extend this
  governing manuscript. Do not implement model selection without locating explicit
  approval or obtaining it.
- Confirm whether cloud/Firebase and TFLite are required for submission, given
  the manuscript's conflicting scope and optional-feature descriptions. Keeping
  ONNX/localStorage as the final architecture would require an approved amendment.
- Dataset provenance, expert annotation records, field collection evidence, and
  UAT source records must come from real research activity. Do not generate them
  to match claims already written in the manuscript.

## Verification for this continuation

- Existing 18 JavaScript regression tests pass using
  `node --test tests/scanner.test.js tests/workflows.test.js`.
- `node scripts/audit-dataset.js` produces `research/dataset-audit.json` without
  changing source images, labels, splits, checkpoints or application behavior.
- The audit checks exact byte duplicates and annotation structure. It does not
  establish visual independence or validate labels, model accuracy or field results.

The capstone is not yet complete. Model/data validity, missing manuscript features,
device testing and research evidence remain acceptance requirements.
