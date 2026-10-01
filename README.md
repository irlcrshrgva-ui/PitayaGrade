# PitayaGrade

PitayaGrade is a capstone project for AI-assisted pre-harvest quality grading and disease detection of dragon fruit. The Android application is built with Capacitor and runs its bundled ONNX model through ONNX Runtime Web.

## Intended final pipeline

1. Capture or upload a dragon-fruit image.
2. Use YOLOv8-Nano to detect and crop the fruit.
3. Grade the crop using manuscript EfficientNet-B3.
4. Analyze reviewed disease/defect regions using YOLOv8-Nano segmentation.
5. Display confidence, recommendations, history, analytics, and reports.

> This is the manuscript pipeline awaiting evaluated models and integration. The current deployed application contains the YOLOv8 ONNX model, while portions of disease analysis still use image heuristics. Selectable classifiers require explicit scope approval.

## Main directories

- `www/` — production web assets packaged by Capacitor
- `android/` — Android Capacitor project
- `js/` and `css/` — editable application source
- `training_results/` and `yolo_results/` — retained experiment outputs
- `assets/diagrams/` — software architecture diagrams
- `pitaya_grade/` — earlier Flutter prototype
- `pitayagrade-apk/` — earlier Cordova-style prototype

## Run the web application

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

The active Capacitor app stores scans in `localStorage` under `pg_scans` and
settings under `pg_settings`. There is no active backend, authentication service,
or user-role system. The SQLite service in the Flutter prototype is separate.

The capstone manuscript is available in `PitayaGrade_Capstone_Paper.md`. It describes the proposed system and should be revised whenever the implemented architecture or measured results change.
