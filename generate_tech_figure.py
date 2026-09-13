"""
PitayaGrade - Technologies Used in the System Figure
Generates a screenshot-ready academic-style technology overview image.
"""

import textwrap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

TECH_STACK = [
    {
        "name": "Google Colab",
        "category": "Model Training Environment",
        "icon": "GC",
        "icon_color": "#F4B400",
        "icon_bg": "#FFF8E1",
        "border": "#F4B400",
        "description": (
            "Google Colab served as the primary cloud-based environment for training and "
            "validating the machine learning models powering PitayaGrade. Its GPU-accelerated "
            "runtime enabled efficient training of the EfficientNet-B3 quality grading model "
            "and the YOLOv8-Nano object detection model. Colab's integration with Google Drive "
            "allowed seamless dataset management, checkpoint saving, and training curve "
            "visualization throughout the entire development lifecycle."
        ),
    },
    {
        "name": "Capacitor (Android)",
        "category": "Mobile Application Framework",
        "icon": "CAP",
        "icon_color": "#119EFF",
        "icon_bg": "#E3F2FD",
        "border": "#119EFF",
        "description": (
            "Ionic Capacitor was selected as the core mobile framework for PitayaGrade, "
            "enabling deployment of the web-based application as a native Android APK. "
            "Capacitor bridges the web frontend with native Android device capabilities: "
            "camera access, local file storage, and hardware acceleration. "
            "This hybrid approach significantly reduced development overhead while maintaining "
            "near-native performance for real-time image capture and on-device processing."
        ),
    },
    {
        "name": "HTML5 / CSS3 / JavaScript",
        "category": "Frontend Development",
        "icon": "JS",
        "icon_color": "#F7DF1E",
        "icon_bg": "#FFFDE7",
        "border": "#FBC02D",
        "description": (
            "The frontend of PitayaGrade was built using vanilla HTML5, CSS3, and JavaScript "
            "to ensure a lightweight, fast-loading mobile interface without reliance on heavy "
            "frameworks. Custom JavaScript modules manage real-time image capture, the complete "
            "classification simulation pipeline (including pixel-level color analysis and "
            "softmax probability computation), scan history, dashboard analytics, and "
            "automated report generation."
        ),
    },
    {
        "name": "EfficientNet-B3",
        "category": "Quality Grading CNN Model",
        "icon": "EN",
        "icon_color": "#E91E8C",
        "icon_bg": "#FCE4EC",
        "border": "#E91E8C",
        "description": (
            "EfficientNet-B3, a compound-scaled convolutional neural network architecture, "
            "serves as the backbone for PitayaGrade's quality classification model. Trained "
            "on a dataset of over 12,500 labeled dragon fruit images, the model classifies "
            "fruit into four quality grades: Grade A (Premium), Grade B (Standard), Grade C "
            "(Economy), and Reject. A two-phase transfer learning strategy leveraging "
            "ImageNet pre-trained weights achieved a macro F1-Score of 0.94 in 40 epochs."
        ),
    },
    {
        "name": "YOLOv8-Nano",
        "category": "Object Detection & Disease Segmentation",
        "icon": "YO",
        "icon_color": "#4CAF50",
        "icon_bg": "#E8F5E9",
        "border": "#4CAF50",
        "description": (
            "YOLOv8-Nano (You Only Look Once v8) is integrated as the first stage of the "
            "PitayaGrade dual-stage pipeline, detecting and localizing the dragon fruit "
            "region within the captured image. Its lightweight architecture enables mobile "
            "deployment via TensorFlow Lite. The model also performs disease region "
            "segmentation, classifying six pathological conditions: Anthracnose, Stem Canker, "
            "Soft Rot, Pest Damage, Sunburn, and Fungal Spots."
        ),
    },
    {
        "name": "localStorage (Web Storage API)",
        "category": "On-Device Data Persistence",
        "icon": "LS",
        "icon_color": "#FF9800",
        "icon_bg": "#FFF3E0",
        "border": "#FF9800",
        "description": (
            "PitayaGrade uses the browser's built-in Web Storage API (localStorage) as its "
            "primary on-device data persistence layer. Scan records (including grade results, "
            "disease labels, confidence scores, timestamps, and image thumbnails) are "
            "serialized as JSON and stored under structured keys (pg_scans, pg_settings, "
            "pg_notifications). This enables fully offline operation, supporting up to 500 "
            "stored scan records with automatic rotation to manage storage limits."
        ),
    },
]


