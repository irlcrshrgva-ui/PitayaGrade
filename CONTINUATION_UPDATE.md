# Project continuation update

## 2026-10-01 continuation: verified Android and Git handoff

- Consolidated the pending app, native report export, localization, notifications,
  reviewed-data preparation and training changes for version control.
- Rebuilt and synchronized the production web assets and Capacitor Android app.
  Removed unused legacy external-storage permissions; report export uses Android's
  document destination picker. Moved permissions/features before the application
  element to resolve manifest-order lint warnings.
- Verification: 43 JavaScript tests, 59 lightweight Python tests and 23 ML runtime
  tests pass. Android `assembleDebug` and `lintDebug` succeed: 0 errors, 25 warnings.
  ML tests use synthetic fixtures and do not establish research accuracy.
- APK: `android/app/build/outputs/apk/debug/app-debug.apk`. No Android hardware
  is connected, so camera, export, printing and lifecycle device checks remain open.
- The project still needs genuine reviewed annotations, evaluated model exports,
  integration of the manuscript detector/classifier/segmenter pipeline, calibrated
  preprocessing/severity and field/UAT evidence. The bundled detector and heuristic
  disease output have not been represented as a completed research pipeline.
- Owner requested autonomous continuation and a Git push without routine
  confirmation prompts. Missing research evidence is a technical dependency,
  not a request for another scope confirmation.
- Integrated the newer GitHub model-registry/settings changes, retaining both
  model selection and notification preferences. The registry currently contains
  only the bundled YOLOv8-Nano model; additional trained models were not invented.

## 2026-09-21 continuation: preprocessing research preview

- Added `python -m scripts.preprocessing_preview` for explicit-config HSV/GrabCut,
  LAB luminance CLAHE and threshold-controlled 3x3 Gaussian blur. Requires all
  settings; does not guess research thresholds or modify training/app inputs.
- Saves upright source, HSV seed, fruit mask, lighting and processed previews,
  with exact configuration, source/output hashes, versions and measurements.
  Rejects unusable initialization/masks and existing output directories.
- Tests cover synthetic segmentation, threshold behavior, repeatability, EXIF,
  invalid configurations, output provenance and source preservation. All eight
  new OpenCV tests pass; dependency consistency and whitespace checks pass.
  The 55 lightweight and nine prior ML checks passed in preceding continuations.
- Pinned the already-installed OpenCV 5.0.0.93 dependency. Documented native-size,
  orientation-first preview order and the limitations of Laplacian variance as
  a noise proxy. Parameter calibration and training/deployment integration still
  require completion. No real-data accuracy or full methodology alignment claimed.

## 2026-09-21 continuation: traceable fruit crop preparation

- Added `python -m scripts.reviewed_crops` to export one upright lossless crop per
  reviewed fruit box. Retains source snapshots, image hashes, box index, exact
  pixel bounds and box-review evidence. Source groups and splits are inherited.
- Raw boxes follow all eight EXIF modes; upright boxes are preserved. Fractional
  bounds round outward. Original images and existing output directories are
  preserved; grade labels and symptom masks are never invented or inherited
  from the detection label.
- Generated review manifests deliberately fail training readiness until genuine
  grade/disease review is supplied. Commands and review steps are documented in
  `research/PREPARATION_GUIDE.md`.
- Verification: all 55 lightweight Python tests pass, including six new crop
  tests; CLI help and whitespace checks pass. The nine ML runtime tests passed
  in the preceding continuation; they were not rerun for this Pillow-only change.
- HSV/GrabCut, CLAHE and selective noise filtering still need implementation and
  evidence-based parameter choices. No evaluated model or app inference changed.

## 2026-09-21 continuation: reviewed disease segmentation

- Completed the interrupted segmentation preparation/training handoff. The
  workflow requires reviewed fruit-ROI polygons for six symptom classes and
  explicitly reviewed Healthy crops with empty masks. It rejects missing review
  evidence, incompatible labels, invalid polygons and incomplete class coverage.
- Exports upright images and coordinate-correct polygons while retaining source
  files, manifest snapshots and image provenance. Added a source-image split check
  so distinct crops of the same `roiSourceId` cannot leak across partitions even
  when their reviewed group IDs differ.
- The pinned YOLO segmentation adapter monitors validation mask loss along with
  its other loss components. The preparation guide now documents its required
  fields, commands, negative-sample representation and limitations.
