"""
PitayaGrade - Real CNN Model Training & Comparison
Trains manuscript EfficientNet-B3 only from a validated review manifest.

Uses PyTorch with CUDA GPU acceleration.
Follows methodology from the capstone paper:
- 224x224 input, two-phase transfer learning, data augmentation,
- 70/15/15 split, Adam optimizer, early stopping
"""

import os
import json
import time
from importlib.metadata import version
from scripts.reviewed_training import training_arguments, prepare_reviewed_dataset
from scripts.training_policy import LossMonitor
from scripts.image_orientation import load_upright_rgb

# Validate before importing ML frameworks or downloading weights.
TRAINING_ARGS = training_arguments() if __name__ == "__main__" else None

import numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support

# ── Configuration ────────────────────────────────────────────────────────────
IMG_SIZE = 224
BATCH_SIZE = 32
PHASE1_EPOCHS = 10
PHASE2_EPOCHS = 30
PATIENCE = 10
SEED = 42
NUM_WORKERS = 2

PROJECT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = PROJECT_DIR / "training_results"

GRADE_CLASSES = ["Grade A", "Grade B", "Grade C", "Reject"]

torch.manual_seed(SEED)
np.random.seed(SEED)

# ── Device ───────────────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")


# ── Dataset Preparation ─────────────────────────────────────────────────────
def prepare_dataset():
    """Use reviewed labels and partitions; reject legacy folder mappings."""
    if TRAINING_ARGS is None:
        raise ValueError("A reviewed manifest and new run directory are required")
    return prepare_reviewed_dataset(TRAINING_ARGS.rows, TRAINING_ARGS.run_dir)


# ── Data Loaders ─────────────────────────────────────────────────────────────
def create_dataloaders(prepared_dir):
    """Create PyTorch dataloaders with augmentation."""
    # ImageNet normalization
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

    train_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(30),
        transforms.ColorJitter(brightness=0.15, contrast=0.1),
        transforms.ToTensor(),
        normalize,
    ])

    val_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        normalize,
    ])

    train_dataset = datasets.ImageFolder(str(prepared_dir / "train"), transform=train_transform, loader=load_upright_rgb)
    val_dataset = datasets.ImageFolder(str(prepared_dir / "val"), transform=val_transform, loader=load_upright_rgb)
    test_dataset = datasets.ImageFolder(str(prepared_dir / "test"), transform=val_transform, loader=load_upright_rgb)

    # Ensure class order matches GRADE_CLASSES
    print(f"Class to idx: {train_dataset.class_to_idx}")

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=NUM_WORKERS, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=NUM_WORKERS, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False,
                             num_workers=NUM_WORKERS, pin_memory=True)

    print(f"Train: {len(train_dataset)}, Val: {len(val_dataset)}, Test: {len(test_dataset)}")
    return train_loader, val_loader, test_loader, train_dataset.class_to_idx


# ── Model Builder ────────────────────────────────────────────────────────────
def build_model(model_name, num_classes=4):
    """
    Build model with ImageNet backbone + custom head (paper Section 3.5.2):
    GlobalAvgPool -> Dropout(0.3) -> Dense(128, ReLU) -> BN -> Dropout(0.2) -> Dense(4, Softmax)
    """
    if model_name == "MobileNetV2":
        base = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
        in_features = base.classifier[1].in_features
        base.classifier = nn.Identity()

    elif model_name == "EfficientNetB3":
        base = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
        in_features = base.classifier[1].in_features
        base.classifier = nn.Identity()

    elif model_name == "ResNet50V2":
        # PyTorch ResNet50 with V2 weights (best available pre-training)
        base = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
        in_features = base.fc.in_features
        base.fc = nn.Identity()

    else:
        raise ValueError(f"Unknown model: {model_name}")

    # Custom classification head matching paper spec
    head = nn.Sequential(
        nn.Dropout(0.3),
        nn.Linear(in_features, 128),
        nn.ReLU(),
        nn.BatchNorm1d(128),
        nn.Dropout(0.2),
        nn.Linear(128, num_classes),
    )

    class FullModel(nn.Module):
        def __init__(self, backbone, classifier):
            super().__init__()
            self.backbone = backbone
            self.classifier = classifier

        def forward(self, x):
            features = self.backbone(x)
            if features.dim() > 2:
                features = nn.functional.adaptive_avg_pool2d(features, 1).flatten(1)
            return self.classifier(features)

    model = FullModel(base, head)

    total_params = sum(p.numel() for p in model.parameters())
    print(f"\n{model_name}: {total_params:,} total params")

    return model


