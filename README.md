# PitayaGrade

PitayaGrade is a capstone project for AI-assisted pre-harvest quality grading and disease detection of dragon fruit. The Android application is built with Capacitor and runs its bundled ONNX model through ONNX Runtime Web.

## Intended final pipeline

1. Capture or upload a dragon-fruit image.
2. Use YOLOv8-Nano to detect and crop the fruit.
3. Grade the crop using manuscript EfficientNet-B3.
4. Analyze reviewed disease/defect regions using YOLOv8-Nano segmentation.
5. Display confidence, recommendations, history, analytics, and reports.

> This is the manuscript pipeline awaiting evaluated models and integration. The current deployed application contains the YOLOv8 ONNX model, while portions of disease analysis still use image heuristics. Selectable classifiers require explicit scope approval.

The Settings model picker now shows the complete planned catalog: YOLOv8-Nano,
MobileNetV2, ResNet50, EfficientNet-B3 and YOLOv8-Nano disease segmentation. Only
the checksum-verified bundled YOLOv8-Nano asset is selectable today. Pending models
are visibly disabled until an evaluated ONNX file, output contract and checksum are
added to `js/model-registry.js`; the build rejects missing or altered selectable
assets. This preserves the required selection workflow without presenting invented
or historical checkpoints as validated models.

## Main directories

- `www/` — production web assets packaged by Capacitor
- `android/` — Android Capacitor project
- `js/` and `css/` — editable application source
- `training_results/` and `yolo_results/` — retained experiment outputs
- `assets/diagrams/` — software architecture diagrams
- `pitaya_grade/` — earlier Flutter prototype
- `pitayagrade-apk/` — earlier Cordova-style prototype

## Run the web application

```bash
npm ci
npm start
```

Open `http://127.0.0.1:4173`. The local server serves only packaged assets,
sets JavaScript-module/WASM content types and disables caching for development.
Use the `PORT` environment variable if that port is occupied.

Serve the repository root or `www/` through a local HTTP server. Opening the HTML directly through `file://` may prevent ONNX Runtime from loading model assets correctly.

## Android development

Requirements:

- Node.js and npm
- Android Studio with an Android SDK
- Java version compatible with the Android Gradle configuration

Install dependencies and synchronize the application:

```bash
npm install
npx cap sync android
```

After editing `index.html`, `js/`, or `css/`, run `npm run build` to update
`www/`, or `npm run sync:android` to also synchronize the Android project.
Run `npm test` for asset wiring and inference regression checks.
Both web entry points use the bundled ONNX runtime and model without a CDN.
Photo scans report model fallback explicitly; disease analysis remains heuristic.
New scans retain their analysis methods and report physical size as not measured.
Existing records are preserved, including earlier framing-based size estimates.
Symptom guidance describes possible signs to inspect, not confirmed findings.

The test suite executes the actual shipped detector with its WASM backend as
well as checking application workflows. This is a runtime test, not an accuracy
evaluation. `npm run test:inference` runs that check on its own.

The pinned ONNX Runtime Web 1.19.0 bundle includes its JavaScript loader,
`ort-wasm-simd-threaded.mjs` and matching WASM binary. Builds verify all three
against `www/runtime-assets.json` so missing/mismatched runtime files cannot be
packaged silently. To regenerate it, install `onnxruntime-web@1.19.0` separately
and run `python setup_onnx.py --runtime-dir <installed-package-directory>`.
That command does not replace model weights. Runtime requirements are documented
by [ONNX Runtime](https://onnxruntime.ai/docs/tutorials/web/deploy.html).

GitHub Actions runs app and lightweight research checks, builds the debug APK,
and retains the APK/lint reports as workflow artifacts. ML runtime checks still
run separately in the pinned research environment; CI does not train research models.

Open the Android project:

```bash
npx cap open android
```

On Windows, build and run the regression/lint checks together:

```powershell
./scripts/build-android.ps1 -JavaHome D:/Android/jbr
```

Use your own Java 21 path if Android Studio is installed elsewhere. The script
uses `ANDROID_HOME` or the current user's `AppData/Local/Android/Sdk`; pass
`-SdkRoot` to override. SDK platform 36 must be installed and its licenses
accepted. Output: `android/app/build/outputs/apk/debug/app-debug.apk`.
This is a debug build, not proof of model accuracy or device validation.

## Machine-learning assets

The supported quality-training command requires a reviewed manifest and a fresh
run directory. See [the preparation guide](research/PREPARATION_GUIDE.md).
It trains manuscript EfficientNet-B3; historical model comparisons do not approve
adding selectable classifiers to the app.

After every quality model has produced predictions for the same frozen test split,
create a CSV using `research/week4/predictions-template.csv` and run
`python -m scripts.summarize_model_evaluation --help`. The tool fails on incomplete,
duplicate or incompatible predictions and generates traceable metrics, confusion
matrices, latency summaries and mistake lists. It does not create missing labels or
replace field evaluation.

YOLO dataset preparation likewise requires reviewed fruit boxes. The Colab entry
point uses the reviewed quality-training workflow. See the preparation guide for
commands and remaining methodology gaps; a new one-class detector cannot directly
replace the app's existing four-grade model.

`train_segmentation.py` prepares reviewed disease-region polygons on fruit crops
and supports YOLOv8n-seg training. See the preparation guide for its separate
manifest contract and Healthy negative samples. This research workflow does not
replace the app's heuristic disease output or establish model accuracy.

The deployed web model is stored under `www/model/`. Large training datasets and framework checkpoints are intentionally excluded from Git because the local project is several gigabytes. Dataset sources, licenses, splitting procedures, preprocessing, and final evaluation results should be documented before the capstone release.

## Research warning

Model performance must be recalculated using a leakage-free, untouched test set. Consecutive video frames and augmented copies from the same source must not appear across training, validation, and test partitions.

## Documentation

See [CONTINUATION_UPDATE.md](CONTINUATION_UPDATE.md) for the latest module-by-module
changes, verification results, storage behavior, and remaining implementation gaps.

Use [the Week 4 evaluation plan](research/WEEK4_EVALUATION_PLAN.md) and its
[evidence templates](research/week4/README.md) for formal model evaluation,
physical-device testing, UAT, manuscript revision and release approval. The blank
templates are not completed evidence and must be filled from actual test runs.

The active Capacitor app stores scans in `localStorage` under `pg_scans` and
settings under `pg_settings`. There is no active backend, authentication service,
or user-role system. The SQLite service in the Flutter prototype is separate.

The capstone manuscript is available in `PitayaGrade_Capstone_Paper.md`. It describes the proposed system and should be revised whenever the implemented architecture or measured results change.