- Verification: 49 lightweight Python tests and 9 real-library ML tests pass,
  including two-epoch detection and segmentation CPU runs. CLI help and whitespace
  checks pass. Synthetic fixtures do not establish research accuracy.
- Reviewed research annotations, full preprocessing, crop provenance verification,
  fruit-surface severity calculation, architecture resolution, app integration
  and real device/user evaluation remain outstanding.

## 2026-09-20 continuation: orientation and image/box consistency

- Quality training now corrects EXIF orientation before resizing, augmentation
  and normalization, for training, validation and test images.
- Detection preparation requires an explicit raw/upright coordinate declaration
  for oriented images. It exports upright PNGs, transforms raw-space boxes and
  avoids double-transforming already-upright annotations. Original files and
  manifests remain intact; `prepared-images.json` records source/output hashes,
  dimensions, orientation and boxes.
- Validation now detects identical upright pixels across splits even when their
  stored pixels differ due to orientation. Invalid metadata and ambiguous
  annotation coordinates stop preparation. This does not detect near duplicates
  or replace actual source-fruit grouping.
- Added tests for all eight orientation modes, box/pixel correspondence,
  duplicate leakage, source preservation and the actual quality data loaders.
- Verification: all 35 lightweight Python tests and 7 real-library ML tests pass;
  syntax and whitespace checks pass. Tests used synthetic temporary fixtures;
  no research model or deployed application asset was replaced.
- No research labels were created or revised. HSV/GrabCut, CLAHE and selective
  noise-filter parameters, crop provenance, disease segmentation, deployment
  architecture and field/device evaluation still require completion.

## 2026-09-20 continuation: validation-loss training behavior

- Corrected quality training to select/restore the lowest validation-loss
  checkpoint across both phases, rather than the highest validation accuracy.
  Both phases now use ReduceLROnPlateau (patience 5, factor 0.5), ten-epoch
  loss-based early stopping and Adam weight decay 1e-4. Phase two fine-tunes
  the upper three feature blocks and preserves frozen BatchNorm statistics.
- Added a version-tested Ultralytics trainer adapter: checkpoint selection and
  early stopping monitor summed validation detection losses; validation drives
  the plateau scheduler. Adam beta_1 is explicitly 0.9. Unsupported adapter
  versions and missing/nonfinite losses stop training rather than falling back.
- Created an isolated ignored `.venv` with CPU PyTorch 2.14.0, torchvision 0.29.0,
  Ultralytics 8.4.156 and the remaining packages in `requirements-training.txt`.
  Run context now records quality-training settings and dependency versions too.
- Synthetic runtime tests exercise real PyTorch/EfficientNet and Ultralytics,
  including a two-epoch CPU detector run. They do not use or alter the public
  research dataset and do not establish research accuracy. Test checkpoints are
  temporary and are removed when the tests finish.
- Verification: all 27 lightweight Python tests and 6 ML runtime tests pass;
  dependency consistency and whitespace checks pass. No app assets changed.
- These corrections supersede the earlier scheduler/stopping gap below. Real
  reviewed labels/boxes, crop/preprocessing verification, disease segmentation,
  architecture resolution, and device/UAT evidence remain outstanding.

## 2026-09-20 continuation: detector annotations and Colab entry point

- Replaced YOLO's invented centered 88% boxes and grade-folder conversion with
  actual reviewed normalized boxes. Requires separate annotation review evidence,
  image integrity, source-group separation and fresh output directories.
- The detector prepares a single Dragon Fruit class, consistent with manuscript
  localization before separate grading. Training uses 128-pixel inputs, batch 32,
  and 10/30-epoch transfer-learning phases. Remaining scheduler/early-stopping
  differences are explicit in the guide and generated training context.
- Removed automatic package installation, stale checkpoint export and app-copy
  guidance. A one-class detector cannot replace the deployed four-grade model.
- Replaced the old Colab experiment with a launcher for reviewed quality training.
  Removed embedded Kaggle credentials from that file and `download_dataset.py`.
  The exposed credential still needs revocation/rotation by its account owner;
  local edits do not revoke a credential or erase it from Git history.
- Corrected the quality trainer's CUDA memory-property typo. Added ten detector
  tests; all 22 Python and 37 JavaScript tests pass. The actual public manifest
  was rejected by detector preparation (12,203 validation errors) before creating
  output or importing training frameworks. Training-order tests use a fake trainer and
  synthetic images; they are software checks, not actual ML performance evidence.
