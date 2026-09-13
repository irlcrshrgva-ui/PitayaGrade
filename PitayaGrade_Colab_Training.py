# ============================================================================
# PitayaGrade - Real CNN Model Training & Comparison
# Run this in Google Colab with GPU runtime enabled
# ============================================================================
# HOW TO USE:
# 1. Go to https://colab.research.google.com
# 2. File > Upload Notebook > Upload this .py file (or paste into cells)
# 3. Runtime > Change runtime type > GPU (T4)
# 4. Run all cells
# ============================================================================

# %% [markdown]
# # PitayaGrade - CNN Model Comparison
# **MobileNetV2 vs EfficientNet-B3 vs ResNet50V2**
#
# Trains all 3 models on the PH DragonFruit Dataset using TensorFlow/Keras
# with two-phase transfer learning as specified in the capstone paper.

# %% --- CELL 1: Setup & Install Dependencies ---
import os

# Install kaggle CLI
os.system("pip install -q kaggle")

# Set up Kaggle credentials
os.makedirs(os.path.expanduser("~/.kaggle"), exist_ok=True)
with open(os.path.expanduser("~/.kaggle/kaggle.json"), "w") as f:
    f.write('{"username":"irlcrishregpea","key":"c8fdde8fa7bf9c21ebc7167a83feec4e"}')
os.chmod(os.path.expanduser("~/.kaggle/kaggle.json"), 0o600)

print("Kaggle credentials configured!")

# %% --- CELL 2: Download Dataset ---
os.system("kaggle datasets download -d ceileguce/ph-dragonfruit-dataset --unzip -p /content/dataset")

