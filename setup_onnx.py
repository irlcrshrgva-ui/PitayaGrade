"""
PitayaGrade - ONNX Runtime Web Setup
Run this AFTER training completes.
Copies:
  yolo_results/best.onnx        → www/model/best.onnx
  onnxruntime-web/ort.min.js    → www/ort.min.js
  onnxruntime-web/ort-wasm*.wasm → www/  (WASM backend files)
"""

import subprocess, sys, shutil, os
from pathlib import Path

PROJECT = Path(__file__).parent
WWW     = PROJECT / "www"

# ── 1. Check model exists ────────────────────────────────────────────────────
model_src = PROJECT / "yolo_results" / "train" / "weights" / "best.onnx"
if not model_src.exists():
    # Try the exported copy
    model_src = PROJECT / "yolo_results" / "best.onnx"
if not model_src.exists():
    print("ERROR: best.onnx not found. Make sure training + export completed.")
    print("  Expected: yolo_results/train/weights/best.onnx")
    sys.exit(1)

model_dst = WWW / "model" / "best.onnx"
model_dst.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(model_src, model_dst)
print(f"OK: model copied ({model_dst.stat().st_size / 1e6:.1f} MB)")

# ── 2. Install onnxruntime-web if not present ────────────────────────────────
try:
    import importlib.util
    ort_path = None
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "onnxruntime-web"],
        capture_output=True, text=True
    )
    # onnxruntime-web is a JS package, not Python — use npm instead
except Exception:
    pass

# Use npm to get the JS files
print("Fetching onnxruntime-web JS files via npm...")
npm_result = subprocess.run(
    ["npm", "install", "--prefix", str(PROJECT / "_ort_tmp"), "onnxruntime-web@1.19.0"],
    capture_output=True, text=True, cwd=str(PROJECT)
)
if npm_result.returncode != 0:
    print("npm failed:", npm_result.stderr[:300])
    print("Trying alternative: downloading from unpkg...")
    import urllib.request
    urls = [
        ("https://unpkg.com/onnxruntime-web@1.19.0/dist/ort.min.js",      WWW / "ort.min.js"),
        ("https://unpkg.com/onnxruntime-web@1.19.0/dist/ort-wasm.wasm",    WWW / "ort-wasm.wasm"),
        ("https://unpkg.com/onnxruntime-web@1.19.0/dist/ort-wasm-simd.wasm", WWW / "ort-wasm-simd.wasm"),
    ]
    for url, dst in urls:
        print(f"  Downloading {dst.name}...")
        urllib.request.urlretrieve(url, str(dst))
        print(f"  OK: {dst.stat().st_size / 1e6:.1f} MB")
else:
    # Copy from node_modules
    ort_dist = PROJECT / "_ort_tmp" / "node_modules" / "onnxruntime-web" / "dist"
    files_to_copy = [
        ("ort.min.js",           WWW / "ort.min.js"),
        ("ort-wasm.wasm",        WWW / "ort-wasm.wasm"),
        ("ort-wasm-simd.wasm",   WWW / "ort-wasm-simd.wasm"),
    ]
    for src_name, dst_path in files_to_copy:
        src_f = ort_dist / src_name
        if src_f.exists():
            shutil.copy2(src_f, dst_path)
            print(f"OK: {src_name} → www/ ({dst_path.stat().st_size / 1e6:.1f} MB)")
        else:
            print(f"WARNING: {src_name} not found in npm dist")
    # Cleanup tmp install
    shutil.rmtree(PROJECT / "_ort_tmp", ignore_errors=True)

# ── 3. Verify www/ has everything ────────────────────────────────────────────
print("\nVerifying www/ contents:")
for f in ["ort.min.js", "ort-wasm.wasm", "model/best.onnx"]:
    p = WWW / f
    if p.exists():
        print(f"  OK  {f} ({p.stat().st_size / 1e6:.1f} MB)")
    else:
        print(f"  MISSING  {f}")

print("\nSetup complete. Run: npx cap sync android && gradlew assembleDebug")