- No real model training, ONNX export, APK rebuild or deployed asset change occurred.
  Reviewed annotations, final methodology alignment, disease segmentation and
  hardware/user evaluation remain required.

## 2026-09-20 continuation: reviewed quality-training gate

- Replaced `train_models.py` ripeness-to-grade mapping and random image splitting
  with mandatory reviewed-manifest validation. Preserves reviewed partitions and
  checks file/pixel hashes, label coverage and source-group separation.
- Defaults to manuscript EfficientNet-B3. New run directories prevent accidental
  reuse of historical metrics/prepared data; each run retains its input manifest.
- Added eight regression tests; all 12 Python and 37 JavaScript tests pass.
- The actual public review manifest was rejected with 6,103 validation errors,
  including missing review evidence and incompatible/missing grade labels. The
  attempted command created no run directory and trained no model.
- No training or accuracy claim is authorized by metadata alone. Expert labels,
  real detection/disease annotations, independent evaluation and device/UAT evidence
  remain outstanding. The manuscript and deployment architecture were not amended.
- The detector/Colab changes above supersede the original follow-up audit item.
  Instructions and outstanding limitations are in `research/PREPARATION_GUIDE.md`.

## 2026-09-20 continuation: working Android build

- With the owner's SDK license/install approval, installed official Android
  command-line tools (download SHA-256 checked), platform 36, platform tools and
  build tools. Gradle also installed its required Build Tools 35. Java 21 comes
  from the existing Android Studio `D:/Android/jbr` installation.
- Corrected the ignored local SDK configuration to the current Windows profile.
  Added `scripts/build-android.ps1`, which synchronizes assets, runs tests, syncs
  Capacitor, builds the debug APK and runs lint; failures stop the script.
- End-to-end script succeeds: 37 JavaScript tests pass; Android assembly and lint
  succeed. App lint reports 0 errors and 28 warnings (storage permissions,
  manifest order, dependency update suggestions and resource/icon issues).
- APK signature verifies. All 16 matching packaged web assets were checked against
  `www/` by SHA-256, including the model and runtime. The newly generated APK is
  copied as `PitayaGrade-debug-2026-09-20.apk`; the June APK remains untouched.
- The new debug certificate differs from the old APK. It cannot update that old
  installation in place. Preserve existing records and obtain the original signing
  key for an in-place update; do not uninstall an existing app just to bypass this.
- `adb devices -l` found no devices. Camera, offline first run, exports and lifecycle
  remain unverified on Android hardware. Reviewed labels/test data and the owner's
  final architecture decision remain necessary to finish the capstone honestly.

## 2026-09-20 continuation: dashboard saved-record rendering

- Escaped saved thumbnail attributes, disease names and processing-time text in
  dashboard recent scans. Grade CSS classes now derive from the four allowed
  labels instead of trusting stored markup. Records are not rewritten.
- Separated grade and disease text in dashboard/history rows so presentation
  translations can apply independently. Assessment titles translate while keeping
  Grade A/B/C/Reject unchanged.
- All 37 JavaScript tests passed, including the expanded dashboard/history
  injection regression and raw-storage preservation check. Source, packaged web
  and Android assets are synchronized. No new APK or device validation occurred.
- Final submission remains blocked by missing reviewed model evidence, the
  unresolved architecture decision and unavailable Android SDK configuration.

## 2026-09-20 continuation: result integrity and release attempt

- Removed the hard-coded 99.4% verification confidence from unrecognized-image
  results. Rejected detections still produce no saved grade record.
- Grade notifications now require physical verification before use or market
  decisions. Added Filipino translations for those messages and local aggregate
  insight summaries/actions/limitations.
- History renders escaped presentation copies of stored text, including symptoms,
  size, thumbnail attributes and recommendations. Grade/style classes and icons
  come from app-controlled values. Raw records, notes and CSV values are retained.
- The 37-test JavaScript suite covers these regressions alongside existing storage,
  report, scanner and localization checks. Web/Android assets are synchronized.
- Attempted `assembleDebug` using `D:/Android/jbr` (Java 21). Gradle 8.14.3 ran,
  but the build failed with `SDK location not found`; the configured SDK path
  belongs to an absent Administrator account. No APK was built or device tested.
