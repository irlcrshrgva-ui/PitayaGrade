import re, sys

with open(r"d:\desktop\PitayaGrade\js\live-scanner.js", "r", encoding="utf-8") as f:
    src = f.read()

# Replace _analyzeFrame to use real model when available
OLD = """  _analyzeFrame() {
    if (!this.video || !this.ctx || this.video.readyState < 2) return;

    this.frameCount++;

    // Capture frame to canvas at 64x64 for analysis
    this.ctx.drawImage(this.video, 0, 0, 64, 64);
    const imageData = this.ctx.getImageData(0, 0, 64, 64);

    // Run the same pixel analysis as the photo scanner
    const result = this._analyzePixels(imageData);

    // Smooth the results for stable HUD display
    this._smoothResult(result);"""

NEW = """  _analyzeFrame() {
    if (!this.video || !this.ctx || this.video.readyState < 2) return;

    this.frameCount++;

    // Capture at 64x64 for HSV fallback, full-res for model
    this.ctx.drawImage(this.video, 0, 0, 64, 64);
    const imageData = this.ctx.getImageData(0, 0, 64, 64);

    if (typeof ModelInference !== 'undefined' && ModelInference.isLoaded) {
      // Use real YOLOv8 model — capture higher-res frame for accuracy
      const cap = document.createElement('canvas');
      cap.width = 320; cap.height = 320;
      cap.getContext('2d').drawImage(this.video, 0, 0, 320, 320);
      const img = new Image();
      img.onload = () => {
        ModelInference.infer(img).then(mr => {
          if (!mr) { this._smoothResult(this._analyzePixels(imageData)); this._updateHud(); return; }
          const hsvResult = this._analyzePixels(imageData);
          const merged = mr.isDragonFruit ? {
            isDragonFruit: true,
            detectedObject: mr.grade === 'Grade A' ? 'Pitaya Premium' :
                            mr.grade === 'Grade B' ? 'Pitaya Standard' :
                            mr.grade === 'Grade C' ? 'Pitaya Economy' : 'Pitaya Reject',
            grade:   { label: mr.grade, confidence: mr.confidence, class: Scanner._gradeClass(mr.grade) },
            disease: hsvResult.isDragonFruit ? hsvResult.disease : { name: 'Healthy', confidence: 0.9, isHealthy: true },
            maturity: hsvResult.isDragonFruit ? hsvResult.maturity : { status: 'Harvestable', value: 75 }
          } : { isDragonFruit: false, detectedObject: 'Unknown Object',
                grade: { label: 'Unrecognized', confidence: 0, class: 'grade-reject' },
                disease: { name: 'N/A', confidence: 0, isHealthy: true },
                maturity: { status: 'N/A', value: 0 } };
          this._smoothResult(merged);
          this._updateHud();
        });
      };
      img.src = cap.toDataURL('image/jpeg', 0.8);
      return; // HUD updated in the promise above
    }

    // HSV fallback when model not loaded
    const result = this._analyzePixels(imageData);

    // Smooth the results for stable HUD display
    this._smoothResult(result);"""

if OLD in src:
    patched = src.replace(OLD, NEW, 1)
    with open(r"d:\desktop\PitayaGrade\js\live-scanner.js", "w", encoding="utf-8") as f:
        f.write(patched)
    print("OK: live-scanner.js patched")
else:
    print("ERROR: _analyzeFrame pattern not found"); sys.exit(1)
