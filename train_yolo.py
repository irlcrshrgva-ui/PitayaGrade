"""
PitayaGrade - YOLOv8-Nano Training Script
Trains a real YOLOv8n detection model on the PH DragonFruit Dataset.

Stage 1: Detects dragonfruit in image (rejects non-dragonfruits via low confidence)
Stage 2: Classifies quality grade (Grade A / B / C / Reject) simultaneously

Output: yolo_results/weights/best.onnx  ← drop this into the Android app
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# ── Install ultralytics if missing ───────────────────────────────────────────
try:
    import ultralytics
    print(f"ultralytics {ultralytics.__version__} already installed.")
except ImportError:
    print("Installing ultralytics...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
    import ultralytics

from ultralytics import YOLO
import torch
import yaml

# ── Configuration ────────────────────────────────────────────────────────────
PROJECT_DIR   = Path(os.path.dirname(os.path.abspath(__file__)))
PREPARED_DIR  = PROJECT_DIR / "dataset_prepared"
YOLO_DIR      = PROJECT_DIR / "yolo_dataset"
RESULTS_DIR   = PROJECT_DIR / "yolo_results"

# YOLOv8 training settings
MODEL_SIZE    = "yolov8n"   # nano — smallest, fastest on mobile. swap to yolov8s for better accuracy
IMG_SIZE      = 640         # standard YOLO input (higher = slower but better small-object detection)
EPOCHS        = 100
PATIENCE      = 20          # early stopping
BATCH_SIZE    = 16          # reduce to 8 if you run out of RAM
WORKERS       = 4
SEED          = 42

# 4 grade classes (detection + grading in one model)
CLASSES = ["Grade A", "Grade B", "Grade C", "Reject"]

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"\nDevice: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
else:
    print("NOTE: No GPU found. Training on CPU will be slow (~2-4 hrs).")
    print("      For GPU, reinstall PyTorch: https://pytorch.org/get-started/locally/")


# ── Step 1: Convert dataset to YOLO detection format ─────────────────────────
def convert_to_yolo_format():
    """
    Converts dataset_prepared/ folder structure → YOLO detection format.

    Each image gets a .txt label file with one line:
        class_id  x_center  y_center  width  height   (all normalized 0-1)

    Since these are close-up fruit photos (no complex backgrounds), we assume
    the fruit fills 88% of the frame centered. This is auto-annotation —
    good enough for single-fruit images. Replace with real annotations from
    Roboflow/CVAT for production use.
    """
    if YOLO_DIR.exists() and (YOLO_DIR / "images" / "train").exists():
        count = sum(1 for _ in (YOLO_DIR / "images" / "train").rglob("*.jpg"))
        if count > 100:
            print(f"\nYOLO dataset already prepared ({count} train images). Skipping.")
            return

    print("\nConverting dataset to YOLO detection format...")

    class_to_id = {cls: i for i, cls in enumerate(CLASSES)}

    # Bounding box: centered, 88% of frame (tight enough for close-up fruit images)
    BOX_X, BOX_Y, BOX_W, BOX_H = 0.5, 0.5, 0.88, 0.88

    total = 0
    for split in ["train", "val", "test"]:
        img_out = YOLO_DIR / "images" / split
        lbl_out = YOLO_DIR / "labels" / split
        img_out.mkdir(parents=True, exist_ok=True)
        lbl_out.mkdir(parents=True, exist_ok=True)

        split_dir = PREPARED_DIR / split
        if not split_dir.exists():
            print(f"  WARNING: {split_dir} not found, skipping.")
            continue

        for cls_name in CLASSES:
            cls_dir = split_dir / cls_name
            if not cls_dir.exists():
                continue

            class_id = class_to_id[cls_name]

            for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp"):
                for img_path in cls_dir.glob(ext):
                    # Copy image
                    dst_img = img_out / img_path.name
                    if dst_img.exists():
                        # Avoid filename collision across classes
                        dst_img = img_out / f"{cls_name.replace(' ','_')}_{img_path.name}"
                    shutil.copy2(img_path, dst_img)

                    # Write YOLO label
                    lbl_path = lbl_out / (dst_img.stem + ".txt")
                    with open(lbl_path, "w") as f:
                        f.write(f"{class_id} {BOX_X} {BOX_Y} {BOX_W} {BOX_H}\n")

                    total += 1

    print(f"  Converted {total} images.")

    # Write data.yaml
    data_yaml = {
        "path": str(YOLO_DIR),
        "train": "images/train",
        "val":   "images/val",
        "test":  "images/test",
        "nc":    len(CLASSES),
        "names": CLASSES,
    }
    yaml_path = YOLO_DIR / "data.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(data_yaml, f, default_flow_style=False)

    print(f"  data.yaml written: {yaml_path}")

    # Print class counts
    for split in ["train", "val", "test"]:
        lbl_dir = YOLO_DIR / "labels" / split
        counts = {cls: 0 for cls in CLASSES}
        for lbl_file in lbl_dir.glob("*.txt"):
            with open(lbl_file) as f:
                line = f.readline().strip()
                if line:
                    cid = int(line.split()[0])
                    counts[CLASSES[cid]] += 1
        print(f"  {split}: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


# ── Step 2: Train YOLOv8-Nano ─────────────────────────────────────────────────
def train():
    print(f"\n{'='*70}")
    print(f"TRAINING: {MODEL_SIZE.upper()} — Dragon Fruit Detector + Grader")
    print(f"{'='*70}")
    print(f"  Classes : {CLASSES}")
    print(f"  Epochs  : {EPOCHS} (early stop patience={PATIENCE})")
    print(f"  ImgSize : {IMG_SIZE}px")
    print(f"  Batch   : {BATCH_SIZE}")
    print(f"  Device  : {device}\n")

    model = YOLO(f"{MODEL_SIZE}.pt")  # downloads pretrained COCO weights automatically

    results = model.train(
        data    = str(YOLO_DIR / "data.yaml"),
        epochs  = EPOCHS,
        imgsz   = IMG_SIZE,
        batch   = BATCH_SIZE,
        patience= PATIENCE,
        workers = WORKERS,
        seed    = SEED,
        device  = device,
        project = str(RESULTS_DIR),
        name    = "train",
        exist_ok= True,

        # Augmentation (matches capstone paper methodology)
        flipud  = 0.3,
        fliplr  = 0.5,
        degrees = 30.0,
        hsv_h   = 0.015,
        hsv_s   = 0.5,
        hsv_v   = 0.3,
        scale   = 0.4,
        mosaic  = 1.0,
        mixup   = 0.1,

        # Optimization
        optimizer = "Adam",
        lr0     = 1e-3,
        lrf     = 1e-5,
        warmup_epochs = 3,
        cos_lr  = True,

        # Output
        save    = True,
        plots   = True,
        verbose = True,
    )

    print(f"\nTraining complete. Best weights: {RESULTS_DIR}/train/weights/best.pt")
    return results


# ── Step 3: Validate on test set ──────────────────────────────────────────────
def validate():
    best_pt = RESULTS_DIR / "train" / "weights" / "best.pt"
    if not best_pt.exists():
        print("No trained model found. Run training first.")
        return

    print(f"\n{'='*70}")
    print("VALIDATION on test set")
    print(f"{'='*70}")

    model = YOLO(str(best_pt))
    metrics = model.val(
        data    = str(YOLO_DIR / "data.yaml"),
        split   = "test",
        imgsz   = IMG_SIZE,
        device  = device,
        project = str(RESULTS_DIR),
        name    = "test_eval",
        exist_ok= True,
        verbose = True,
    )

    print(f"\nmAP50    : {metrics.box.map50:.4f}")
    print(f"mAP50-95 : {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall   : {metrics.box.mr:.4f}")

    per_class = metrics.box.ap_class_index
    for i, cls_id in enumerate(per_class):
        print(f"  {CLASSES[cls_id]:10s} AP50={metrics.box.ap50[i]:.4f}")

    return metrics


# ── Step 4: Export to ONNX for the Android app ────────────────────────────────
def export_onnx():
    best_pt = RESULTS_DIR / "train" / "weights" / "best.pt"
    if not best_pt.exists():
        print("No trained model found. Run training first.")
        return

    print(f"\n{'='*70}")
    print("EXPORTING to ONNX (for onnxruntime-web in Android app)")
    print(f"{'='*70}")

    model = YOLO(str(best_pt))
    export_path = model.export(
        format  = "onnx",
        imgsz   = IMG_SIZE,
        opset   = 12,           # opset 12 = best onnxruntime-web compatibility
        simplify= True,         # ONNX simplifier reduces model complexity
        dynamic = False,        # fixed input shape for mobile
        half    = False,        # keep float32 (float16 needs CUDA)
    )

    onnx_src = Path(str(export_path))
    onnx_dst = PROJECT_DIR / "yolo_results" / "best.onnx"
    if onnx_src != onnx_dst and onnx_src.exists():
        shutil.copy2(onnx_src, onnx_dst)

    print(f"\nONNX model saved: {onnx_dst}")
    print(f"Size: {onnx_dst.stat().st_size / 1e6:.1f} MB")
    print("\nNext steps:")
    print("  1. Copy yolo_results/best.onnx into android/app/src/main/assets/")
    print("  2. Load with onnxruntime-web in scanner.js")
    print("  3. Run: npx cap sync android && gradlew assembleDebug")

    return onnx_dst


# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PitayaGrade YOLOv8 Training")
    parser.add_argument("--prepare-only", action="store_true", help="Only prepare dataset, skip training")
    parser.add_argument("--skip-train",   action="store_true", help="Skip training, just export existing model")
    args = parser.parse_args()

    print("=" * 70)
    print("PitayaGrade - YOLOv8-Nano Training")
    print("Dragon Fruit Detector + Quality Grader (Grade A/B/C/Reject)")
    print("=" * 70)

    # Step 1: Prepare dataset
    convert_to_yolo_format()

    if args.prepare_only:
        print("\nDataset prepared. Run without --prepare-only to train.")
        sys.exit(0)

    # Step 2: Train
    if not args.skip_train:
        train()

    # Step 3: Validate
    validate()

    # Step 4: Export
    export_onnx()

    print(f"\n{'='*70}")
    print("ALL DONE!")
    print(f"  Model  : {RESULTS_DIR}/train/weights/best.pt")
    print(f"  ONNX   : {RESULTS_DIR}/best.onnx  ← use this in the app")
    print(f"  Plots  : {RESULTS_DIR}/train/")
    print("=" * 70)
