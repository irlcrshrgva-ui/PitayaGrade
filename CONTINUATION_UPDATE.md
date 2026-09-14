# Project continuation update

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