# Verify download
for root, dirs, files in os.walk("/content/dataset"):
    img_count = len([f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if img_count > 0:
        print(f"  {root}: {img_count} images")

# %% --- CELL 3: Imports ---
import json
import shutil
import time
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.applications import MobileNetV2, EfficientNetB3, ResNet50V2
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from pathlib import Path
from collections import Counter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch

# Check GPU
print("TensorFlow version:", tf.__version__)
gpus = tf.config.list_physical_devices("GPU")
print("GPU devices:", gpus)
if gpus:
    for gpu in gpus:
        tf.config.experimental.set_memory_growth(gpu, True)
    print("GPU memory growth enabled")

# %% --- CELL 4: Configuration ---
IMG_SIZE = (224, 224)
BATCH_SIZE = 32  # Colab T4 has 16GB VRAM, can handle larger batches
PHASE1_EPOCHS = 10
PHASE2_EPOCHS = 30
PATIENCE = 10
SEED = 42

DATASET_DIR = Path("/content/dataset")
RESULTS_DIR = Path("/content/training_results")
RESULTS_DIR.mkdir(exist_ok=True)

GRADE_CLASSES = ["Grade A", "Grade B", "Grade C", "Reject"]

# Dataset class mapping (PH DragonFruit Dataset)
# Ripe_frames    -> Grade A (Premium) - fully ripe, peak quality
# Ripe2_frames   -> Grade B (Standard) - secondary ripeness
# Overripe_frames -> Grade C (Economy) - past peak
# Rotten_frames  -> Reject - not suitable for sale
CLASS_MAPPING = {
    "Ripe_frames": "Grade A",
    "Ripe2_frames": "Grade B",
    "Overripe_frames": "Grade C",
    "Rotten_frames": "Reject",
}

# %% --- CELL 5: Prepare Dataset (Train/Val/Test Split 70/15/15) ---
def prepare_dataset():
    """Create train/val/test split from the downloaded dataset."""
    prepared_dir = Path("/content/dataset_prepared")

    if prepared_dir.exists() and (prepared_dir / "train").exists():
        train_count = sum(1 for _ in (prepared_dir / "train").rglob("*.*"))
        if train_count > 100:
            print(f"Dataset already prepared ({train_count} train images). Skipping.")
            return prepared_dir

    # Find the actual dataset location
    dataset_root = None
    for root, dirs, files in os.walk(DATASET_DIR):
        if any(d in CLASS_MAPPING for d in dirs):
            dataset_root = Path(root)
            break

    if dataset_root is None:
        # Try to find any directory structure
        print("Looking for dataset folders...")
        for root, dirs, files in os.walk(DATASET_DIR):
            if dirs:
                print(f"  {root}: {dirs}")
        raise FileNotFoundError("Could not find dataset class folders!")

    print(f"Dataset root: {dataset_root}")

    # Collect all images with labels
    all_images = []
    for folder_name, grade in CLASS_MAPPING.items():
        folder_path = dataset_root / folder_name
        if not folder_path.exists():
            print(f"WARNING: {folder_path} not found!")
            continue
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp"):
            for img_path in folder_path.glob(ext):
                all_images.append((str(img_path), grade))

    print(f"\nTotal images: {len(all_images)}")
    class_counts = Counter(label for _, label in all_images)
    for grade in GRADE_CLASSES:
        print(f"  {grade}: {class_counts.get(grade, 0)}")

    # Stratified split
    paths = [p for p, _ in all_images]
    labels = [l for _, l in all_images]

    train_paths, temp_paths, train_labels, temp_labels = train_test_split(
        paths, labels, test_size=0.30, stratify=labels, random_state=SEED
    )
    val_paths, test_paths, val_labels, test_labels = train_test_split(
        temp_paths, temp_labels, test_size=0.50, stratify=temp_labels, random_state=SEED
    )

    print(f"\nSplit: Train={len(train_paths)}, Val={len(val_paths)}, Test={len(test_paths)}")

    # Copy images into structured directories
    for split_name, split_paths, split_labels in [
        ("train", train_paths, train_labels),
        ("val", val_paths, val_labels),
        ("test", test_paths, test_labels),
    ]:
        for grade in GRADE_CLASSES:
            (prepared_dir / split_name / grade).mkdir(parents=True, exist_ok=True)

        for img_path, label in zip(split_paths, split_labels):
            src = Path(img_path)
            dst = prepared_dir / split_name / label / src.name
            if dst.exists():
                dst = prepared_dir / split_name / label / f"{src.stem}_{hash(img_path) % 10000}{src.suffix}"
            if not dst.exists():
                shutil.copy2(src, dst)

    print("Dataset preparation complete!")
    return prepared_dir

prepared_dir = prepare_dataset()

# %% --- CELL 6: Data Generators ---
def create_data_generators(prepared_dir):
    """Create TF data generators with augmentation (paper Section 3.3)."""
    train_datagen = keras.preprocessing.image.ImageDataGenerator(
        rescale=1.0 / 255,
        horizontal_flip=True,
        vertical_flip=True,
        rotation_range=30,
        brightness_range=[0.85, 1.15],
        width_shift_range=0.1,
        height_shift_range=0.1,
        zoom_range=0.1,
        fill_mode="nearest",
    )

    val_datagen = keras.preprocessing.image.ImageDataGenerator(rescale=1.0 / 255)

    train_gen = train_datagen.flow_from_directory(
        str(prepared_dir / "train"),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        classes=GRADE_CLASSES,
        shuffle=True,
        seed=SEED,
    )

    val_gen = val_datagen.flow_from_directory(
        str(prepared_dir / "val"),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        classes=GRADE_CLASSES,
        shuffle=False,
    )

    test_gen = val_datagen.flow_from_directory(
        str(prepared_dir / "test"),
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode="categorical",
        classes=GRADE_CLASSES,
        shuffle=False,
    )

    print(f"Train: {train_gen.samples}, Val: {val_gen.samples}, Test: {test_gen.samples}")
    print(f"Classes: {train_gen.class_indices}")
    return train_gen, val_gen, test_gen

train_gen, val_gen, test_gen = create_data_generators(prepared_dir)

# %% --- CELL 7: Model Builder ---
def build_model(model_name, num_classes=4):
    """
    Build model with pre-trained backbone + custom head.
    Head architecture from paper Section 3.5.2:
      GlobalAvgPool -> Dropout(0.3) -> Dense(128, ReLU)
      -> BatchNorm -> Dropout(0.2) -> Dense(4, Softmax)
    """
    input_shape = IMG_SIZE + (3,)

    if model_name == "MobileNetV2":
        base = MobileNetV2(weights="imagenet", include_top=False, input_shape=input_shape)
    elif model_name == "EfficientNetB3":
        base = EfficientNetB3(weights="imagenet", include_top=False, input_shape=input_shape)
    elif model_name == "ResNet50V2":
        base = ResNet50V2(weights="imagenet", include_top=False, input_shape=input_shape)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    base.trainable = False  # Freeze for Phase 1

    inputs = keras.Input(shape=input_shape)
    x = base(inputs, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(128, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.2)(x)
    outputs = layers.Dense(num_classes, activation="softmax")(x)

    model = keras.Model(inputs, outputs)

    trainable = sum(tf.keras.backend.count_params(w) for w in model.trainable_weights)
    print(f"\n{model_name}: {model.count_params():,} total params, {trainable:,} trainable")
    return model, base

# %% --- CELL 8: Training Function ---
def train_model(model_name, model, base_model, train_gen, val_gen):
    """
    Two-phase transfer learning (paper Section 3.5.3):
    Phase 1: Frozen backbone, train head only (LR=1e-3)
    Phase 2: Unfreeze all, fine-tune (LR=1e-5, early stopping)
    """
    print(f"\n{'='*70}")
    print(f"TRAINING: {model_name}")
    print(f"{'='*70}")

    history_data = {
        "model": model_name,
        "phase1_epochs": [],
        "phase2_epochs": [],
        "train_acc": [],
        "val_acc": [],
        "train_loss": [],
        "val_loss": [],
    }

    checkpoint_path = str(RESULTS_DIR / f"{model_name}_best.keras")

    # ── Phase 1: Feature Extraction ──
    print(f"\n--- Phase 1: Feature Extraction ({PHASE1_EPOCHS} epochs) ---")
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    t0 = time.time()
    h1 = model.fit(train_gen, validation_data=val_gen, epochs=PHASE1_EPOCHS, verbose=1)
    phase1_time = time.time() - t0
    print(f"Phase 1: {phase1_time:.0f}s")

    history_data["train_acc"].extend([float(x) for x in h1.history["accuracy"]])
    history_data["val_acc"].extend([float(x) for x in h1.history["val_accuracy"]])
    history_data["train_loss"].extend([float(x) for x in h1.history["loss"]])
    history_data["val_loss"].extend([float(x) for x in h1.history["val_loss"]])
    history_data["phase1_epochs"] = list(range(1, PHASE1_EPOCHS + 1))

    # ── Phase 2: Fine-tuning ──
    print(f"\n--- Phase 2: Fine-tuning ({PHASE2_EPOCHS} epochs, patience={PATIENCE}) ---")
    base_model.trainable = True

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-5),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=PATIENCE, restore_best_weights=True, verbose=1),
        ModelCheckpoint(checkpoint_path, monitor="val_accuracy", save_best_only=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5, min_lr=1e-7, verbose=1),
    ]

    t0 = time.time()
    h2 = model.fit(train_gen, validation_data=val_gen, epochs=PHASE2_EPOCHS, callbacks=callbacks, verbose=1)
    phase2_time = time.time() - t0
    actual_p2 = len(h2.history["accuracy"])
    print(f"Phase 2: {phase2_time:.0f}s ({actual_p2} epochs)")

    history_data["train_acc"].extend([float(x) for x in h2.history["accuracy"]])
    history_data["val_acc"].extend([float(x) for x in h2.history["val_accuracy"]])
    history_data["train_loss"].extend([float(x) for x in h2.history["loss"]])
    history_data["val_loss"].extend([float(x) for x in h2.history["val_loss"]])
    history_data["phase2_epochs"] = list(range(PHASE1_EPOCHS + 1, PHASE1_EPOCHS + actual_p2 + 1))
    history_data["total_epochs"] = PHASE1_EPOCHS + actual_p2
    history_data["total_time_seconds"] = phase1_time + phase2_time

    # Save history
    with open(RESULTS_DIR / f"{model_name}_history.json", "w") as f:
        json.dump(history_data, f, indent=2)

    return model, history_data