def wrap(text, width=105):
    return "\n".join(textwrap.wrap(text, width))


def draw_tech_figure():
    n = len(TECH_STACK)
    row_h_in  = 2.55          # inches per card
    header_in = 1.55          # title + intro block
    footer_in = 0.25
    fig_h = header_in + n * row_h_in + footer_in

    fig = plt.figure(figsize=(11, fig_h), facecolor="white")
    ax  = fig.add_axes([0, 0, 1, 1])   # full-figure axes in figure coords
    ax.set_xlim(0, 11)
    ax.set_ylim(0, fig_h)
    ax.axis("off")

    y = fig_h - 0.22

    # ── Section Title ──────────────────────────────────────────────────────────
    ax.text(5.5, y, "Technologies Used in the System",
            ha="center", va="top",
            fontsize=16, fontweight="bold", color="#212121")
    y -= 0.30
    ax.plot([0.4, 10.6], [y, y], color="#E91E8C", lw=1.8)
    y -= 0.28

    intro = (
        "To ensure seamless operation, robust offline capability, and accurate real-time "
        "classification of dragon fruit quality and disease status, PitayaGrade employs a "
        "carefully selected stack of modern technologies. Each component was chosen for its "
        "specific strengths in machine learning inference, mobile deployment, responsive "
        "user interface development, and lightweight on-device data management."
    )
    ax.text(5.5, y, wrap(intro, 120),
            ha="center", va="top",
            fontsize=9, color="#424242",
            linespacing=1.55)
    y -= 0.68

    # ── Technology Cards ───────────────────────────────────────────────────────
    card_x   = 0.30
    card_w   = 10.40
    card_h   = row_h_in - 0.12
    gap      = 0.12

    for tech in TECH_STACK:
        y_bot = y - card_h

        # Card box
        rect = FancyBboxPatch(
            (card_x, y_bot), card_w, card_h,
            boxstyle="round,pad=0.05",
            linewidth=1.1,
            edgecolor=tech["border"],
            facecolor="#FAFAFA",
        )
        ax.add_patch(rect)

        # Left color bar
        bar = FancyBboxPatch(
            (card_x, y_bot), 0.07, card_h,
            boxstyle="square,pad=0",
            linewidth=0,
            facecolor=tech["border"],
        )
        ax.add_patch(bar)

        # Icon circle
        icon_cx = card_x + 0.07 + 0.52
        icon_cy = y_bot + card_h / 2
        circle = plt.Circle((icon_cx, icon_cy), 0.36,
                             color=tech["icon_bg"], zorder=3)
        ax.add_patch(circle)
        circle_edge = plt.Circle((icon_cx, icon_cy), 0.36,
                                  color=tech["icon_color"], fill=False,
                                  linewidth=1.6, zorder=4)
        ax.add_patch(circle_edge)
        ax.text(icon_cx, icon_cy, tech["icon"],
                ha="center", va="center",
                fontsize=9, fontweight="bold",
                color=tech["icon_color"], zorder=5)

        # Text column starts after icon
        tx = card_x + 0.07 + 1.06
        name_y = y_bot + card_h - 0.16

        ax.text(tx, name_y, tech["name"],
                ha="left", va="top",
                fontsize=11.5, fontweight="bold", color="#212121")

        ax.text(tx, name_y - 0.30, tech["category"],
                ha="left", va="top",
                fontsize=8.5, color=tech["border"], fontstyle="italic")

        ax.text(tx, name_y - 0.60, wrap(tech["description"], 96),
                ha="left", va="top",
                fontsize=8.5, color="#424242", linespacing=1.52)

        y = y_bot - gap

    # Footer (using standard hyphens)
    ax.text(5.5, 0.08,
            "PitayaGrade - Bachelor of Science in Information Technology - Capstone Project AY 2025-2026",
            ha="center", va="bottom",
            fontsize=7.5, color="#9E9E9E", style="italic")

    out = os.path.join(OUTPUT_DIR, "tech_used_figure.png")
    plt.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved: {out}")


if __name__ == "__main__":
    draw_tech_figure()