- Completion still depends on reviewed model data, the owner's architecture
  decision, Android SDK setup and real device/research evaluation. The manuscript
  has not been amended and no new model-performance claim has been made.

## 2026-09-20 continuation: assessment and chart translations

- Extended Filipino presentation coverage to scan/history maturity, size, color,
  surface descriptions, symptom guidance, limitations and record actions. Numeric
  estimates and Grade A/B/C/Reject remain unchanged; English originals restore
  when switching back. Stored records and notes are not rewritten.
- Dashboard chart empty states, total labels and disease labels now use the
  language dictionary when drawn. Trend weekdays use the selected locale. Charts
  redraw through existing navigation and refresh handlers.
- All 34 JavaScript tests passed. After two final dictionary additions, all seven
  localization tests passed again. Web and Android assets were synchronized.
- Browser verification covered Filipino settings/analytics navigation, visual
  inspection of analytics and switching back to English. Populated result screens
  and physical Android behavior were not browser-tested in this continuation.
- Remaining work includes other dynamic insight/diagnostic text, validated grade
  and disease models, and device/release testing. No APK was built.

## 2026-09-20 continuation: dynamic notification localization

- Separated unread markers from notification titles so dictionary translations
  work for unread and read alerts alike.
- Added Filipino presentation text for session grade counts, possible-disease
  titles, grade alerts, relative times, confidence values and unrecognized-image
  guidance. Stored notification text, grade categories and user notes are retained.
- All 32 JavaScript regression tests pass, including dynamic summary counts and
  switching back to the original English text. Web and Android assets were
  synchronized; diff whitespace validation passed. No browser/device verification
  or APK build was performed in this continuation.
- Localization remains partial (including canvas labels and detailed guidance).
  Validated classifiers, disease models and Android device testing remain open.

## 2026-09-20 continuation: report text, confirmations and recommendations

- Added Filipino translations for deletion confirmations, report headings and
  empty states, camera/storage errors and the main harvest/grading recommendations.
  Confirmation cancellation is preserved; translating a prompt does not authorize
  or trigger deletion. Some dynamic text, canvas labels and detailed guidance
  still need translation coverage.
- Recommendations now describe possible disease symptoms and require inspection
  before treatment, confirm ripeness before harvest, and avoid claiming Grade A
  establishes export eligibility. Stored grade categories were not changed.
- Escaped disease names and size fields in report HTML, including the disease
  summary table. Imported or modified local text cannot become executable markup
  through these fields. Reports describe disease counts as estimates.
- All 31 JavaScript regression tests pass, including confirmation cancellation,
  report escaping and recommendation wording checks. Web and Android assets are
  synchronized. This does not validate model accuracy or constitute an APK build.

## 2026-09-20 continuation: English/Filipino interface

- Added `js/language.js` and a saved English/Filipino selector under Settings.
  Navigation, common controls, empty states, tutorial messages, selected error
  messages and result headings translate without changing stored grade labels.
- Dynamic UI text is refreshed through a mutation observer; English originals
  are retained for switching back. Textarea content and report notes are excluded
  from translation. CSV keeps the original stored values.
- This is partial localization: detailed assessment guidance, some dynamic
  summaries, canvas text and native confirmation dialogs remain in English.
  The Settings caption states that detailed guidance remains in English. Full
  bilingual coverage under manuscript section 4.2.1 remains incomplete.
- Three localization regressions cover switching back, dynamic replacements,
  protected notes/grade labels and fallback text. All 28 JavaScript tests passed
  before the final dictionary extension; the three localization tests were rerun
  successfully after that extension. Browser switching was verified on a fresh
  app origin after the older preview appeared to retain stale assets.
- Source, `www/` and Android assets are synchronized. No APK or new model was
  produced. Grade A/B/C/Reject remains the owner's required grading scheme.

## 2026-09-20 continuation: retain manuscript grades

The owner explicitly retained Grade A/B/C/Reject and requested continued work on
other features. No replacement with Fresh/Defective outputs was authorized.

- Settings now includes a persisted Scan alerts checkbox. Disabling it suppresses
  new scan/session notifications without deleting records or previous alerts.
  The preference was checked through a browser reload.