# %% --- CELL 9: Evaluation Function ---
def evaluate_model(model_name, model, test_gen):
    """Evaluate on test set, compute per-class precision/recall/F1."""
    print(f"\n--- Evaluating {model_name} ---")
    test_gen.reset()
    y_pred_probs = model.predict(test_gen, verbose=1)
    y_pred = np.argmax(y_pred_probs, axis=1)
    y_true = test_gen.classes[:len(y_pred)]

    accuracy = np.mean(y_pred == y_true)
    print(f"\n{model_name} Test Accuracy: {accuracy*100:.1f}%")

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=range(len(GRADE_CLASSES))
    )

    report = classification_report(y_true, y_pred, target_names=GRADE_CLASSES, digits=4, output_dict=True)
    print(classification_report(y_true, y_pred, target_names=GRADE_CLASSES, digits=4))

    cm = confusion_matrix(y_true, y_pred)
    print("Confusion Matrix:")
    print(cm)

    metrics = {
        "model": model_name,
        "test_accuracy": float(accuracy),
        "per_class": {},
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
    }
    for i, grade in enumerate(GRADE_CLASSES):
        metrics["per_class"][grade] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1_score": float(f1[i]),
            "support": int(support[i]),
        }

    with open(RESULTS_DIR / f"{model_name}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics

# %% --- CELL 10: TRAIN ALL 3 MODELS ---
model_names_list = ["MobileNetV2", "EfficientNetB3", "ResNet50V2"]
all_histories = {}
all_metrics = {}

for model_name in model_names_list:
    print(f"\n{'#'*70}")
    print(f"# {model_name}")
    print(f"{'#'*70}")

    # Check for existing results (resume support)
    hist_path = RESULTS_DIR / f"{model_name}_history.json"
    met_path = RESULTS_DIR / f"{model_name}_metrics.json"
    if hist_path.exists() and met_path.exists():
        print(f"{model_name} already trained. Loading results...")
        with open(hist_path) as f:
            all_histories[model_name] = json.load(f)
        with open(met_path) as f:
            all_metrics[model_name] = json.load(f)
        continue

    try:
        model, base_model = build_model(model_name)
        model, history = train_model(model_name, model, base_model, train_gen, val_gen)
        all_histories[model_name] = history
        metrics = evaluate_model(model_name, model, test_gen)
        all_metrics[model_name] = metrics

        # Free GPU memory between models
        del model, base_model
        keras.backend.clear_session()
        tf.compat.v1.reset_default_graph()

    except Exception as e:
        print(f"ERROR with {model_name}: {e}")
        import traceback
        traceback.print_exc()

# %% --- CELL 11: Generate Visualizations ---
PITAYA_PINK = "#E91E8C"
PITAYA_GREEN = "#4CAF50"
PITAYA_BLUE = "#2196F3"
BLACK = "#212121"
GRAY_DARK = "#757575"

MODEL_COLORS = {
    "MobileNetV2": PITAYA_BLUE,
    "EfficientNetB3": PITAYA_GREEN,
    "ResNet50V2": PITAYA_PINK,
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

# ── Training Curves (6-panel) ──
fig, axes = plt.subplots(2, 3, figsize=(15, 7))
fig.suptitle(
    "CNN Model Training Curves - Dragon Fruit Quality Grading (PitayaGrade)",
    fontsize=13, fontweight="bold", color=BLACK, y=1.01,
)

for col, model_name in enumerate(model_names_list):
    if model_name not in all_histories:
        continue
    h = all_histories[model_name]
    color = MODEL_COLORS[model_name]
    epochs = list(range(1, len(h["train_acc"]) + 1))
    phase1_end = len(h["phase1_epochs"])

    ax_acc = axes[0][col]
    ax_loss = axes[1][col]

    ax_acc.plot(epochs, h["train_acc"], color=color, lw=2, label="Train Accuracy")
    ax_acc.plot(epochs, h["val_acc"], color=color, lw=2, linestyle="--", alpha=0.75, label="Val Accuracy")
    ax_acc.axvline(phase1_end, color="gray", lw=1, linestyle=":", alpha=0.7)
    ax_acc.text(phase1_end + 0.5, min(h["train_acc"]) + 0.02, "Phase 2\nstart", fontsize=6.5, color="gray", va="bottom")
    ax_acc.set_xlim(1, len(epochs))
    ax_acc.set_ylim(0.3, 1.05)
    ax_acc.set_title(f"{model_name}\nModel Accuracy", fontsize=10, fontweight="bold")
    ax_acc.set_xlabel("Epochs", fontsize=8)
    ax_acc.set_ylabel("Accuracy", fontsize=8)
    ax_acc.legend(fontsize=7.5, loc="lower right")
    ax_acc.yaxis.grid(True, alpha=0.35, linestyle="--")
    ax_acc.set_facecolor("#FAFAFA")
    for spine in ["top", "right"]:
        ax_acc.spines[spine].set_visible(False)

    ax_loss.plot(epochs, h["train_loss"], color=color, lw=2, label="Train Loss")
    ax_loss.plot(epochs, h["val_loss"], color=color, lw=2, linestyle="--", alpha=0.75, label="Val Loss")
    ax_loss.axvline(phase1_end, color="gray", lw=1, linestyle=":", alpha=0.7)
    ax_loss.set_xlim(1, len(epochs))
    ax_loss.set_title("Model Loss", fontsize=10, fontweight="bold")
    ax_loss.set_xlabel("Epochs", fontsize=8)
    ax_loss.set_ylabel("Loss", fontsize=8)
    ax_loss.legend(fontsize=7.5, loc="upper right")
    ax_loss.yaxis.grid(True, alpha=0.35, linestyle="--")
    ax_loss.set_facecolor("#FAFAFA")
    for spine in ["top", "right"]:
        ax_loss.spines[spine].set_visible(False)

plt.tight_layout()
plt.savefig(str(RESULTS_DIR / "comparison_training_curves.png"), dpi=180, bbox_inches="tight", facecolor="white")
plt.show()
print("Saved: comparison_training_curves.png")

# %% --- CELL 12: Comparison Table ---
CLASSES_FLAT = ["Grade A (Premium)", "Grade B (Standard)", "Grade C (Economy)", "Reject"]

rows = []
for model_name in model_names_list:
    if model_name not in all_metrics:
        continue
    m = all_metrics[model_name]
    for grade, grade_flat in zip(GRADE_CLASSES, CLASSES_FLAT):
        pc = m["per_class"].get(grade, {})
        rows.append([
            model_name, grade_flat,
            f"{pc.get('precision', 0):.2f}",
            f"{pc.get('recall', 0):.2f}",
            f"{pc.get('f1_score', 0):.2f}",
        ])

col_labels = ["CNN Model", "Grade Class", "Precision", "Recall", "F1-Score"]
col_widths = [0.20, 0.32, 0.16, 0.14, 0.16]
n_rows = len(rows)
fig_h = 0.42 * n_rows + 1.6
fig, ax = plt.subplots(figsize=(9, fig_h))
ax.axis("off")

fig.text(0.5, 0.97, "Table 1. Comparative Analysis - Dragon Fruit Quality Grading Models",
         ha="center", va="top", fontsize=12, fontweight="bold", color=BLACK)

y_start = 0.88
row_h = (y_start - 0.06) / (n_rows + 1)
x_start = 0.04

def cell(ax, x, y, w, h, text, bold=False, bg=None, text_color=BLACK):
    if bg:
        rect = FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0",
                              linewidth=0.5, edgecolor="#BDBDBD", facecolor=bg,
                              transform=ax.transAxes, clip_on=False)
        ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=9.5, fontweight="bold" if bold else "normal",
            color=text_color, transform=ax.transAxes, clip_on=False)

