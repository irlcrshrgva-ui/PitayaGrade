# PitayaGrade

PitayaGrade is a capstone project for AI-assisted pre-harvest quality grading and disease detection of dragon fruit. The Android application is built with Capacitor and runs its bundled ONNX model through ONNX Runtime Web.

## Intended final pipeline

1. Capture or upload a dragon-fruit image.
2. Use YOLOv8-Nano to detect and crop the fruit.
3. Grade the crop using a user-selected classifier:
   - MobileNetV2
   - ResNet50
   - EfficientNet-B3
4. Analyze the crop using a separate disease classifier.
5. Display confidence, recommendations, history, analytics, and reports.

> The selectable classifiers and genuine disease model are planned features. The current deployed application contains the YOLOv8 ONNX model, while portions of disease analysis still use image heuristics.

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

Open the Android project:

```bash
npx cap open android
```

## Machine-learning assets

The deployed web model is stored under `www/model/`. Large training datasets and framework checkpoints are intentionally excluded from Git because the local project is several gigabytes. Dataset sources, licenses, splitting procedures, preprocessing, and final evaluation results should be documented before the capstone release.

## Research warning

Model performance must be recalculated using a leakage-free, untouched test set. Consecutive video frames and augmented copies from the same source must not appear across training, validation, and test partitions.

## Documentation

The capstone manuscript is available in `PitayaGrade_Capstone_Paper.md`. It describes the proposed system and should be revised whenever the implemented architecture or measured results change.