- Session summaries cover fixed 60-minute windows anchored at the first scan,
  with counts for all four grades and image-based disease flags. The most recent
  session is checked on app startup, foregrounding and scan changes. While open,
  the app schedules its summary at the window end. The saved summary marker
  prevents duplicate delivery after clearing alerts. This is an in-app feature,
  not background Android push; older missed sessions are not backfilled.
- `scripts/prepare-public-data.py` exports 3,050 deduplicated task records from
  3,047 unique pixel images, keeping original source labels and image bytes.
  `research/public-review-manifest.json` provides review fields and provisional
  70/15/15 partitions; identical images share partitions across tasks. Related
  nonidentical images still require source-group review before evaluation.
- `scripts/validate-research-data.py` checks labels, source-group review metadata,
  class coverage, duplicate leakage and image checksums. The current manifest
  correctly fails the manuscript-quality check. These are preparation tools;
  no trained model or accuracy claim is produced.
- Validation: 25 JavaScript tests and four Python research-validation tests pass.
  Android asset synchronization is repeated after this update; APK/device testing
  and the model/research blockers described above remain outstanding.

## 2026-09-19 continuation: manuscript alignment and in-app alerts

The owner selected `PitayaGrade_Capstone_Paper.md` as the governing document.
`research/SCOPE_ALIGNMENT.md` records implementation gaps and unresolved research
decisions. No grading categories or manuscript claims were changed.

- Connected the existing notification module to a header button and native modal
  dialog, with unread counts, mark-all-read and clear-alert controls. Saved scans
  now trigger the existing alert logic. This implements part of section 4.2.3;
  Firebase push, session timing and periodic advisories remain incomplete.
- Invalid notification storage is preserved; failed writes retain existing state.
  Notification and toast content is escaped. Heuristic disease alerts explicitly
  describe possible conditions and do not claim confirmed diagnoses.
- Added four notification regressions; all 22 JavaScript tests pass. Browser
  checks confirmed the empty dialog, readable styling and Escape dismissal.
- Web assets and Capacitor Android assets were synchronized. No APK was built:
  the saved SDK path belongs to the previous Administrator account and Java was
  not found on PATH. Actual device verification remains outstanding.
- Downloaded the reviewed public quality and maturity originals into ignored
  `dataset/public/` for inspection, with SHA-256 verification and source records.
  All 3,779 entries decode, but 509 pixel-identical duplicate groups were found
  across the combined collection. These groups must not cross evaluation splits.
  `scripts/inspect-public-data.py` records source labels and image groups without
  inventing Grade A/B/C labels. Training and model deployment have not occurred.

Current results: `research/public-data-inspection.json`; download provenance:
`research/quality-download.json` and `research/maturity-download.json`.
The following earlier continuation details remain historical context; the
notification panel gap described below has now been addressed as stated above.

The active implementation is the Capacitor web app: `index.html`, `js/`, `css/`,
and generated `www/` assets. Existing page styling, navigation structure, record
fields, local-storage keys, and the Flutter SQLite schema were preserved.

## 1. Record persistence and cross-module refresh

**Change:** Added shared validated storage access. Malformed JSON, invalid records,
and unavailable storage no longer crash all record views. Valid records are sorted
newest first. Mutations refuse to overwrite unreadable or partly invalid record
collections. Successful writes broadcast a change event.

**Location:** `js/storage.js`: `ScanStore.read`, `validScan`, `getScans`,
`saveScans`, `clear`; `js/app.js`: `PitayaApp.init`; record reads/writes in
`js/scanner.js`, `js/history.js`, `js/dashboard.js`, and `js/reports.js`.

**Reason:** Each module previously parsed and wrote local storage independently,
with no common failure handling or refresh contract.

**Result:** Save, note edit, delete, and clear operations keep history, dashboard,
analytics, and report previews consistent. Cross-tab scan changes also refresh
views. Invalid original data remains in storage; no automatic data migration or
destructive repair is performed. The existing 500-scan retention policy remains.

## 2. History notes and deletion

**Change:** Added the missing notes editor and Save Notes action to the existing
record detail sheet, with a 2,000-character limit, escaped text rendering, error
feedback, and persistent updates. Deletion handles storage failures before
claiming success or closing the sheet.

**Location:** `js/history.js`: `showDetail`, `deleteScan`;
`js/storage.js`: `updateNotes`; existing `notes` field in `pg_scans`.

**Reason:** Records had a notes field and history advertised notes search, but
there was no interface for entering or editing notes.