# Header
x = x_start
for lbl, w in zip(col_labels, col_widths):
    cell(ax, x, y_start, w, row_h, lbl, bold=True, bg="#333333", text_color="white")
    x += w

# Data rows
model_bg = {"MobileNetV2": "#E3F2FD", "EfficientNetB3": "#E8F5E9", "ResNet50V2": "#FCE4EC"}
model_row_start = {}
prev = None
for ri, row in enumerate(rows):
    if row[0] != prev:
        model_row_start[row[0]] = ri
        prev = row[0]

for ri, row in enumerate(rows):
    model = row[0]
    bg = model_bg.get(model, "#F5F5F5")
    y = y_start - (ri + 1) * row_h

    x = x_start
    for ci, (val, w) in enumerate(zip(row, col_widths)):
        if ci == 0:
            if ri == model_row_start.get(model):
                rect = FancyBboxPatch((x, y - 3 * row_h), w, 4 * row_h,
                                     boxstyle="square,pad=0", linewidth=0.5,
                                     edgecolor="#BDBDBD", facecolor=bg,
                                     transform=ax.transAxes, clip_on=False)
                ax.add_patch(rect)
                ax.text(x + w / 2, y - 3 * row_h / 2 + row_h / 2, model,
                        ha="center", va="center", fontsize=9.5, fontweight="bold",
                        color=BLACK, transform=ax.transAxes, clip_on=False)
            x += w
            continue

        is_best = False
        if ci == 4:
            cls_idx = ri % 4
            f1_vals = []
            for mn in model_names_list:
                if mn in all_metrics:
                    g = GRADE_CLASSES[cls_idx]
                    f1_vals.append(all_metrics[mn]["per_class"].get(g, {}).get("f1_score", 0))
            if f1_vals and float(val) >= max(f1_vals) - 0.001:
                is_best = True

        cell_bg = "#C8E6C9" if is_best else bg
        cell(ax, x, y, w, row_h, val, bold=is_best, bg=cell_bg)
        x += w

