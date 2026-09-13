"""
Generate Android launcher icons from assets/logo.png
"""
from PIL import Image, ImageDraw
import os, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(BASE, "assets", "logo.png")
RES  = os.path.join(BASE, "android", "app", "src", "main", "res")

SIZES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

FOREGROUND_SIZES = {
    "mipmap-mdpi":    108,
    "mipmap-hdpi":    162,
    "mipmap-xhdpi":   216,
    "mipmap-xxhdpi":  324,
    "mipmap-xxxhdpi": 432,
}

def make_round(img):
    size = img.size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size[0], size[1]), fill=255)
    result = Image.new("RGBA", size, (0, 0, 0, 0))
    result.paste(img, mask=mask)
    return result

src = Image.open(LOGO).convert("RGBA")

for folder, px in SIZES.items():
    out_dir = os.path.join(RES, folder)
    os.makedirs(out_dir, exist_ok=True)

    # Standard icon
    icon = src.resize((px, px), Image.LANCZOS)
    icon.save(os.path.join(out_dir, "ic_launcher.png"))

    # Round icon
    icon_round = make_round(icon.copy())
    bg = Image.new("RGBA", (px, px), (14, 21, 37, 255))
    bg.paste(icon_round, mask=icon_round.split()[3])
    bg.save(os.path.join(out_dir, "ic_launcher_round.png"))

    print(f"  {folder}: ic_launcher.png + ic_launcher_round.png ({px}x{px})")

# Foreground (adaptive icon — used on Android 8+)
for folder, px in FOREGROUND_SIZES.items():
    out_dir = os.path.join(RES, folder)
    os.makedirs(out_dir, exist_ok=True)

    # Foreground: full canvas, logo scaled to 80% centered
    canvas = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    inner = int(px * 0.80)
    logo_scaled = src.resize((inner, inner), Image.LANCZOS)
    offset = (px - inner) // 2
    canvas.paste(logo_scaled, (offset, offset), logo_scaled.split()[3])
    canvas.save(os.path.join(out_dir, "ic_launcher_foreground.png"))
    print(f"  {folder}: ic_launcher_foreground.png ({px}x{px})")

print("\nAll icons generated.")