**Result:** Notes survive reloads and can be searched in history and exported.

## 3. Reports and CSV export

**Change:** Validated required dates and ordering; applied local calendar dates;
included the entire ending day with an exclusive next-day boundary. Record/date
changes invalidate stale previews. Added notes to the report and CSV. CSV now
escapes embedded quotes, preserves newlines, uses UTF-8 BOM and CRLF, and
neutralizes spreadsheet-formula prefixes. Blocked print windows show feedback.

**Location:** `js/reports.js`: `_setDefaultDates`, `_getFilteredScans`,
`invalidate`, `generateReport`, `exportCSV`, `_csvCell`, `printReport`.

**Reason:** Reversed or blank dates silently produced empty reports; end-of-day
milliseconds were excluded; quoted data could break CSV rows; printing could
throw when `window.open` returned null.

**Result:** Reports use the selected local date range, include saved notes, and
handle empty data and blocked printing explicitly. Android-native sharing or PDF
export has not been added; browser CSV/print support still depends on the host.

## 4. Dashboard and analytics consistency

**Change:** Empty analytics reset totals; pending counters and gauge updates are
cancelled before replacing them; the harvest gauge uses stored maturity values
instead of deriving maturity from grade. Trend dates use local calendar days;
a single quality data point renders; disease legends clear with empty data;
hidden narrow grade charts do not draw negative-radius arcs. Active charts redraw
after resize. Local insights no longer assert pathogen spread or measured trends
from static heuristic counts.

**Location:** `js/dashboard.js`: `_updateStats`, `_animateCounter`, `_updateGauge`,
`_renderGradeChart`, `_renderDiseaseTrend`, `_renderQualityTrend`,
`_renderDiseaseBreakdown`, `_renderOfflineInsights`; `js/app.js`: resize listener;
`index.html`: harvest gauge caption.

**Reason:** Deleting all records could leave stale analytics, UTC dates disagreed
with report dates, and grade-based maturity contradicted stored assessments.

**Result:** The dashboard and analytics describe the same saved records and
maturity values, including after deletion and empty-state transitions.

## 5. Model detection and photo/live integration

**Change:** The detector returns the highest-confidence box. Its normalized
coordinates determine the existing grid ROI for disease and quality analysis.
Model-confirmed fruit bypasses fallback-only color rejection. Removed filename
blacklisting, which could reject a fruit solely because of its filename. Live
frames now call the same `_generateResult` assessment logic as photo scans,
without mutating the selected photo's pixels. Removed invented healthy/mature
defaults from the live model path.

**Location:** `js/model-inference.js`: `_postprocess`; `js/scanner.js`:
`_modelROI`, `_generateResult`; `js/live-scanner.js`: `_analyzeFrame`.

**Reason:** The trained model's box was discarded, color heuristics could override
valid detections, and live/photo disease and maturity paths disagreed.

**Result:** Both scan modes share assessment logic and use the detected region.
The ROI is quantized to the existing 128-pixel analysis grid. This does not add a
separate learned disease model or implement the proposed classifier selector.

## 6. Image and camera lifecycle

**Change:** Added image type/20-MB validation, file-read feedback, and image-request
tracking so older asynchronous uploads cannot replace newer selections. Pending
camera requests are invalidated when stopped; late streams release their tracks;
video playback errors release resources. Page hiding/navigation stops the camera.
Stale frame results are ignored and photo/live capture cannot overlap processing.

**Location:** `js/scanner.js`: `loadImage`, `resetScanner`;
`js/live-scanner.js`: `startCamera`, `stopCamera`, `_analyzeFrame`,
`captureAndAnalyze`, `cleanup`; `js/app.js`: lifecycle listeners.

**Reason:** Leaving the scan page during a permission request could activate a
camera afterwards, and older images or live results could update newer state.

**Result:** Camera ownership and image selection follow the current active scan.

## 7. Settings and unavailable feature states

**Change:** Connected the existing detection-threshold setting to a range control
and `ModelInference.CONF_THRESHOLD`, with bounded saved values and persistence
failure rollback. Connectivity reflects browser connectivity and local processing.
Offline preference is respected by the dormant cloud-insights branch. Offline and
clear-data controls support keyboard use; Escape closes the detail sheet. The
language switch is disabled and labeled pending instead of falsely claiming the
interface was translated. Alternate model status says it is not bundled.