ax.text(0.5, 0.01, "Green highlight = best F1-Score per class",
        ha="center", va="bottom", fontsize=7.5, color=GRAY_DARK, style="italic",
        transform=ax.transAxes)

plt.tight_layout(rect=[0, 0.02, 1, 0.96])
plt.savefig(str(RESULTS_DIR / "comparison_table.png"), dpi=180, bbox_inches="tight", facecolor="white")
plt.show()
print("Saved: comparison_table.png")

# %% --- CELL 13: Combined Figure ---
fig = plt.figure(figsize=(16, 18), facecolor="white")
gs = GridSpec(2, 1, figure=fig, height_ratios=[1.1, 1], hspace=0.22)

ax_table = fig.add_subplot(gs[0])
ax_table.axis("off")
fig.text(0.5, 0.975,
         "Table 1. Comparative Analysis - Dragon Fruit Quality Grading CNN Models\n(Real Training Results)",
         ha="center", va="top", fontsize=13, fontweight="bold", color=BLACK)

cell_text = [r[1:] for r in rows]
row_labels = [r[0] for r in rows]
col_labels_short = col_labels[1:]

model_colors_tbl = {"MobileNetV2": "#E3F2FD", "EfficientNetB3": "#E8F5E9", "ResNet50V2": "#FCE4EC"}
cell_colors = []
for ri, row in enumerate(rows):
    base_c = model_colors_tbl.get(row[0], "#F5F5F5")
    row_c = [base_c] * 4
    cls_idx = ri % 4
    f1_vals = []
    for mn in model_names_list:
        if mn in all_metrics:
            g = GRADE_CLASSES[cls_idx]
            f1_vals.append(all_metrics[mn]["per_class"].get(g, {}).get("f1_score", 0))
    if f1_vals and float(row[4]) >= max(f1_vals) - 0.001:
        row_c[3] = "#C8E6C9"
    cell_colors.append(row_c)

