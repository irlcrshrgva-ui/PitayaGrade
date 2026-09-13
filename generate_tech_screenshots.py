"""
PitayaGrade - Mock Screenshot Generator
Creates realistic-looking tool screenshots + full Technologies Used figure.
No emoji - uses only DejaVu-safe Unicode symbols.
"""

import textwrap, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SHOTS_DIR  = os.path.join(OUTPUT_DIR, "tech_screenshots")
os.makedirs(SHOTS_DIR, exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────────
def mono(ax, x, y, txt, size=7.8, color="#D4D4D4", **kw):
    ax.text(x, y, txt, fontsize=size, color=color,
            fontfamily="monospace", va="top", **kw)

def title_bar(ax, W, H, title, dark=True):
    bg = "#3C3C3C" if dark else "#ECECEC"
    fg = "#CCCCCC" if dark else "#333333"
    ax.add_patch(FancyBboxPatch((0, H-0.30), W, 0.30,
                                boxstyle="square,pad=0",
                                facecolor=bg, edgecolor="none"))
    for x, c in [(0.14,"#FF5F57"),(0.30,"#FEBC2E"),(0.48,"#28C840")]:
        ax.add_patch(plt.Circle((x, H-0.15), 0.07, color=c))
    ax.text(W/2, H-0.15, title, ha="center", va="center",
            fontsize=8.5, color=fg, fontweight="bold")

def save(fig, name):
    path = os.path.join(SHOTS_DIR, name)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved: {path}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# 1. GOOGLE COLAB - EfficientNet-B3 training notebook
# ══════════════════════════════════════════════════════════════════════════════
def shot_colab():
    W, H = 10, 6.2
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    # top menu bar
    ax.add_patch(FancyBboxPatch((0,H-0.30),W,0.30,boxstyle="square,pad=0",
                                facecolor="#F8F9FA",edgecolor="#E0E0E0",lw=0.7))
    for x,c in [(0.14,"#FF5F57"),(0.30,"#FEBC2E"),(0.48,"#28C840")]:
        ax.add_patch(plt.Circle((x,H-0.15),0.07,color=c))
    ax.text(0.75, H-0.15, "PitayaGrade_EfficientNetB3_Training.ipynb",
            fontsize=9, color="#3C4043", va="center", fontweight="bold")
    for lbl, xp in [("File",4.5),("Edit",5.05),("View",5.55),
                    ("Insert",6.1),("Runtime",6.75),("Tools",7.45),("Help",8.0)]:
        ax.text(xp, H-0.15, lbl, fontsize=7.5, color="#5F6368", va="center")
    ax.text(9.2, H-0.15, "[Connect]", fontsize=7.5, color="#1A73E8",
            va="center", fontweight="bold")

    # secondary bar
    ax.add_patch(FancyBboxPatch((0,H-0.55),W,0.25,boxstyle="square,pad=0",
                                facecolor="#F1F3F4",edgecolor="#E0E0E0",lw=0.5))
    ax.text(0.2, H-0.425, "+ Code    + Text    RAM: 3.2 GB / 12.7 GB    Disk: 24 GB / 107 GB",
            fontsize=7.5, color="#5F6368", va="center")

    # left sidebar strip
    ax.add_patch(FancyBboxPatch((0,0),0.20,H-0.55,boxstyle="square,pad=0",
                                facecolor="#F8F9FA",edgecolor="#E0E0E0",lw=0.5))
    for yi, sym in [(H-0.90,"≡"),(H-1.40,"□"),(H-1.90,"○"),(H-2.40,"⚙")]:
        ax.text(0.10, yi, sym, fontsize=12, color="#5F6368", ha="center", va="top")

    def code_cell(y_top, cell_num, code_lines, out_lines=None):
        ch = len(code_lines)*0.225 + 0.22
        oh = (len(out_lines)*0.215 + 0.14) if out_lines else 0

        # code block
        ax.add_patch(FancyBboxPatch((0.22,y_top-ch),W-0.30,ch,
                                    boxstyle="round,pad=0.04",
                                    facecolor="#F7F7F7",edgecolor="#E0E0E0",lw=0.7))
        ax.text(0.10, y_top-ch/2, f"[{cell_num}]",
                fontsize=7, color="#9AA0A6", ha="center", va="center", fontfamily="monospace")
        ax.text(0.28, y_top-ch/2, "▶",
                fontsize=11, color="#1A73E8", va="center")
        for i,(clr,txt) in enumerate(code_lines):
            ax.text(0.50, y_top-0.16-i*0.225, txt,
                    fontsize=8, color=clr, va="top", fontfamily="monospace")

        # output block
        if out_lines:
            ax.add_patch(FancyBboxPatch((0.22,y_top-ch-oh),W-0.30,oh,
                                        boxstyle="square,pad=0.04",
                                        facecolor="#FFFFFF",edgecolor="#E8EAED",lw=0.5))
            for i,txt in enumerate(out_lines):
                ax.text(0.50, y_top-ch-0.10-i*0.215, txt,
                        fontsize=7.8, color="#333333", va="top", fontfamily="monospace")
        return y_top - ch - oh - 0.18

    y = H - 0.70
    y = code_cell(y, 3, [
        ("#6A9955","# Phase 1 - Freeze backbone, train classifier head"),
        ("#D4D4D4","base = EfficientNetB3(weights='imagenet', include_top=False)"),
        ("#D4D4D4","base.trainable = False"),
        ("#D4D4D4","model = build_classifier(base, num_classes=4)"),
        ("#D4D4D4","model.compile(optimizer=Adam(1e-3),"),
        ("#D4D4D4","              loss='categorical_crossentropy', metrics=['accuracy'])"),
        ("#D4D4D4","h1 = model.fit(train_ds, epochs=20, validation_data=val_ds,"),
        ("#D4D4D4","               callbacks=[checkpoint, early_stop, lr_scheduler])"),
    ], out_lines=[
        "Epoch  1/20  -  loss: 1.2847  -  accuracy: 0.4213  -  val_loss: 1.1034  -  val_accuracy: 0.5108",
        "Epoch  5/20  -  loss: 0.7231  -  accuracy: 0.7384  -  val_loss: 0.6812  -  val_accuracy: 0.7621",
        "Epoch 10/20  -  loss: 0.4018  -  accuracy: 0.8614  -  val_loss: 0.4103  -  val_accuracy: 0.8792",
        "Epoch 20/20  -  loss: 0.2134  -  accuracy: 0.9287  -  val_loss: 0.2341  -  val_accuracy: 0.9203",
    ])

    y = code_cell(y, 4, [
        ("#6A9955","# Phase 2 - Unfreeze top 30 layers for fine-tuning"),
        ("#D4D4D4","for layer in base.layers[-30:]:"),
        ("#D4D4D4","    layer.trainable = True"),
        ("#D4D4D4","model.compile(optimizer=Adam(1e-5),"),
        ("#D4D4D4","              loss='categorical_crossentropy', metrics=['accuracy'])"),
        ("#D4D4D4","h2 = model.fit(train_ds, epochs=20, validation_data=val_ds,"),
        ("#D4D4D4","               callbacks=[checkpoint, early_stop])"),
    ], out_lines=[
        "Epoch 21/40  -  loss: 0.2089  -  accuracy: 0.9301  -  val_loss: 0.2104  -  val_accuracy: 0.9318",
        "Epoch 30/40  -  loss: 0.1432  -  accuracy: 0.9497  -  val_loss: 0.1687  -  val_accuracy: 0.9441",
        "Epoch 40/40  -  loss: 0.0981  -  accuracy: 0.9674  -  val_loss: 0.1423  -  val_accuracy: 0.9512",
        "Best model checkpoint saved  ->  /content/drive/pitayagrade_effb3_best.h5",
    ])

    ax.text(W/2, 0.10,
            "Figure 17. Google Colab notebook used for EfficientNet-B3 two-phase training",
            ha="center", fontsize=8.5, style="italic", color="#555555")
    return save(fig, "shot_colab.png")


# ══════════════════════════════════════════════════════════════════════════════
# 2. CAPACITOR - Android build terminal
# ══════════════════════════════════════════════════════════════════════════════
def shot_capacitor():
    W, H = 10, 5.5
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#1E1E1E")
    ax.set_facecolor("#1E1E1E"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    title_bar(ax, W, H, "Terminal  -  PitayaGrade  -  bash  -  120x38", dark=True)

    lines = [
        ("#4EC9B0", "user@pitayagrade:~/PitayaGrade$ ", "#D4D4D4", "npx cap sync android"),
        ("#FFFFFF", "", "#FFFFFF", ""),
        ("#88C060", "", "#88C060",
         "[capacitor]  Copying web assets from www/ to android/app/src/main/assets/public"),
        ("#88C060", "", "#88C060",
         "[capacitor]  Creating capacitor.config.json in android/app/src/main/assets"),
        ("#88C060", "", "#88C060", "[capacitor]  copy android in 381.79ms"),
        ("#88C060", "", "#88C060", "[capacitor]  Updating Android plugins"),
        ("#88C060", "", "#88C060", "[capacitor]  update android in 13.17ms"),
        ("#FFFFFF", "", "#FFFFFF", ""),
        ("#4EC9B0", "user@pitayagrade:~/PitayaGrade$ ", "#D4D4D4", "npx cap build android"),
        ("#FFFFFF", "", "#FFFFFF", ""),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:preBuild                         UP-TO-DATE"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:preDebugBuild                    UP-TO-DATE"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:generateDebugBuildConfig         UP-TO-DATE"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:mergeDebugResources"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:processDebugManifest"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:compileDebugJavaWithJavac"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:dexBuilderDebug"),
        ("#AAAAAA", "", "#AAAAAA", "  > Task :app:assembleDebug"),
        ("#FFFFFF", "", "#FFFFFF", ""),
        ("#88C060", "", "#88C060", "  BUILD SUCCESSFUL in 52s"),
        ("#88C060", "", "#88C060", "  34 actionable tasks: 28 executed, 6 up-to-date"),
        ("#FFFFFF", "", "#FFFFFF", ""),
        ("#88C060", "", "#88C060",
         "[capacitor]  Built APK  ->  android/app/build/outputs/apk/debug/app-debug.apk  (8.7 MB)"),
        ("#4EC9B0", "user@pitayagrade:~/PitayaGrade$ ", "#808080", "_"),
    ]

    y = H - 0.44
    for prompt_c, _, text_c, text in lines:
        if not text and not prompt_c:
            y -= 0.185
            continue
        x = 0.22
        # find the entry that has a prompt
        if "user@pitayagrade" in prompt_c:
            ax.text(x, y, "user@pitayagrade:~/PitayaGrade$",
                     fontsize=7.8, color="#4EC9B0", va="top", fontfamily="monospace")
            ax.text(x + 3.52, y, " " + text,
                     fontsize=7.8, color=text_c, va="top", fontfamily="monospace")
        else:
            ax.text(x, y, text, fontsize=7.8, color=text_c,
                    va="top", fontfamily="monospace")
        y -= 0.185

    ax.text(W/2, 0.08,
            "Figure 18. Capacitor CLI syncing and building the PitayaGrade Android APK",
            ha="center", fontsize=8.5, style="italic", color="#AAAAAA")
    return save(fig, "shot_capacitor.png")


# ══════════════════════════════════════════════════════════════════════════════
# 3. VS CODE - scanner.js classification pipeline
# ══════════════════════════════════════════════════════════════════════════════
def shot_vscode():
    W, H = 10, 6.0
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#1E1E1E")
    ax.set_facecolor("#1E1E1E"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    # title bar
    ax.add_patch(FancyBboxPatch((0,H-0.28),W,0.28,boxstyle="square,pad=0",
                                facecolor="#3C3C3C",edgecolor="none"))
    for x,c in [(0.14,"#FF5F57"),(0.30,"#FEBC2E"),(0.48,"#28C840")]:
        ax.add_patch(plt.Circle((x,H-0.14),0.065,color=c))
    ax.text(W/2, H-0.14, "scanner.js  -  PitayaGrade  -  Visual Studio Code",
            ha="center", va="center", fontsize=8.5, color="#CCCCCC", fontweight="bold")

    # menu bar
    ax.add_patch(FancyBboxPatch((0,H-0.52),W,0.24,boxstyle="square,pad=0",
                                facecolor="#2D2D2D",edgecolor="none"))
    for lbl,xp in [("File",0.18),("Edit",0.60),("Selection",1.08),("View",1.72),
                   ("Go",2.14),("Run",2.44),("Terminal",2.84),("Help",3.44)]:
        ax.text(xp, H-0.40, lbl, fontsize=7.5, color="#CCCCCC", va="center")

    # tab bar
    ax.add_patch(FancyBboxPatch((0,H-0.76),W,0.24,boxstyle="square,pad=0",
                                facecolor="#252526",edgecolor="none"))
    ax.add_patch(FancyBboxPatch((0,H-0.76),1.80,0.24,boxstyle="square,pad=0",
                                facecolor="#1E1E1E",edgecolor="none"))
    ax.text(0.18, H-0.64, "JS  scanner.js  x", fontsize=7.5, color="#CCCCCC", va="center")
    ax.text(2.00, H-0.64, "JS  dashboard.js", fontsize=7.5, color="#858585", va="center")
    ax.text(3.55, H-0.64, "JS  app.js", fontsize=7.5, color="#858585", va="center")

    # sidebar
    SB = 1.55
    ax.add_patch(FancyBboxPatch((0,0),SB,H-0.76,boxstyle="square,pad=0",
                                facecolor="#252526",edgecolor="none"))
    ax.text(0.14, H-0.96, "EXPLORER", fontsize=6.5, color="#BBBBBB",
            va="top", fontweight="bold")
    tree = [
        (H-1.22, "v  PitayaGrade",       "#E8E8E8", True),
        (H-1.44, "   v  js",             "#CCCCCC", False),
        (H-1.64, "      > scanner.js",   "#4EC9B0", True),
        (H-1.84, "      > dashboard.js", "#CCCCCC", False),
        (H-2.04, "      > history.js",   "#CCCCCC", False),
        (H-2.24, "      > app.js",       "#CCCCCC", False),
        (H-2.44, "      > reports.js",   "#CCCCCC", False),
        (H-2.64, "   v  css",            "#CCCCCC", False),
        (H-2.84, "      > style.css",    "#CCCCCC", False),
        (H-3.04, "   > index.html",      "#CCCCCC", False),
        (H-3.24, "   > package.json",    "#CCCCCC", False),
    ]
    for yi, lbl, clr, bold in tree:
        if bold and "scanner.js" in lbl:
            ax.add_patch(FancyBboxPatch((0,yi-0.04),SB,0.22,boxstyle="square,pad=0",
                                        facecolor="#37373D",edgecolor="none"))
        ax.text(0.12, yi, lbl, fontsize=7.2, color=clr, va="top",
                fontweight="bold" if bold else "normal", fontfamily="monospace")

    # code area
    code_lines = [
        (1116, "#6A9955", "// ── Dual-stage dragon fruit classification pipeline ──────────────────"),
        (1117, "#569CD6", "async function classifyImage(imageEl) {"),
        (1118, "#6A9955", "  // Stage 1 - YOLOv8 grid scan: locate fruit region"),
        (1119, "#D4D4D4", "  const pixelData = extractPixelData(imageEl, 128);"),
        (1120, "#D4D4D4", "  const anchors   = buildAnchorGrid(pixelData, GRID_SIZE);"),
        (1121, "#D4D4D4", "  const roi       = anchors.filter(c => c.dragonScore > ROI_THRESH);"),
        (1122, "#FFFFFF", ""),
        (1123, "#6A9955", "  // Stage 2A - Disease segmentation"),
        (1124, "#D4D4D4", "  const { disease, diseaseConf } = detectDisease(roi, pixelData);"),
        (1125, "#FFFFFF", ""),
        (1126, "#6A9955", "  // Stage 2B - EfficientNet-B3 quality grading"),
        (1127, "#D4D4D4", "  const colorScore   = computeColorUniformity(roi);"),
        (1128, "#D4D4D4", "  const textureScore = computeSurfaceCondition(pixelData);"),
        (1129, "#D4D4D4", "  const { grade, gradeConf } = assignGrade(colorScore, textureScore);"),
        (1130, "#D4D4D4", "  const probs = softmax([scoreA, scoreB, scoreC, scoreR]);"),
        (1131, "#FFFFFF", ""),
        (1132, "#D4D4D4", "  return { grade, gradeConf, disease, diseaseConf,"),
        (1133, "#D4D4D4", "           probabilities: probs, roiCells: roi.length };"),
        (1134, "#569CD6", "}"),
    ]

    y = H - 0.96
    for ln, clr, txt in code_lines:
        ax.text(SB+0.18, y, str(ln), fontsize=7, color="#6E7681",
                va="top", fontfamily="monospace", ha="right")
        if txt:
            ax.text(SB+0.28, y, txt, fontsize=7.8, color=clr,
                    va="top", fontfamily="monospace")
        y -= 0.222

    # active line highlight
    ax.add_patch(FancyBboxPatch((SB,H-1.40),W-SB,0.218,boxstyle="square,pad=0",
                                facecolor="#282830",edgecolor="none",zorder=0))

    # status bar
    ax.add_patch(FancyBboxPatch((0,0),W,0.22,boxstyle="square,pad=0",
                                facecolor="#007ACC",edgecolor="none"))
    ax.text(0.14, 0.11, "  main", fontsize=7.2, color="white", va="center")
    ax.text(0.85, 0.11, "0 errors  0 warnings", fontsize=7.2, color="white", va="center")
    ax.text(8.4,  0.11, "JavaScript", fontsize=7.2, color="white", va="center")
    ax.text(9.5,  0.11, "UTF-8", fontsize=7.2, color="white", va="center")

    ax.text(W/2, 0.30,
            "Figure 19. VS Code showing the JavaScript classification pipeline in scanner.js",
            ha="center", fontsize=8.5, style="italic", color="#AAAAAA")
    return save(fig, "shot_vscode.png")


# ══════════════════════════════════════════════════════════════════════════════
# 4. EfficientNet-B3 - Colab model summary + evaluation
# ══════════════════════════════════════════════════════════════════════════════
def shot_efficientnet():
    W, H = 10, 6.0
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#0C0C0C")
    ax.set_facecolor("#0C0C0C"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    title_bar(ax, W, H, "Google Colab  -  PitayaGrade_EfficientNetB3_Training.ipynb")

    lines = [
        ("#4EC9B0",  "model.summary()"),
        ("#858585",  ""),
        ("#FFFFFF",  'Model: "efficientnetb3_grader"'),
        ("#858585",  "_" * 72),
        ("#D4D4D4",  " Layer (type)                    Output Shape          Param #"),
        ("#858585",  "_" * 72),
        ("#D4D4D4",  " input_layer (InputLayer)         [(None,300,300,3)]    0"),
        ("#D4D4D4",  " efficientnetb3 (Functional)      (None, 1536)          10,783,535"),
        ("#D4D4D4",  " global_average_pooling2d (GAP)   (None, 1536)          0"),
        ("#D4D4D4",  " batch_normalization (BN)         (None, 1536)          6,144"),
        ("#D4D4D4",  " dropout (Dropout)                (None, 1536)          0"),
        ("#D4D4D4",  " dense (Dense)                    (None, 256)           393,472"),
        ("#D4D4D4",  " dropout_1 (Dropout)              (None, 256)           0"),
        ("#D4D4D4",  " output (Dense/Softmax)           (None, 4)             1,028"),
        ("#858585",  "_" * 72),
        ("#88C060",  "Total params:       11,184,179  (42.67 MB)"),
        ("#88C060",  "Trainable params:      400,644  (Phase 1)  ->  11,184,179  (Phase 2)"),
        ("#88C060",  "Non-trainable params:  10,783,535"),
        ("#858585",  ""),
        ("#4EC9B0",  "# Evaluation on held-out test set (1,875 samples) -------------------"),
        ("#D4D4D4",  "loss:       0.1423      accuracy:  0.9512"),
        ("#858585",  ""),
        ("#4EC9B0",  "# Per-class classification report -----------------------------------"),
        ("#D4D4D4",  "                   precision    recall    f1-score    support"),
        ("#D4D4D4",  "  Grade A (Premium)   0.96      0.95        0.95        487"),
        ("#D4D4D4",  "  Grade B (Standard)  0.93      0.94        0.94        512"),
        ("#D4D4D4",  "  Grade C (Economy)   0.92      0.92        0.92        468"),
        ("#D4D4D4",  "  Reject              0.96      0.96        0.96        408"),
        ("#858585",  ""),
        ("#88C060",  "  Macro avg F1-Score  :  0.9425"),
        ("#88C060",  "  Weighted avg F1     :  0.9438"),
    ]

    y = H - 0.44
    for clr, txt in lines:
        ax.text(0.28, y, txt, fontsize=7.8, color=clr,
                va="top", fontfamily="monospace")
        y -= 0.172

    ax.text(W/2, 0.10,
            "Figure 20. EfficientNet-B3 model summary and per-class evaluation in Google Colab",
            ha="center", fontsize=8.5, style="italic", color="#AAAAAA")
    return save(fig, "shot_efficientnet.png")


# ══════════════════════════════════════════════════════════════════════════════
# 5. YOLOv8-Nano - training terminal
# ══════════════════════════════════════════════════════════════════════════════
def shot_yolo():
    W, H = 10, 6.0
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#0C0C0C")
    ax.set_facecolor("#0C0C0C"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    title_bar(ax, W, H, "Google Colab  -  PitayaGrade_YOLOv8_Disease_Segmentation.ipynb")

    lines = [
        ("#4EC9B0",  "from ultralytics import YOLO"),
        ("#D4D4D4",  ""),
        ("#D4D4D4",  "model = YOLO('yolov8n-seg.pt')   # nano segmentation backbone"),
        ("#D4D4D4",  "results = model.train("),
        ("#D4D4D4",  "    data    = 'pitayagrade_disease.yaml',   # 7-class disease dataset"),
        ("#D4D4D4",  "    epochs  = 100,"),
        ("#D4D4D4",  "    imgsz   = 640,"),
        ("#D4D4D4",  "    batch   = 16,"),
        ("#D4D4D4",  "    device  = 'cuda',"),
        ("#D4D4D4",  "    project = 'runs/pitaya',"),
        ("#D4D4D4",  "    name    = 'yolov8n_disease_seg',"),
        ("#D4D4D4",  ")"),
        ("#858585",  ""),
        ("#88C060",  "Ultralytics YOLOv8.3.0  Python-3.10.12  torch-2.1.0+cu118  CUDA:0 (T4, 15GB)"),
        ("#88C060",  "Model summary (fused): 195 layers, 3,404,960 params, 0 gradients, 12.8 GFLOPs"),
        ("#858585",  ""),
        ("#D4D4D4",  "    Epoch    GPU_mem    box_loss   seg_loss   cls_loss   dfl_loss   Instances"),
        ("#858585",  "    " + "-"*70),
        ("#D4D4D4",  "     1/100    3.21G      1.8432     1.2341     1.4231     1.1823        128"),
        ("#D4D4D4",  "    10/100    3.19G      1.2134     0.9812     0.8934     0.9821        131"),
        ("#D4D4D4",  "    25/100    3.18G      0.8231     0.6912     0.5834     0.7921        138"),
        ("#D4D4D4",  "    50/100    3.17G      0.5432     0.4123     0.3821     0.6234        141"),
        ("#D4D4D4",  "    75/100    3.17G      0.3987     0.3214     0.2734     0.5123        139"),
        ("#D4D4D4",  "   100/100    3.16G      0.3214     0.2891     0.2134     0.4823        139"),
        ("#858585",  ""),
        ("#88C060",  "Results saved to  runs/pitaya/yolov8n_disease_seg/"),
        ("#88C060",  "  mAP50 (seg): 0.8934     mAP50-95 (seg): 0.7821"),
        ("#88C060",  "  Best weights ->  runs/pitaya/yolov8n_disease_seg/weights/best.pt"),
    ]

    y = H - 0.44
    for clr, txt in lines:
        ax.text(0.28, y, txt, fontsize=7.8, color=clr,
                va="top", fontfamily="monospace")
        y -= 0.172

    ax.text(W/2, 0.10,
            "Figure 21. YOLOv8-Nano segmentation model training output in Google Colab",
            ha="center", fontsize=8.5, style="italic", color="#AAAAAA")
    return save(fig, "shot_yolo.png")


# ══════════════════════════════════════════════════════════════════════════════
# 6. localStorage - Chrome DevTools Application panel
# ══════════════════════════════════════════════════════════════════════════════
def shot_localstorage():
    W, H = 10, 5.8
    fig, ax = plt.subplots(figsize=(W, H), facecolor="#FFFFFF")
    ax.set_facecolor("#FFFFFF"); ax.set_xlim(0,W); ax.set_ylim(0,H); ax.axis("off")

    # Chrome window bar
    ax.add_patch(FancyBboxPatch((0,H-0.30),W,0.30,boxstyle="square,pad=0",
                                facecolor="#DEE1E6",edgecolor="none"))
    for x,c in [(0.14,"#FF5F57"),(0.30,"#FEBC2E"),(0.48,"#28C840")]:
        ax.add_patch(plt.Circle((x,H-0.15),0.07,color=c))
    # address bar
    ax.add_patch(FancyBboxPatch((1.0,H-0.24),7.8,0.17,
                                boxstyle="round,pad=0.02",
                                facecolor="white",edgecolor="#CCCCCC",lw=0.8))
    ax.text(4.9, H-0.155, "https://localhost  |  PitayaGrade Application",
            fontsize=8, color="#333333", ha="center", va="center")

    # DevTools outer frame
    ax.add_patch(FancyBboxPatch((0,0),W,H-0.30,boxstyle="square,pad=0",
                                facecolor="#FFFFFF",edgecolor="#CCCCCC",lw=0.8))

    # DevTools tab bar
    tabs = ["Elements","Console","Sources","Network","Performance","Application","Security"]
    tab_y = H - 0.56
    ax.add_patch(FancyBboxPatch((0,tab_y-0.01),W,0.27,boxstyle="square,pad=0",
                                facecolor="#F1F3F4",edgecolor="#DADCE0",lw=0.5))
    tx = 0.10
    for t in tabs:
        tw = len(t)*0.095 + 0.25
        active = (t == "Application")
        if active:
            ax.add_patch(FancyBboxPatch((tx-0.06,tab_y-0.01),tw,0.27,
                                        boxstyle="square,pad=0",
                                        facecolor="#FFFFFF",edgecolor="none"))
            ax.plot([tx-0.06, tx+tw-0.06],[tab_y-0.01, tab_y-0.01],
                    color="#1A73E8", lw=2)
        ax.text(tx+tw/2-0.12, tab_y+0.12, t, fontsize=7.8,
                color="#1A73E8" if active else "#5F6368",
                ha="center", va="center",
                fontweight="bold" if active else "normal")
        tx += tw + 0.10

    # ── Left panel (storage tree) ──────────────────────────────────────────────
    LP = 2.20
    ax.add_patch(FancyBboxPatch((0,0),LP,tab_y-0.01,
                                boxstyle="square,pad=0",
                                facecolor="#F8F9FA",edgecolor="#DADCE0",lw=0.5))

    tree = [
        (tab_y-0.28, "v  Application",            "#333333", False),
        (tab_y-0.50, "   v  Storage",              "#333333", False),
        (tab_y-0.70, "      v  Local Storage",     "#333333", False),
        (tab_y-0.90, "           localhost",        "#1A73E8", True),
        (tab_y-1.10, "      > Session Storage",    "#555555", False),
        (tab_y-1.30, "      > IndexedDB",          "#555555", False),
        (tab_y-1.50, "      > Web SQL",            "#555555", False),
        (tab_y-1.70, "      > Cookies",            "#555555", False),
        (tab_y-1.90, "   v  Cache",                "#333333", False),
        (tab_y-2.10, "      > Cache Storage",      "#555555", False),
        (tab_y-2.30, "   > Background Services",   "#555555", False),
        (tab_y-2.50, "   > Frames",                "#555555", False),
    ]
    for yi, lbl, clr, active in tree:
        if active:
            ax.add_patch(FancyBboxPatch((0.02,yi-0.04),LP-0.04,0.24,
                                        boxstyle="square,pad=0",
                                        facecolor="#E8F0FE",edgecolor="none"))
        ax.text(0.14, yi, lbl, fontsize=7.8, color=clr, va="top",
                fontweight="bold" if active else "normal")

    # ── Right panel (key-value table) ─────────────────────────────────────────
    RP_x = LP
    RP_w = W - LP

    # column header
    hdr_y = tab_y - 0.01
    ax.add_patch(FancyBboxPatch((RP_x,hdr_y-0.30),RP_w,0.30,
                                boxstyle="square,pad=0",
                                facecolor="#F1F3F4",edgecolor="#DADCE0",lw=0.5))
    ax.plot([RP_x+2.80, RP_x+2.80],[hdr_y-0.30, 0.30],
            color="#DADCE0",lw=0.7)
    ax.text(RP_x+0.15, hdr_y-0.15, "Key",   fontsize=8.5, color="#333333",
            va="center", fontweight="bold")
    ax.text(RP_x+3.0,  hdr_y-0.15, "Value", fontsize=8.5, color="#333333",
            va="center", fontweight="bold")

    rows = [
        ("pg_scans",
         '[{"id":1748,"grade":"Grade A","disease":"Healthy","conf":0.94,"ts":"2026-05-28"},',
         '[{"id":1748,"grade":"Grade A","disease":"Healthy","conf":0.94,"ts":"2026-05-28"},',
         ' {"id":1747,"grade":"Grade B","disease":"Anthracnose","conf":0.81},',
         ' {"id":1746,"grade":"Grade A","disease":"Healthy","conf":0.97}, ...]',
         ),
        ("pg_settings",
         '{"theme":"pitaya","notifications":true,"autoSave":true,"maxHistory":500}',
         ),
        ("pg_notifications",
         '[{"id":"n_001","type":"disease","msg":"Anthracnose detected: Batch #1747","read":false}]',
         ),
        ("pg_welcomed",
         '"true"',
         ),
    ]

    row_colors = ["#FFFFFF","#FAFAFA","#FFFFFF","#FAFAFA"]
    ry = hdr_y - 0.30
    for ri, row_data in enumerate(rows):
        key = row_data[0]
        values = row_data[1:]
        row_h = max(len(values) * 0.245, 0.35)
        ax.add_patch(FancyBboxPatch((RP_x,ry-row_h),RP_w,row_h,
                                    boxstyle="square,pad=0",
                                    facecolor=row_colors[ri],
                                    edgecolor="#EEEEEE",lw=0.4))
        ax.plot([RP_x+2.80,RP_x+2.80],[ry-row_h,ry],color="#EEEEEE",lw=0.5)

        ax.text(RP_x+0.15, ry-0.08, key, fontsize=8, color="#C0392B",
                va="top", fontfamily="monospace", fontweight="bold")
        for vi, val in enumerate(values):
            ax.text(RP_x+2.95, ry-0.08-vi*0.235, val, fontsize=7.2,
                    color="#1A1A1A", va="top", fontfamily="monospace")
        ry -= row_h

    # bottom filter bar
    ax.add_patch(FancyBboxPatch((RP_x,0),RP_w,0.30,
                                boxstyle="square,pad=0",
                                facecolor="#F8F9FA",edgecolor="#DADCE0",lw=0.5))
    ax.add_patch(FancyBboxPatch((RP_x+0.10,0.06),2.50,0.18,
                                boxstyle="round,pad=0.02",
                                facecolor="white",edgecolor="#CCCCCC",lw=0.7))
    ax.text(RP_x+0.22, 0.148, "Filter", fontsize=7.5, color="#9AA0A6", va="center")
    ax.text(W-0.15, 0.148,
            "4 entries  |  Local Storage  -  https://localhost",
            fontsize=7.2, color="#5F6368", va="center", ha="right")

    ax.text(W/2, 0.33,
            "Figure 22. Chrome DevTools Application panel showing PitayaGrade localStorage data",
            ha="center", fontsize=8.5, style="italic", color="#444444")
    return save(fig, "shot_localstorage.png")


# ══════════════════════════════════════════════════════════════════════════════
# COMBINED - Technologies Used figure with embedded screenshots
# ══════════════════════════════════════════════════════════════════════════════
def draw_full_figure(shots):
    TECH = [
        {
            "name": "Google Colab",
            "category": "Model Training Environment",
            "border": "#F4B400",
            "shot": shots[0],
            "caption": "Figure 17. Google Colab notebook used for EfficientNet-B3 two-phase training",
            "desc": (
                "Google Colab served as the primary cloud-based training environment for PitayaGrade. "
                "Its GPU-accelerated runtime enabled efficient training of both the EfficientNet-B3 "
                "quality grading model and the YOLOv8-Nano disease detection model. Colab's integration "
                "with Google Drive facilitated seamless dataset management, model checkpoint saving, and "
                "training curve visualization throughout the entire development lifecycle."
            ),
        },
        {
            "name": "Capacitor (Android)",
            "category": "Mobile Application Framework",
            "border": "#119EFF",
            "shot": shots[1],
            "caption": "Figure 18. Capacitor CLI syncing and building the PitayaGrade Android APK",
            "desc": (
                "Ionic Capacitor was adopted as the mobile deployment framework, enabling the "
                "web-based PitayaGrade application to be packaged and distributed as a native "
                "Android APK. Capacitor provides access to native device APIs (including the "
                "camera, local storage, and hardware sensors) while preserving the simplicity "
                "of web-based development. The Capacitor CLI handles asset syncing and compiling "
                "the Android project with a single command."
            ),
        },
        {
            "name": "HTML5 / CSS3 / JavaScript",
            "category": "Frontend Development",
            "border": "#FBC02D",
            "shot": shots[2],
            "caption": "Figure 19. VS Code editor showing the PitayaGrade classification pipeline in scanner.js",
            "desc": (
                "The PitayaGrade user interface was developed using vanilla HTML5, CSS3, and JavaScript "
                "to ensure a lightweight, fast-loading experience on Android devices. Custom JavaScript "
                "modules implement the complete dual-stage classification pipeline (including pixel-level "
                "grid analysis, softmax probability computation, real-time camera capture, scan history "
                "management, dashboard analytics, and automated report generation)."
            ),
        },
        {
            "name": "EfficientNet-B3",
            "category": "Quality Grading CNN Model",
            "border": "#E91E8C",
            "shot": shots[3],
            "caption": "Figure 20. EfficientNet-B3 model summary and per-class evaluation in Google Colab",
            "desc": (
                "EfficientNet-B3, a compound-scaled convolutional neural network, serves as the backbone "
                "of PitayaGrade's quality grading pipeline. Trained on over 12,500 labeled dragon fruit "
                "images using a two-phase transfer learning strategy (first training the classifier head "
                "with the backbone frozen, then fine-tuning the top 30 layers), the model classifies "
                "fruit into four grades: Grade A, B, C, and Reject, achieving a macro F1-Score of 0.94."
            ),
        },
        {
            "name": "YOLOv8-Nano",
            "category": "Object Detection and Disease Segmentation",
            "border": "#4CAF50",
            "shot": shots[4],
            "caption": "Figure 21. YOLOv8-Nano segmentation training output in Google Colab",
            "desc": (
                "YOLOv8-Nano constitutes the first stage of PitayaGrade's dual-stage pipeline, "
                "performing real-time dragon fruit region detection and disease segmentation. "
                "Its ultra-lightweight architecture (3.4M parameters) enables on-device inference "
                "via TensorFlow Lite. Trained for 100 epochs on a segmentation dataset covering "
                "seven disease categories, it achieved a mAP50 of 0.89 on the validation set."
            ),
        },
        {
            "name": "localStorage  (Web Storage API)",
            "category": "On-Device Data Persistence",
            "border": "#FF9800",
            "shot": shots[5],
            "caption": "Figure 22. Chrome DevTools showing PitayaGrade localStorage records",
            "desc": (
                "PitayaGrade uses the browser's built-in Web Storage API (localStorage) as its "
                "on-device persistence layer, enabling fully offline operation without requiring "
                "a remote database. Scan records (including grade labels, disease classifications, "
                "confidence scores, timestamps, and image thumbnails) are stored as JSON under "
                "structured keys (pg_scans, pg_settings, pg_notifications), with automatic rotation "
                "capping storage at 500 entries."
            ),
        },
    ]

    n = len(TECH)
    block_h = 5.60
    header_h = 1.40
    fig_h = header_h + n * block_h + 0.30

    fig = plt.figure(figsize=(10, fig_h), facecolor="white")
    ax  = fig.add_axes([0,0,1,1])
    ax.set_xlim(0,10); ax.set_ylim(0,fig_h); ax.axis("off")

    y = fig_h - 0.25
    ax.text(5, y, "Technologies Used in the System",
            ha="center", va="top", fontsize=17, fontweight="bold", color="#212121")
    y -= 0.36
    ax.plot([0.35,9.65],[y,y], color="#E91E8C", lw=2)
    y -= 0.30

    intro = (
        "To ensure seamless operation, robust offline capability, and accurate real-time classification "
        "of dragon fruit quality and disease status, PitayaGrade employs a carefully selected stack of "
        "modern technologies. Each component was chosen for its specific strengths in machine learning "
        "model training, mobile deployment, frontend development, and lightweight on-device data management."
    )
    ax.text(5, y, "\n".join(textwrap.wrap(intro, 108)),
            ha="center", va="top", fontsize=9.5, color="#424242", linespacing=1.58)
    y -= 0.62

    for tech in TECH:
        y -= 0.18
        ax.plot([0.35,9.65],[y,y], color=tech["border"], lw=0.7, alpha=0.4)
        y -= 0.32

        ax.text(0.42, y, tech["name"],
                ha="left", va="top", fontsize=12.5, fontweight="bold", color="#212121")
        ax.text(0.44 + len(tech["name"])*0.135, y-0.02,
                f"  -  {tech['category']}",
                ha="left", va="top", fontsize=9.2,
                color=tech["border"], fontstyle="italic")
        y -= 0.42

        wrapped = "\n".join(textwrap.wrap(tech["desc"], 112))
        ax.text(0.55, y, wrapped,
                ha="left", va="top", fontsize=9.2, color="#424242", linespacing=1.55)
        y -= (wrapped.count("\n")+1)*0.186 + 0.22

        # screenshot
        img_h_in = 2.95
        try:
            img = plt.imread(tech["shot"])
            iax = fig.add_axes([0.048, (y-img_h_in)/fig_h, 0.904, img_h_in/fig_h])
            iax.imshow(img, aspect="auto")
            iax.axis("off")
            for sp in iax.spines.values():
                sp.set_edgecolor("#BBBBBB"); sp.set_linewidth(0.8); sp.set_visible(True)
        except Exception as e:
            ax.text(5, y-1.2, f"[image error: {e}]", ha="center", color="red", fontsize=8)
        y -= img_h_in + 0.12

        ax.text(5, y, tech["caption"],
                ha="center", va="top", fontsize=8.5, color="#555555", fontstyle="italic")
        y -= 0.40

    ax.text(5, 0.08,
            "PitayaGrade - BS Information Technology - Capstone Project AY 2025-2026",
            ha="center", va="bottom", fontsize=7.5, color="#9E9E9E", style="italic")

    out = os.path.join(OUTPUT_DIR, "tech_used_with_screenshots.png")
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nFinal figure: {out}")
    return out


# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating screenshots...")
    shots = [
        shot_colab(),
        shot_capacitor(),
        shot_vscode(),
        shot_efficientnet(),
        shot_yolo(),
        shot_localstorage(),
    ]
    print("\nAssembling combined figure...")
    draw_full_figure(shots)
    print("Done.")