**Location:** `index.html`: Settings page; `js/app.js`: `_bindSettings`,
`_saveSettings`, `_checkConnectivity`, `_bindModal`; `js/dashboard.js`:
`generateAIInsights`.

**Reason:** The threshold was decorative, the language button changed only its
label, and connectivity text claimed cloud/TFLite processing that was not running.

**Result:** The threshold affects both scan modes and persists across sessions.
The UI distinguishes implemented behavior from unavailable options.

## 8. Assessment provenance and simulated metrics

**Change:** Removed simulated validation metrics from new assessments. History
does not display legacy unvalidated metric objects as measured performance; those
objects remain stored unchanged. Settings and processing labels no longer claim
that EfficientNet-B3 or YOLOv8-Seg is executing. Results/reports identify disease,
maturity, and size as image-based estimates.

**Location:** `js/scanner.js`: `_getModelMetrics`, `_displayResult`;
`js/history.js`: `showDetail`; `index.html`: settings/processing copy;
`js/reports.js`: report footer.

**Reason:** Hard-coded accuracy/precision/recall figures were presented as measured
results despite no linked evaluation for the deployed pipeline.

**Result:** The app retains confidence output while no longer inventing evaluation
evidence. Existing training experiment files are retained.

## Verification and packaged files

- `tests/scanner.test.js`: asset wiring/parity, model loading, detection dimensions,
  selected threshold, bounding coordinates, and model rejection.
- `tests/workflows.test.js`: corrupt/partial storage preservation, quota failure,
  notes/search, report date boundaries, invalid dates, CSV escaping, blocked print,
  escaped report notes, analytics reset, model ROI, late camera cancellation, and
  scan error recovery.
- All 18 regression tests passed. All editable JavaScript syntax checks passed.
- Browser checks: startup/tutorial, dashboard/settings/report navigation, threshold
  persistence through reload, invalid report range feedback, valid empty report,
  and visual inspection of the settings layout.
- `scripts/sync-web.js` copies source changes into `www/`; packaged HTML and all
  corresponding `www/js/` modules were synchronized.
- Capacitor Android synchronization completed successfully, copying `www/` into
  `android/app/src/main/assets/public`. This is asset synchronization, not an APK build.
- Full trained-model accuracy, physical camera behavior, and APK/device tests were
  not verified by these checks. No accuracy claim is implied by passing tests.

## Remaining incomplete parts

1. **Selectable classifiers and separate disease model:** `www/model/`,
   `js/model-inference.js`, `js/scanner.js`, and the Settings alternate-model row.
   Only `best.onnx` is bundled. The intended MobileNetV2/ResNet50/EfficientNet-B3
   selection and separate disease classifier need compatible trained assets,
   preprocessing/output contracts, and verified evaluations.
2. **Filipino localization:** `index.html`, dynamic strings across `js/`, and
   `PitayaApp.settings.language`. A translation dictionary and complete dynamic
   string coverage are absent; the control now communicates this limitation.
3. **Notification center:** `js/notifications.js` contains `NotificationManager`,
   but the active HTML has no notification list/badge panel. Toast feedback works.
   A notifications screen exists in the old Flutter prototype; it is not part of
   the active Capacitor navigation. No new screen was invented in this update.
4. **Cloud insights:** `js/dashboard.js`: disabled `CLOUD_AI_ENABLED`, placeholder
   API key, and `_fetchCloudAI`. Local aggregate insights work. Production cloud
   use needs a defined service and secure server-side credential handling; putting
   a real key in the frontend is not a completion path.
5. **Model/research validation:** `training_results/`, `yolo_results/`,
   `schema/pitayagrade-schema.json`, and `PitayaGrade_Capstone_Paper.md` contain
   experiment/proposed-architecture material. Results must be reconciled with the
   deployed model and evaluated on a leakage-free held-out set. The requested
   schema was not rewritten to silently change the proposed research structure.
6. **Backend/authentication/roles:** none are implemented in the active app.
   `pitaya_grade/lib/services/database_service.dart` uses SQLite only for the
   separate Flutter prototype. Adding a server, accounts, or role tables would
   require a scope and schema decision, not connecting an existing active route.
7. **Device release verification:** Android camera permissions, lifecycle on real
   hardware, offline first-run inference, CSV download/printing support in WebView,
   model accuracy, and a rebuilt APK still need device-level validation.