def freeze_backbone(model):
    """Freeze backbone for Phase 1."""
    for param in model.backbone.parameters():
        param.requires_grad = False


def unfreeze_backbone(model):
    """Fine-tune the upper three EfficientNet feature blocks, retaining lower features."""
    freeze_backbone(model)
    for block in list(model.backbone.features.children())[-3:]:
        for param in block.parameters():
            param.requires_grad = True


# ── Training Loop ────────────────────────────────────────────────────────────
def train_one_epoch(model, loader, criterion, optimizer):
    model.train()
    # Frozen parameters must also preserve BatchNorm running statistics.
    if not any(p.requires_grad for p in model.backbone.parameters()):
        model.backbone.eval()
    else:
        for module in model.backbone.modules():
            if isinstance(module, nn.modules.batchnorm._BatchNorm) and not any(p.requires_grad for p in module.parameters()):
                module.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * inputs.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

    return running_loss / total, correct / total


def validate(model, loader, criterion):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * inputs.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    return running_loss / total, correct / total


def train_model(model_name, model, train_loader, val_loader):
    """Two-phase transfer learning; selection and stopping use validation loss."""
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    history = dict(model=model_name, phase1_epochs=[], phase2_epochs=[],
                   train_acc=[], val_acc=[], train_loss=[], val_loss=[], learning_rate=[],
                   selection_metric="val_loss", fine_tuning="upper three feature blocks")
    overall = LossMonitor(PATIENCE)
    best_state = None
    started = time.time()
    for phase, epochs, lr in ((1, PHASE1_EPOCHS, 1e-3), (2, PHASE2_EPOCHS, 1e-5)):
        if phase == 1:
            freeze_backbone(model)
        else:
            model.load_state_dict(best_state)
            unfreeze_backbone(model)
        optimizer = optim.Adam(filter(lambda p: p.requires_grad, model.parameters()),
                               lr=lr, weight_decay=1e-4)
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5, threshold=0, min_lr=1e-7)
        phase_monitor = LossMonitor(PATIENCE)
        for _ in range(epochs):
            current_lr = optimizer.param_groups[0]['lr']
            train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer)
            val_loss, val_acc = validate(model, val_loader, criterion)
            epoch = len(history['val_loss']) + 1
            phase_monitor.update(val_loss, epoch)
            if overall.update(val_loss, epoch):
                best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
                history['best_val_accuracy'] = val_acc
            scheduler.step(val_loss)
            for key, value in (('train_loss', train_loss), ('train_acc', train_acc),
                               ('val_loss', val_loss), ('val_acc', val_acc),
                               ('learning_rate', current_lr)):
                history[key].append(value)
            history[f'phase{phase}_epochs'].append(epoch)
            print(f'Phase {phase} epoch {epoch}: val_loss={val_loss:.4f}, val_acc={val_acc:.4f}, lr={current_lr:.1e}')
            if phase_monitor.should_stop:
                break
    if best_state is None:
        raise RuntimeError('No finite validation-loss checkpoint was produced')
    model.load_state_dict(best_state)
    history.update(best_val_loss=overall.best, best_epoch=overall.best_epoch,
                   total_epochs=len(history['val_loss']), total_time_seconds=time.time() - started)
    with open(RESULTS_DIR / f"{model_name}_history.json", "w") as output:
        json.dump(history, output, indent=2)
    torch.save(model.state_dict(), str(RESULTS_DIR / f"{model_name}_best.pth"))
    return model, history