tbl = ax_table.table(
    cellText=cell_text, rowLabels=row_labels, colLabels=col_labels_short,
    cellColours=cell_colors,
    rowColours=[model_colors_tbl.get(r[0], "#F5F5F5") for r in rows],
    loc="center", cellLoc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9.5)
tbl.scale(1, 1.55)

for j in range(len(col_labels_short)):
    c = tbl[(0, j)]
    c.set_facecolor("#333333")
    c.set_text_props(color="white", fontweight="bold")
for i in range(len(rows)):
    c = tbl[(i + 1, -1)]
    c.set_text_props(fontweight="bold")

# Bottom: Training Curves
gs_curves = gs[1].subgridspec(2, 3, hspace=0.42, wspace=0.35)
fig.text(0.5, 0.485, "Training Curves - Accuracy & Loss per Model",
         ha="center", va="top", fontsize=12, fontweight="bold", color=BLACK)

for col_idx, model_name in enumerate(model_names_list):
    if model_name not in all_histories:
        continue
    h = all_histories[model_name]
    color = MODEL_COLORS[model_name]
    epochs = list(range(1, len(h["train_acc"]) + 1))
    phase1_end = len(h["phase1_epochs"])

    ax_a = fig.add_subplot(gs_curves[0, col_idx])
    ax_l = fig.add_subplot(gs_curves[1, col_idx])

    for ax, y1, y2, ylabel, title_suffix in [
        (ax_a, h["train_acc"], h["val_acc"], "Accuracy", "Model Accuracy"),
        (ax_l, h["train_loss"], h["val_loss"], "Loss", "Model Loss"),
    ]:
        ax.plot(epochs, y1, color=color, lw=2, label="Train " + ylabel)
        ax.plot(epochs, y2, color=color, lw=2, linestyle="--", alpha=0.75, label="Val " + ylabel)
        ax.axvline(phase1_end, color="gray", lw=0.9, linestyle=":", alpha=0.65)
        ax.text(phase1_end + 0.5, ax.get_ylim()[0] if ylabel == "Loss" else min(y1),
                "Ph.2", fontsize=6, color="#9E9E9E", va="bottom")
        ax.set_xlim(1, len(epochs))
        ax.set_xlabel("Epochs", fontsize=7.5)
        ax.set_ylabel(ylabel, fontsize=7.5)
        ax.legend(fontsize=6.5, loc="lower right" if ylabel == "Accuracy" else "upper right")
        ax.yaxis.grid(True, alpha=0.3, linestyle="--")
        ax.set_facecolor("#FAFAFA")
        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.tick_params(labelsize=7)
        if ax == ax_a:
            ax.set_title(f"{model_name}\n{title_suffix}", fontsize=9, fontweight="bold")
        else:
            ax.set_title(title_suffix, fontsize=9, fontweight="bold")

