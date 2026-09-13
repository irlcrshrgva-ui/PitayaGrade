import re, sys

with open(r"d:\desktop\PitayaGrade\js\scanner.js", "r", encoding="utf-8") as f:
    src = f.read()

# ── 1. Replace the analyze() body ──────────────────────────────────────────
pattern = re.compile(
    r"(    const steps = processingOverlay\.querySelectorAll\('\.processing-step'\);)"
    r".*?"
    r"(    this\.isProcessing = false;\n  },)",
    re.DOTALL
)

NEW_ANALYZE_MIDDLE = """

    const stepLabel = (el) => el.textContent.replace(/^\\S+\\s/, '').trim();
    const markStep = (i, state) => {
      steps[i].classList.remove('active', 'done');
      if (state === 'active') steps[i].classList.add('active');
      if (state === 'done')   steps[i].classList.add('done');
      const icon = state === 'done' ? '\\u2705' : state === 'active' ? '\\u23F3' : '\\u2B1C';
      steps[i].innerHTML = icon + ' ' + stepLabel(steps[i]);
    };

    // Animate steps 0-3 while real YOLOv8 inference runs in parallel
    for (let i = 0; i < 4; i++) { markStep(i, 'active'); await this._delay(250); }

    const imgEl = document.getElementById('scannerPreview');
    const modelPromise = (typeof ModelInference !== 'undefined' && imgEl)
      ? ModelInference.infer(imgEl)
      : Promise.resolve(null);

    for (let i = 0; i < 4; i++) markStep(i, 'done');
    markStep(4, 'active'); await this._delay(200);

    const modelResult = await modelPromise;

    markStep(4, 'done');
    markStep(5, 'active'); await this._delay(150);

    const result = this._generateResult(modelResult);

    markStep(5, 'done');
    await this._delay(200);

    processingOverlay.classList.add('hidden');
    steps.forEach((s, i) => markStep(i, 'idle'));

    this._displayResult(result);
    this._saveScan(result);

"""

def replacer(m):
    return m.group(1) + NEW_ANALYZE_MIDDLE + m.group(2)

patched, n = pattern.subn(replacer, src)
if n == 0:
    print("ERROR: analyze() pattern not found"); sys.exit(1)
print(f"OK: analyze() replaced ({n})")

# ── 2. Update _generateResult signature ────────────────────────────────────
patched = patched.replace("  _generateResult() {", "  _generateResult(modelResult) {", 1)
print("OK: _generateResult signature updated")

# ── 3. Inject YOLOv8 override block after compound grade computation ───────
INJECT_AFTER = "    const gradeResult = this._computeCompoundGrade(data, imgWidth, imgHeight, roi, cellSize);"

OVERRIDE_BLOCK = """
    // ── YOLOv8 grade override (real model result takes priority) ─────────
    if (modelResult && modelResult.isDragonFruit && modelResult.grade) {
      const gl  = modelResult.grade;
      const gc  = Math.round(modelResult.confidence * 1000) / 1000;
      const diseaseOvr = this._segmentDiseases(data, imgWidth, imgHeight, roi, cellSize);
      const mr = gradeResult.metrics.maturityRatio;
      const matOvr = mr > 0.85
        ? { status: 'Harvestable', value: Math.min(100, Math.round(75 + mr * 25)), isHarvestable: true }
        : mr > 0.60
        ? { status: 'Harvestable', value: Math.round(55 + mr * 30), isHarvestable: true }
        : { status: 'Developing',  value: Math.round(25 + mr * 40), isHarvestable: false };
      const cov = gradeResult.metrics.sizeCoverage;
      const ed  = gradeResult.metrics.edgeDensity;
      const pr  = gradeResult.metrics.pinkPixels / (gradeResult.metrics.totalPixels + 1);
      let tR = 0, tG = 0, tB = 0;
      const tPx = data.length / 4;
      for (let ii = 0; ii < data.length; ii += 4) { tR += data[ii]; tG += data[ii+1]; tB += data[ii+2]; }
      const br = (tR/tPx*0.299 + tG/tPx*0.587 + tB/tPx*0.114) / 255;
      const sizes = this.featureParams.sizes;
      const surfs = this.featureParams.surfaceOptions;
      const cols  = this.featureParams.colorDescriptors;
      const si = cov > 0.55 ? 3 : cov > 0.35 ? 2 : cov > 0.20 ? 1 : 0;
      const ui = ed < 0.08 ? 0 : ed < 0.15 ? 1 : ed < 0.25 ? 2 : ed < 0.35 ? 3 : 4;
      const ci = pr > 0.5 && br > 0.4 ? 0 : pr > 0.4 ? 1 : pr > 0.3 ? 2 : 3;
      const sym = diseaseOvr.isHealthy
        ? ['No visible symptoms detected', 'Uniform skin texture confirmed', 'Normal coloration verified']
        : this._getDiseaseSymptoms(diseaseOvr.name);
      return {
        id: Date.now(), timestamp: new Date().toISOString(), image: this.currentImage,
        isDragonFruit: true,
        grade: { label: gl, confidence: gc, class: this._gradeClass(gl) },
        disease: { name: diseaseOvr.name, confidence: diseaseOvr.confidence,
                   isHealthy: diseaseOvr.isHealthy, symptoms: sym, areaPercent: diseaseOvr.areaPercent },
        maturity: matOvr,
        details: {
          size: sizes[si],
          colorUniformity: (gradeResult.scores.colorUniformity * 100).toFixed(1) + '%',
          colorDescriptor: cols[ci], surfaceCondition: surfs[ui],
          brightness: (br * 100).toFixed(0) + '%',
          processingMode: PitayaApp.settings.offlineMode ? 'Offline (TFLite)' : 'Online (YOLOv8n ONNX)',
          processingTime: (modelResult.inferenceMs / 1000).toFixed(2) + 's',
          modelUsed: 'YOLOv8n ONNX + HSV Disease Segmentation'
        },
        compoundScore: gradeResult.score,
        featureScores: gradeResult.scores,
        modelMetrics: this._getModelMetrics(gl, diseaseOvr.name),
        recommendations: this._getRecommendations(gl, diseaseOvr.name, matOvr.status)
      };
    }
    // ── End YOLOv8 override ───────────────────────────────────────────────
"""

if INJECT_AFTER in patched:
    patched = patched.replace(INJECT_AFTER, INJECT_AFTER + OVERRIDE_BLOCK, 1)
    print("OK: YOLOv8 override block injected")
else:
    print("WARNING: inject point not found — override block skipped")

with open(r"d:\desktop\PitayaGrade\js\scanner.js", "w", encoding="utf-8") as f:
    f.write(patched)
print("Done. scanner.js written.")