# ── Evaluation ───────────────────────────────────────────────────────────────
def evaluate_model(model_name, model, test_loader, class_to_idx):
    """Evaluate on test set with per-class metrics."""
    print(f"\n--- Evaluating {model_name} ---")
    model.eval()

    all_preds = []
    all_labels = []

    with torch.no_grad():
        for inputs, labels in test_loader:
            inputs = inputs.to(device)
            outputs = model(inputs)
            _, predicted = outputs.max(1)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.numpy())

    y_pred = np.array(all_preds)
    y_true = np.array(all_labels)

    # Map idx back to class names
    idx_to_class = {v: k for k, v in class_to_idx.items()}
    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]

    accuracy = np.mean(y_pred == y_true)
    print(f"{model_name} Test Accuracy: {accuracy*100:.1f}%")

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, average=None, labels=range(len(class_names))
    )

    print(classification_report(y_true, y_pred, target_names=class_names, digits=4))

    cm = confusion_matrix(y_true, y_pred)
    print("Confusion Matrix:")
    print(cm)

    metrics = {
        "model": model_name,
        "test_accuracy": float(accuracy),
        "per_class": {},
        "confusion_matrix": cm.tolist(),
        "class_names": class_names,
    }
    for i, grade in enumerate(class_names):
        metrics["per_class"][grade] = {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1_score": float(f1[i]),
            "support": int(support[i]),
        }

    with open(RESULTS_DIR / f"{model_name}_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


# ── Visualization ────────────────────────────────────────────────────────────
def generate_visualizations(all_histories, all_metrics, model_names):
    """Generate real training curves and comparison table."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import FancyBboxPatch

    COLORS = {"MobileNetV2": "#2196F3", "EfficientNetB3": "#4CAF50", "ResNet50V2": "#E91E8C"}
    BLACK = "#212121"

    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.facecolor": "white", "axes.facecolor": "white"})

    # ── 6-panel training curves ──
    print("\nGenerating training curves...")
    fig, axes = plt.subplots(2, len(model_names), figsize=(5 * len(model_names), 7), squeeze=False)
    fig.suptitle("CNN Model Training Curves - Dragon Fruit Quality Grading (PitayaGrade)",
                 fontsize=13, fontweight="bold", y=1.01)

    for col, name in enumerate(model_names):
        if name not in all_histories:
            continue
        h = all_histories[name]
        color = COLORS[name]
        epochs = list(range(1, len(h["train_acc"]) + 1))
        p1_end = len(h["phase1_epochs"])

        for row, (y_train, y_val, ylabel, title) in enumerate([
            (h["train_acc"], h["val_acc"], "Accuracy", "Model Accuracy"),
            (h["train_loss"], h["val_loss"], "Loss", "Model Loss"),
        ]):
            ax = axes[row][col]
            ax.plot(epochs, y_train, color=color, lw=2, label=f"Train {ylabel}")
            ax.plot(epochs, y_val, color=color, lw=2, ls="--", alpha=0.75, label=f"Val {ylabel}")
            ax.axvline(p1_end, color="gray", lw=1, ls=":", alpha=0.7)
            if row == 0:
                ax.text(p1_end + 0.5, min(y_train) + 0.02, "Phase 2\nstart", fontsize=6.5, color="gray", va="bottom")
                ax.set_ylim(0.3, 1.05)
                ax.set_title(f"{name}\n{title}", fontsize=10, fontweight="bold")
            else:
                ax.set_title(title, fontsize=10, fontweight="bold")
            ax.set_xlim(1, len(epochs))
            ax.set_xlabel("Epochs", fontsize=8)
            ax.set_ylabel(ylabel, fontsize=8)
            ax.legend(fontsize=7.5, loc="lower right" if row == 0 else "upper right")
            ax.yaxis.grid(True, alpha=0.35, ls="--")
            ax.set_facecolor("#FAFAFA")
            for s in ["top", "right"]:
                ax.spines[s].set_visible(False)

    plt.tight_layout()
    plt.savefig(str(RESULTS_DIR / "comparison_training_curves.png"), dpi=180, bbox_inches="tight")
    plt.close()
    print("  Saved: comparison_training_curves.png")

    # ── Comparison Table ──
    print("Generating comparison table...")
    class_names = list(all_metrics[model_names[0]]["per_class"].keys()) if all_metrics else GRADE_CLASSES
    FLAT = {"Grade A": "Grade A (Premium)", "Grade B": "Grade B (Standard)",
            "Grade C": "Grade C (Economy)", "Reject": "Reject"}

    rows = []
    for name in model_names:
        if name not in all_metrics:
            continue
        m = all_metrics[name]
        for grade in class_names:
            pc = m["per_class"].get(grade, {})
            rows.append([name, FLAT.get(grade, grade),
                         f"{pc.get('precision',0):.2f}", f"{pc.get('recall',0):.2f}", f"{pc.get('f1_score',0):.2f}"])

    if not rows:
        print("  No data for table.")
        return

    col_labels = ["CNN Model", "Grade Class", "Precision", "Recall", "F1-Score"]
    col_w = [0.20, 0.32, 0.16, 0.14, 0.16]
    n = len(rows)

    fig, ax = plt.subplots(figsize=(9, 0.42 * n + 1.6))
    ax.axis("off")
    fig.text(0.5, 0.97, "Table 1. Comparative Analysis - Dragon Fruit Quality Grading Models",
             ha="center", va="top", fontsize=12, fontweight="bold")

    y_s = 0.88
    rh = (y_s - 0.06) / (n + 1)
    xs = 0.04

    mbg = {"MobileNetV2": "#E3F2FD", "EfficientNetB3": "#E8F5E9", "ResNet50V2": "#FCE4EC"}

    def cell(x, y, w, h, text, bold=False, bg=None, tc=BLACK):
        if bg:
            ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="square,pad=0", lw=0.5,
                                        ec="#BDBDBD", fc=bg, transform=ax.transAxes, clip_on=False))
        ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=9.5,
                fontweight="bold" if bold else "normal", color=tc, transform=ax.transAxes, clip_on=False)

    x = xs
    for lbl, w in zip(col_labels, col_w):
        cell(x, y_s, w, rh, lbl, bold=True, bg="#333333", tc="white")
        x += w

    ms = {}
    prev = None
    for ri, r in enumerate(rows):
        if r[0] != prev:
            ms[r[0]] = ri
            prev = r[0]

    n_classes = len(class_names)
    for ri, r in enumerate(rows):
        mdl = r[0]
        bg = mbg.get(mdl, "#F5F5F5")
        y = y_s - (ri + 1) * rh
        x = xs
        for ci, (v, w) in enumerate(zip(r, col_w)):
            if ci == 0:
                if ri == ms.get(mdl):
                    ax.add_patch(FancyBboxPatch((x, y - (n_classes-1)*rh), w, n_classes*rh,
                                                boxstyle="square,pad=0", lw=0.5, ec="#BDBDBD", fc=bg,
                                                transform=ax.transAxes, clip_on=False))
                    ax.text(x + w/2, y - (n_classes-1)*rh/2 + rh/2, mdl, ha="center", va="center",
                            fontsize=9.5, fontweight="bold", color=BLACK, transform=ax.transAxes, clip_on=False)
                x += w
                continue
            best = False
            if ci == 4:
                idx = ri % n_classes
                gn = class_names[idx]
                f1s = [all_metrics[mn]["per_class"].get(gn, {}).get("f1_score", 0)
                       for mn in model_names if mn in all_metrics]
                if f1s and float(v) >= max(f1s) - 0.001:
                    best = True
            cell(x, y, w, rh, v, bold=best, bg="#C8E6C9" if best else bg)
            x += w

    ax.text(0.5, 0.01, "Green highlight = best F1-Score per class", ha="center", va="bottom",
            fontsize=7.5, color="#757575", style="italic", transform=ax.transAxes)

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.savefig(str(RESULTS_DIR / "comparison_table.png"), dpi=180, bbox_inches="tight")
    plt.close()
    print("  Saved: comparison_table.png")

    # ── Combined figure ──
    print("Generating combined figure...")
    fig = plt.figure(figsize=(16, 18), facecolor="white")
    gs = GridSpec(2, 1, figure=fig, height_ratios=[1.1, 1], hspace=0.22)

    ax_t = fig.add_subplot(gs[0])
    ax_t.axis("off")
    fig.text(0.5, 0.975, "Table 1. Comparative Analysis - Dragon Fruit Quality Grading CNN Models\n(Real Training Results)",
             ha="center", va="top", fontsize=13, fontweight="bold")

    cell_text = [r[1:] for r in rows]
    row_labels = [r[0] for r in rows]
    cell_colors = []
    for ri, r in enumerate(rows):
        bc = mbg.get(r[0], "#F5F5F5")
        rc = [bc] * 4
        idx = ri % n_classes
        gn = class_names[idx]
        f1s = [all_metrics[mn]["per_class"].get(gn, {}).get("f1_score", 0) for mn in model_names if mn in all_metrics]
        if f1s and float(r[4]) >= max(f1s) - 0.001:
            rc[3] = "#C8E6C9"
        cell_colors.append(rc)

    tbl = ax_t.table(cellText=cell_text, rowLabels=row_labels, colLabels=col_labels[1:],
                     cellColours=cell_colors, rowColours=[mbg.get(r[0], "#F5F5F5") for r in rows],
                     loc="center", cellLoc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9.5)
    tbl.scale(1, 1.55)
    for j in range(4):
        tbl[(0, j)].set_facecolor("#333333")
        tbl[(0, j)].set_text_props(color="white", fontweight="bold")
    for i in range(len(rows)):
        tbl[(i+1, -1)].set_text_props(fontweight="bold")

    gs_c = gs[1].subgridspec(2, len(model_names), hspace=0.42, wspace=0.35)
    fig.text(0.5, 0.485, "Training Curves - Accuracy & Loss per Model",
             ha="center", va="top", fontsize=12, fontweight="bold")

    for ci, name in enumerate(model_names):
        if name not in all_histories:
            continue
        h = all_histories[name]
        color = COLORS[name]
        ep = list(range(1, len(h["train_acc"]) + 1))
        p1 = len(h["phase1_epochs"])

        ax_a = fig.add_subplot(gs_c[0, ci])
        ax_l = fig.add_subplot(gs_c[1, ci])
        for ax, y1, y2, yl, ts in [(ax_a, h["train_acc"], h["val_acc"], "Accuracy", "Model Accuracy"),
                                    (ax_l, h["train_loss"], h["val_loss"], "Loss", "Model Loss")]:
            ax.plot(ep, y1, color=color, lw=2, label=f"Train {yl}")
            ax.plot(ep, y2, color=color, lw=2, ls="--", alpha=0.75, label=f"Val {yl}")
            ax.axvline(p1, color="gray", lw=0.9, ls=":", alpha=0.65)
            ax.set_xlim(1, len(ep))
            ax.set_xlabel("Epochs", fontsize=7.5)
            ax.set_ylabel(yl, fontsize=7.5)
            ax.legend(fontsize=6.5, loc="lower right" if yl == "Accuracy" else "upper right")
            ax.yaxis.grid(True, alpha=0.3, ls="--")
            ax.set_facecolor("#FAFAFA")
            for s in ["top", "right"]:
                ax.spines[s].set_visible(False)
            ax.tick_params(labelsize=7)
            ax.set_title(f"{name}\n{ts}" if ax == ax_a else ts, fontsize=9, fontweight="bold")

    plt.savefig(str(RESULTS_DIR / "comparison_combined.png"), dpi=180, bbox_inches="tight")
    plt.close()
    print("  Saved: comparison_combined.png")

    # ── Summary ──
    print(f"\n{'='*70}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*70}")
    for name in model_names:
        if name in all_metrics:
            m = all_metrics[name]
            h = all_histories.get(name, {})
            print(f"\n{name}:")
            print(f"  Test Accuracy: {m['test_accuracy']*100:.1f}%")
            print(f"  Training Time: {h.get('total_time_seconds', 0):.0f}s")
            for grade in class_names:
                pc = m["per_class"].get(grade, {})
                print(f"  {grade:10s} -> P={pc.get('precision',0):.3f}  R={pc.get('recall',0):.3f}  F1={pc.get('f1_score',0):.3f}")


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    global RESULTS_DIR
    RESULTS_DIR = TRAINING_ARGS.run_dir
    print("=" * 70)
    print("PitayaGrade - Real CNN Model Training")
    print("EfficientNet-B3 | reviewed manuscript quality labels")
    print("=" * 70)

    # Prepare dataset
    prepared_dir = prepare_dataset()
    train_loader, val_loader, test_loader, class_to_idx = create_dataloaders(prepared_dir)

    (RESULTS_DIR / 'training-context.json').write_text(json.dumps({
        'task': 'manuscript-quality', 'model': 'EfficientNetB3',
        'frameworks': {name: version(name) for name in ('torch', 'torchvision', 'scikit-learn')},
        'classToIndex': class_to_idx, 'imageSize': IMG_SIZE, 'batchSize': BATCH_SIZE, 'seed': SEED,
        'orientation': 'EXIF-transpose to upright RGB before resize and augmentation',
        'phase1': {'epochs': PHASE1_EPOCHS, 'lr': 1e-3, 'backbone': 'frozen'},
        'phase2': {'epochs': PHASE2_EPOCHS, 'lr': 1e-5, 'backbone': 'upper three feature blocks'},
        'optimizer': {'name': 'Adam', 'weightDecay': 1e-4, 'betas': [0.9, 0.999]},
        'scheduler': {'name': 'ReduceLROnPlateau', 'patience': 5, 'factor': 0.5},
        'selectionMetric': 'val_loss', 'earlyStoppingPatience': PATIENCE,
        'methodologyLimitations': ['Reviewed fruit-crop provenance and full preprocessing alignment still need verification.',
                                  'No metadata check establishes expert-label truth or field accuracy.']
    }, indent=2) + '\n', encoding='utf-8')

    model_names = ["EfficientNetB3"]
    all_histories = {}
    all_metrics = {}

    for model_name in model_names:
        print(f"\n{'#'*70}")
        print(f"# {model_name}")
        print(f"{'#'*70}")

        try:
            model = build_model(model_name)
            model, history = train_model(model_name, model, train_loader, val_loader)
            all_histories[model_name] = history

            metrics = evaluate_model(model_name, model, test_loader, class_to_idx)
            all_metrics[model_name] = metrics

            # Free GPU memory
            del model
            torch.cuda.empty_cache()

        except Exception as e:
            print(f"ERROR with {model_name}: {e}")
            import traceback
            traceback.print_exc()
            raise

    # Generate all visualizations
    if all_histories and all_metrics:
        generate_visualizations(all_histories, all_metrics, model_names)

    print(f"\n{'='*70}")
    print("ALL DONE! Results in:", RESULTS_DIR)
    print("=" * 70)


if __name__ == "__main__":
    main()