plt.savefig(str(RESULTS_DIR / "comparison_combined.png"), dpi=180, bbox_inches="tight", facecolor="white")
plt.show()
print("Saved: comparison_combined.png")

# %% --- CELL 14: Print Final Summary ---
print("\n" + "=" * 70)
print("FINAL RESULTS SUMMARY")
print("=" * 70)

for model_name in model_names_list:
    if model_name in all_metrics:
        m = all_metrics[model_name]
        h = all_histories.get(model_name, {})
        print(f"\n{model_name}:")
        print(f"  Test Accuracy: {m['test_accuracy']*100:.1f}%")
        print(f"  Training Time: {h.get('total_time_seconds', 0):.0f}s")
        print(f"  Total Epochs:  {h.get('total_epochs', 'N/A')}")
        for grade in GRADE_CLASSES:
            pc = m["per_class"].get(grade, {})
            print(f"  {grade:10s} -> P={pc.get('precision',0):.3f}  R={pc.get('recall',0):.3f}  F1={pc.get('f1_score',0):.3f}")

# %% --- CELL 15: Download Results ---
# Zip all results for download
import zipfile

zip_path = "/content/pitayagrade_training_results.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for f in RESULTS_DIR.iterdir():
        zf.write(f, f.name)

print(f"\nResults zipped to: {zip_path}")
print("Download it using the file browser on the left, or run:")
print("  from google.colab import files; files.download('/content/pitayagrade_training_results.zip')")

# Auto-download
try:
    from google.colab import files
    files.download(zip_path)
except ImportError:
    print("(Not running in Colab - skip auto-download)")
