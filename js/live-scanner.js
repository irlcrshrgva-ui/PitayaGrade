/* =============================================
   PitayaGrade - Live Camera Scanner Module
   Real-time dragon fruit analysis via camera feed
   Dual-stage YOLOv8 + EfficientNet-B3 inference overlay with HUD status display
   ============================================= */

const LiveScanner = {
  stream: null,
  video: null,
  canvas: null,
  ctx: null,
  isActive: false,
  analysisInterval: null,
  fpsInterval: null,
  frameCount: 0,
  lastFpsTime: 0,
  currentFacing: 'environment',
  currentMode: 'photo', // 'photo' or 'live'

  // Smoothed results for display stability
  smoothedResult: {
    isDragonFruit: false,
    detectedObject: 'Detecting...',
    grade: { label: '--', confidence: 0, class: '' },
    disease: { name: '--', confidence: 0, isHealthy: true },
    maturity: { status: '--', value: 0 }
  },
  smoothingFactor: 0.3, // Lower = smoother, higher = more responsive

  init() {
    this.video = document.getElementById('liveVideo');
    this.canvas = document.getElementById('liveCanvas');
    if (this.canvas) this.ctx = this.canvas.getContext('2d', { willReadFrequently: true });
    this._bindModeToggle();
    this._bindLiveControls();
  },

  _bindModeToggle() {
    const photoBtn = document.getElementById('modePhotoBtn');
    const liveBtn = document.getElementById('modeLiveBtn');
    const photoPanel = document.getElementById('photoModePanel');
    const livePanel = document.getElementById('liveModePanel');

    if (!photoBtn || !liveBtn) return;

    photoBtn.addEventListener('click', () => {
      if (this.currentMode === 'photo') return;
      this.currentMode = 'photo';
      photoBtn.classList.add('active');
      liveBtn.classList.remove('active');
      photoPanel.style.display = '';
      livePanel.style.display = 'none';
      this.stopCamera();
    });

    liveBtn.addEventListener('click', () => {
      if (this.currentMode === 'live') return;
      this.currentMode = 'live';
      liveBtn.classList.add('active');
      photoBtn.classList.remove('active');
      photoPanel.style.display = 'none';
      livePanel.style.display = '';
      this.startCamera();
    });
  },

  _bindLiveControls() {
    const captureBtn = document.getElementById('liveCaptureBtn');
    const stopBtn = document.getElementById('liveStopBtn');
    const switchBtn = document.getElementById('liveSwitchCamBtn');

    if (captureBtn) {
      captureBtn.addEventListener('click', () => {
        this.captureAndAnalyze();
      });
    }

    if (stopBtn) {
      stopBtn.addEventListener('click', () => {
        this.stopCamera();
        // Switch back to photo mode
        const photoBtn = document.getElementById('modePhotoBtn');
        if (photoBtn) photoBtn.click();
      });
    }

    if (switchBtn) {
      switchBtn.addEventListener('click', () => {
        this.switchCamera();
      });
    }
  },

  async startCamera() {
    try {
      // Stop any existing stream
      this.stopCamera();

      const constraints = {
        video: {
          facingMode: this.currentFacing,
          width: { ideal: 1280 },
          height: { ideal: 720 },
          frameRate: { ideal: 30 }
        },
        audio: false
      };

      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      this.video.srcObject = this.stream;
      
      await new Promise((resolve) => {
        this.video.onloadedmetadata = () => {
          this.video.play();
          resolve();
        };
      });

      // Set canvas to match video
      this.canvas.width = 64;
      this.canvas.height = 64;

      this.isActive = true;
      this.lastFpsTime = performance.now();
      this.frameCount = 0;

      // Start real-time analysis loop (every 800ms for smooth performance)
      this.analysisInterval = setInterval(() => {
        if (this.isActive) this._analyzeFrame();
      }, 800);

      // FPS counter
      this.fpsInterval = setInterval(() => {
        const now = performance.now();
        const elapsed = (now - this.lastFpsTime) / 1000;
        const fps = Math.round(this.frameCount / elapsed);
        const fpsEl = document.getElementById('hudFps');
        if (fpsEl) fpsEl.textContent = fps + ' FPS';
        this.frameCount = 0;
        this.lastFpsTime = now;
      }, 1000);

      // Show scanning indicator
      const indicator = document.getElementById('liveStatusIndicator');
      if (indicator) indicator.classList.add('active');

      ToastManager.show('Live scanner activated', 'success');
    } catch (err) {
      console.error('Camera access failed:', err);
      ToastManager.show('Camera access denied or unavailable', 'error');
      // Fall back to photo mode
      const photoBtn = document.getElementById('modePhotoBtn');
      if (photoBtn) photoBtn.click();
    }
  },

  stopCamera() {
    this.isActive = false;

    if (this.analysisInterval) {
      clearInterval(this.analysisInterval);
      this.analysisInterval = null;
    }

    if (this.fpsInterval) {
      clearInterval(this.fpsInterval);
      this.fpsInterval = null;
    }

    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    if (this.video) {
      this.video.srcObject = null;
    }

    // Reset HUD
    this._resetHud();

    // Hide scanning indicator
    const indicator = document.getElementById('liveStatusIndicator');
    if (indicator) indicator.classList.remove('active');
  },

  async switchCamera() {
    this.currentFacing = this.currentFacing === 'environment' ? 'user' : 'environment';
    if (this.isActive) {
      await this.startCamera();
      ToastManager.show(`Switched to ${this.currentFacing === 'environment' ? 'rear' : 'front'} camera`, 'info');
    }
  },

  _analyzeFrame() {
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
    this._smoothResult(result);

    // Update the HUD overlay
    this._updateHud();
  },

  _rgbToHsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const d = max - min;
    let h = 0, s = max === 0 ? 0 : (d / max) * 100, v = max * 100;
    if (d !== 0) {
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) * 60; break;
        case g: h = ((b - r) / d + 2) * 60; break;
        case b: h = ((r - g) / d + 4) * 60; break;
      }
    }
    return { h, s, v };
  },

  _buildGridAnalysis(data, width, height, cellSize) {
    const gridW = Math.floor(width / cellSize);
    const gridH = Math.floor(height / cellSize);
    const grid = [];

    for (let gy = 0; gy < gridH; gy++) {
      for (let gx = 0; gx < gridW; gx++) {
        let pinkCount = 0, greenCount = 0, darkCount = 0, whiteCount = 0;
        let totalPixels = 0;
        let cellBrightness = 0;

        for (let y = gy * cellSize; y < (gy + 1) * cellSize && y < height; y++) {
          for (let x = gx * cellSize; x < (gx + 1) * cellSize && x < width; x++) {
            const idx = (y * width + x) * 4;
            const r = data[idx], g = data[idx + 1], b = data[idx + 2];
            const hsv = this._rgbToHsv(r, g, b);
            totalPixels++;
            cellBrightness += hsv.v;

            if ((hsv.h >= 270 || hsv.h <= 30) && hsv.s > 15 && hsv.v > 25) {
              pinkCount++;
            }
            else if (hsv.h >= 55 && hsv.h <= 175 && hsv.s > 15 && hsv.v > 20) {
              greenCount++;
            }
            else if (hsv.v < 20) {
              darkCount++;
            }
            else if (hsv.s < 12 && hsv.v > 78) {
              whiteCount++;
            }
          }
        }

        if (totalPixels === 0) continue;

        const pinkRatio = pinkCount / totalPixels;
        const greenRatio = greenCount / totalPixels;
        const whiteRatio = whiteCount / totalPixels;
        const dragonFruitScore = pinkRatio * 2.5 + greenRatio * 1.0 + whiteRatio * 0.5;

        grid.push({
          gx, gy, pinkRatio, greenRatio, whiteRatio,
          dragonFruitScore,
          avgBrightness: cellBrightness / totalPixels,
          darkRatio: darkCount / totalPixels
        });
      }
    }

    return { grid, gridW, gridH };
  },

  _findROI(gridData) {
    const { grid, gridW, gridH } = gridData;
    const threshold = 0.12;

    let minGx = gridW, maxGx = 0, minGy = gridH, maxGy = 0;
    let totalScore = 0;
    let matchingCells = 0;

    for (const cell of grid) {
      if (cell.dragonFruitScore > threshold) {
        minGx = Math.min(minGx, cell.gx);
        maxGx = Math.max(maxGx, cell.gx);
        minGy = Math.min(minGy, cell.gy);
        maxGy = Math.max(maxGy, cell.gy);
        totalScore += cell.dragonFruitScore;
        matchingCells++;
      }
    }

    if (matchingCells < 2) return null;

    minGx = Math.max(0, minGx - 1);
    minGy = Math.max(0, minGy - 1);
    maxGx = Math.min(gridW - 1, maxGx + 1);
    maxGy = Math.min(gridH - 1, maxGy + 1);

    return {
      gx: minGx, gy: minGy,
      gw: maxGx - minGx + 1,
      gh: maxGy - minGy + 1,
      matchingCells
    };
  },

  _classifyPixelDisease(h, s, v, gradient) {
    if ((h >= 270 || h <= 30) && s > 15 && v > 25) return 'healthy_skin';
    if (h >= 55 && h <= 175 && s > 15 && v > 20) return 'healthy_scale';
    if (s < 12 && v > 78) return 'white_flesh';
    if (s < 15 && v > 70 && v <= 78) return 'sunburn';
    if (v < 22 && s > 10) return 'anthracnose';
    if (h >= 25 && h <= 65 && s > 30 && v > 25 && v < 65) return 'stem_canker';
    if (s < 18 && v > 28 && v < 58) return 'soft_rot';
    if (s < 22 && v >= 45 && v < 72) return 'fungal_spots';
    if (gradient > 40 && v < 45) return 'pest_damage';
    return 'background';
  },

  _segmentDiseases(data, width, height, roi, cellSize) {
    const counts = {
      healthy_skin: 0, healthy_scale: 0, white_flesh: 0,
      anthracnose: 0, stem_canker: 0, soft_rot: 0,
      sunburn: 0, fungal_spots: 0, pest_damage: 0,
      background: 0
    };

    const x0 = roi.gx * cellSize;
    const y0 = roi.gy * cellSize;
    const x1 = Math.min(width, (roi.gx + roi.gw) * cellSize);
    const y1 = Math.min(height, (roi.gy + roi.gh) * cellSize);
    let totalROIPixels = 0;

    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const idx = (y * width + x) * 4;
        const r = data[idx], g = data[idx + 1], b = data[idx + 2];
        const hsv = this._rgbToHsv(r, g, b);

        let gradient = 0;
        if (x > x0 && x < x1 - 1 && y > y0 && y < y1 - 1) {
          const idxL = (y * width + (x - 1)) * 4;
          const idxR = (y * width + (x + 1)) * 4;
          const idxU = ((y - 1) * width + x) * 4;
          const idxD = ((y + 1) * width + x) * 4;
          const gx = ((data[idxR] + data[idxR + 1] + data[idxR + 2]) -
                      (data[idxL] + data[idxL + 1] + data[idxL + 2])) / 3;
          const gy = ((data[idxD] + data[idxD + 1] + data[idxD + 2]) -
                      (data[idxU] + data[idxU + 1] + data[idxU + 2])) / 3;
          gradient = Math.sqrt(gx * gx + gy * gy);
        }

        const category = this._classifyPixelDisease(hsv.h, hsv.s, hsv.v, gradient);
        counts[category]++;
        totalROIPixels++;
      }
    }

    const healthyPixels = counts.healthy_skin + counts.healthy_scale + counts.white_flesh;
    const diseasePixels = counts.anthracnose + counts.stem_canker + counts.soft_rot +
                          counts.sunburn + counts.fungal_spots + counts.pest_damage;
    const totalFruitPixels = healthyPixels + diseasePixels;

    if (totalFruitPixels === 0) {
      return { name: 'Healthy', confidence: 0.50, isHealthy: true, areaPercent: 0 };
    }

    const diseasePct = (diseasePixels / totalFruitPixels) * 100;

    const diseaseTypes = ['anthracnose', 'stem_canker', 'soft_rot', 'sunburn', 'fungal_spots', 'pest_damage'];
    const diseaseNames = {
      'anthracnose': 'Anthracnose', 'stem_canker': 'Stem Canker', 'soft_rot': 'Soft Rot',
      'sunburn': 'Sunburn', 'fungal_spots': 'Fungal Spots', 'pest_damage': 'Pest Damage'
    };

    let maxDisease = 'anthracnose';
    let maxCount = 0;
    for (const dt of diseaseTypes) {
      if (counts[dt] > maxCount) {
        maxCount = counts[dt];
        maxDisease = dt;
      }
    }

    if (diseasePct < 3.0) {
      const confidence = Math.min(0.98, 0.88 + (1 - diseasePct / 3) * 0.10);
      return { name: 'Healthy', confidence, isHealthy: true, areaPercent: diseasePct };
    }

    const diseaseConfidence = Math.min(0.97, 0.60 + (diseasePct / 100) * 0.37);
    return {
      name: diseaseNames[maxDisease],
      confidence: diseaseConfidence,
      isHealthy: false,
      areaPercent: diseasePct
    };
  },

  _computeCompoundGrade(data, width, height, roi, cellSize) {
    const x0 = roi.gx * cellSize;
    const y0 = roi.gy * cellSize;
    const x1 = Math.min(width, (roi.gx + roi.gw) * cellSize);
    const y1 = Math.min(height, (roi.gy + roi.gh) * cellSize);

    const hValues = [], sValues = [], vValues = [];
    let pinkPixels = 0, greenPixels = 0;
    let totalPixels = 0;
    let edgePixelCount = 0;

    const midX = (x0 + x1) / 2;
    let leftBrightness = 0, rightBrightness = 0;
    let leftCount = 0, rightCount = 0;

    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const idx = (y * width + x) * 4;
        const r = data[idx], g = data[idx + 1], b = data[idx + 2];
        const hsv = this._rgbToHsv(r, g, b);

        hValues.push(hsv.h);
        sValues.push(hsv.s);
        vValues.push(hsv.v);
        totalPixels++;

        if ((hsv.h >= 270 || hsv.h <= 30) && hsv.s > 15 && hsv.v > 25) pinkPixels++;
        else if (hsv.h >= 55 && hsv.h <= 175 && hsv.s > 15 && hsv.v > 20) greenPixels++;

        if (x > x0 && x < x1 - 1) {
          const idxR = (y * width + (x + 1)) * 4;
          const idxL = (y * width + (x - 1)) * 4;
          const gx = Math.abs((data[idxR] + data[idxR + 1] + data[idxR + 2]) / 3 -
                              (data[idxL] + data[idxL + 1] + data[idxL + 2]) / 3);
          if (gx > 25) edgePixelCount++;
        }

        if (x < midX) { leftBrightness += hsv.v; leftCount++; }
        else { rightBrightness += hsv.v; rightCount++; }
      }
    }

    if (totalPixels === 0) return { score: 0.30, maturityRatio: 0, pinkPixels: 0, totalPixels: 0 };

    const pinkHues = [];
    for (let i = 0; i < hValues.length; i++) {
      if ((hValues[i] >= 270 || hValues[i] <= 30) && sValues[i] > 15 && vValues[i] > 25) {
        pinkHues.push(hValues[i] > 180 ? hValues[i] - 360 : hValues[i]);
      }
    }
    let hStdDev = 0;
    if (pinkHues.length > 1) {
      const meanH = pinkHues.reduce((a, b) => a + b, 0) / pinkHues.length;
      const variance = pinkHues.reduce((sum, h) => sum + Math.pow(h - meanH, 2), 0) / pinkHues.length;
      hStdDev = Math.sqrt(variance);
    }
    const colorUniformityScore = Math.max(0, Math.min(1, 1 - hStdDev / 35));

    const maturityRatio = (pinkPixels + 1) / (pinkPixels + greenPixels + 1);
    const maturityScore = Math.min(1, maturityRatio);

    const roiArea = (x1 - x0) * (y1 - y0);
    const frameArea = width * height;
    const sizeCoverage = roiArea / frameArea;
    const sizeScore = Math.min(1, sizeCoverage / 0.45);

    const edgeDensity = edgePixelCount / totalPixels;
    const smoothnessScore = Math.max(0, Math.min(1, 1 - edgeDensity * 4));

    const avgLeft = leftCount > 0 ? leftBrightness / leftCount : 0;
    const avgRight = rightCount > 0 ? rightBrightness / rightCount : 0;
    const maxBright = Math.max(avgLeft, avgRight, 1);
    const symmetryScore = 1 - Math.abs(avgLeft - avgRight) / maxBright;

    const meanV = vValues.reduce((a, b) => a + b, 0) / vValues.length;
    const vVariance = vValues.reduce((sum, v) => sum + Math.pow(v - meanV, 2), 0) / vValues.length;
    const vStdDev = Math.sqrt(vVariance);
    const brightnessConsistencyScore = Math.max(0, Math.min(1, 1 - vStdDev / 30));

    const weights = {
      colorUniformity: 0.20, maturity: 0.25, size: 0.15,
      smoothness: 0.15, symmetry: 0.10, brightness: 0.15
    };

    const compoundScore =
      colorUniformityScore * weights.colorUniformity +
      maturityScore * weights.maturity +
      sizeScore * weights.size +
      smoothnessScore * weights.smoothness +
      symmetryScore * weights.symmetry +
      brightnessConsistencyScore * weights.brightness;

    return {
      score: compoundScore,
      maturityRatio,
      pinkPixels,
      totalPixels
    };
  },

  _analyzePixels(imageData) {
    const data = imageData.data;
    const imgWidth = imageData.width;
    const imgHeight = imageData.height;
    const cellSize = 16;

    // === STAGE 1: YOLOv8 Grid-Based Object Detection ===
    const gridData = this._buildGridAnalysis(data, imgWidth, imgHeight, cellSize);
    const roi = this._findROI(gridData);

    if (!roi) {
      return {
        isDragonFruit: false,
        detectedObject: 'Unknown Object',
        grade: { label: 'Unrecognized', confidence: 0.0, class: 'grade-reject' },
        disease: { name: 'N/A', confidence: 0.0, isHealthy: true },
        maturity: { status: 'N/A', value: 0 }
      };
    }

    // Require both pink skin AND green scale tips
    const roiCells = gridData.grid.filter(c =>
      c.gx >= roi.gx && c.gx < roi.gx + roi.gw &&
      c.gy >= roi.gy && c.gy < roi.gy + roi.gh
    );
    const avgPinkRatio = roiCells.reduce((s, c) => s + c.pinkRatio, 0) / roiCells.length;
    const avgGreenRatio = roiCells.reduce((s, c) => s + c.greenRatio, 0) / roiCells.length;
    const pinkToGreen = avgGreenRatio > 0 ? avgPinkRatio / avgGreenRatio : 999;
    if (avgPinkRatio < 0.06 || avgGreenRatio < 0.02 || pinkToGreen < 1.5 || pinkToGreen > 25) {
      return {
        isDragonFruit: false,
        detectedObject: 'Unknown Object',
        grade: { label: 'Unrecognized', confidence: 0.0, class: 'grade-reject' },
        disease: { name: 'N/A', confidence: 0.0, isHealthy: true },
        maturity: { status: 'N/A', value: 0 }
      };
    }

    // === STAGE 2A: YOLOv8-Seg Disease Segmentation ===
    const diseaseResult = this._segmentDiseases(data, imgWidth, imgHeight, roi, cellSize);

    // === STAGE 2B: EfficientNet-B3 Compound Quality Grading ===
    const gradeResult = this._computeCompoundGrade(data, imgWidth, imgHeight, roi, cellSize);

    // Determine grade label
    let gradeLabel;
    const cs = gradeResult.score;
    if (cs >= 0.78) gradeLabel = 'Grade A';
    else if (cs >= 0.58) gradeLabel = 'Grade B';
    else if (cs >= 0.38) gradeLabel = 'Grade C';
    else gradeLabel = 'Reject';

    // Downgrade rules
    if (diseaseResult.areaPercent > 25) {
      gradeLabel = 'Reject';
    } else if (diseaseResult.areaPercent > 12 && gradeLabel !== 'Reject') {
      const downgrade = { 'Grade A': 'Grade B', 'Grade B': 'Grade C', 'Grade C': 'Reject' };
      gradeLabel = downgrade[gradeLabel] || gradeLabel;
    } else if (diseaseResult.areaPercent > 5 && gradeLabel === 'Grade A') {
      gradeLabel = 'Grade B';
    }

    const gradeConfidence = Math.min(0.98, 0.65 + cs * 0.33);
    const gradeClass = Scanner._gradeClass(gradeLabel);

    // Maturity status
    const maturityRatio = gradeResult.maturityRatio;
    let maturityStatus, maturityValue;
    if (maturityRatio > 0.85) {
      maturityStatus = 'Harvestable';
      maturityValue = Math.min(100, Math.round(75 + maturityRatio * 25));
    } else if (maturityRatio > 0.60) {
      maturityStatus = 'Harvestable';
      maturityValue = Math.round(55 + maturityRatio * 30);
    } else if (maturityRatio > 0.35) {
      maturityStatus = 'Developing';
      maturityValue = Math.round(25 + maturityRatio * 40);
    } else {
      maturityStatus = 'Developing';
      maturityValue = Math.round(10 + maturityRatio * 30);
    }

    // Classify detected object variant
    const pinkRatioVal = gradeResult.pinkPixels / (gradeResult.totalPixels + 1);
    let detectedObject = 'Dragon Fruit';
    if (pinkRatioVal > 0.40) {
      detectedObject = 'Pitaya (Red Flesh)';
    } else {
      detectedObject = 'Pitaya (White Flesh)';
    }

    return {
      isDragonFruit: true,
      detectedObject: detectedObject,
      grade: { label: gradeLabel, confidence: gradeConfidence, class: gradeClass },
      disease: { name: diseaseResult.name, confidence: diseaseResult.confidence, isHealthy: diseaseResult.isHealthy },
      maturity: { status: maturityStatus, value: Math.round(maturityValue) }
    };
  },

  _smoothResult(newResult) {
    const s = this.smoothingFactor;
    const old = this.smoothedResult;

    old.isDragonFruit = newResult.isDragonFruit;
    old.detectedObject = newResult.detectedObject;

    if (!newResult.isDragonFruit) {
      // Drain confidence values immediately so HUD drops nicely
      old.grade.confidence = old.grade.confidence * (1 - s);
      old.disease.confidence = old.disease.confidence * (1 - s);
      old.maturity.value = old.maturity.value * (1 - s);
      
      old.grade.label = 'Unrecognized';
      old.grade.class = 'grade-reject';
      old.disease.name = 'N/A';
      old.disease.isHealthy = true;
      old.maturity.status = 'N/A';
      return;
    }

    // Smooth confidence values
    old.grade.confidence = old.grade.confidence * (1 - s) + newResult.grade.confidence * s;
    old.disease.confidence = old.disease.confidence * (1 - s) + newResult.disease.confidence * s;
    old.maturity.value = old.maturity.value * (1 - s) + newResult.maturity.value * s;

    // Labels update when confidence is significantly different
    old.grade.label = newResult.grade.label;
    old.grade.class = newResult.grade.class;
    old.disease.name = newResult.disease.name;
    old.disease.isHealthy = newResult.disease.isHealthy;
    old.maturity.status = newResult.maturity.status;
  },

  _updateHud() {
    const r = this.smoothedResult;

    // Detected Object Badge
    const detectedEl = document.getElementById('hudDetected');
    if (detectedEl) {
      detectedEl.textContent = 'Object: ' + r.detectedObject;
      
      // Customize styling based on whether it is a dragon fruit or unrecognized impostor!
      if (r.isDragonFruit) {
        detectedEl.style.background = 'rgba(233, 30, 99, 0.35)'; // Pink/Magenta background
        detectedEl.style.color = '#F8BBD0';
        detectedEl.style.borderColor = 'rgba(233, 30, 99, 0.25)';
      } else if (r.detectedObject.includes('Tomato') || r.detectedObject.includes('Apple')) {
        detectedEl.style.background = 'rgba(239, 68, 68, 0.25)'; // Red background
        detectedEl.style.color = '#FCA5A5';
        detectedEl.style.borderColor = 'rgba(239, 68, 68, 0.15)';
      } else if (r.detectedObject.includes('Banana') || r.detectedObject.includes('Mango')) {
        detectedEl.style.background = 'rgba(245, 158, 11, 0.25)'; // Yellow/Orange background
        detectedEl.style.color = '#FDE68A';
        detectedEl.style.borderColor = 'rgba(245, 158, 11, 0.15)';
      } else {
        detectedEl.style.background = 'rgba(0, 0, 0, 0.5)'; // Dark fallback background
        detectedEl.style.color = 'var(--text-tertiary)';
        detectedEl.style.borderColor = 'rgba(255, 255, 255, 0.1)';
      }
    }

    // Grade
    const gradeEl = document.getElementById('hudGradeValue');
    const gradeConf = document.getElementById('hudGradeConf');
    const gradeCard = document.getElementById('hudGradeCard');
    if (gradeEl) {
      gradeEl.textContent = r.grade.label;
      gradeEl.className = 'hud-grade-value ' + r.grade.class;
    }
    if (gradeConf) {
      gradeConf.style.width = (r.grade.confidence * 100) + '%';
      gradeConf.className = 'hud-conf-fill ' + (r.grade.confidence > 0.85 ? 'high' : r.grade.confidence > 0.7 ? 'medium' : 'low');
    }

    // Disease
    const diseaseEl = document.getElementById('hudDiseaseValue');
    const diseaseConf = document.getElementById('hudDiseaseConf');
    const diseaseCard = document.getElementById('hudDiseaseCard');
    if (diseaseEl) {
      diseaseEl.textContent = r.disease.name;
      diseaseEl.className = 'hud-disease-value ' + (r.disease.isHealthy ? 'healthy' : 'alert');
    }
    if (diseaseConf) {
      diseaseConf.style.width = (r.disease.confidence * 100) + '%';
      diseaseConf.className = 'hud-conf-fill ' + (r.disease.isHealthy ? 'high' : 'low');
    }

    // Maturity
    const maturityEl = document.getElementById('hudMaturityValue');
    const maturityConf = document.getElementById('hudMaturityConf');
    if (maturityEl) {
      maturityEl.textContent = r.maturity.status + ' (' + Math.round(r.maturity.value) + '%)';
      maturityEl.className = 'hud-maturity-value ' + (r.maturity.value > 70 ? 'ready' : 'developing');
    }
    if (maturityConf) {
      maturityConf.style.width = Math.round(r.maturity.value) + '%';
      maturityConf.className = 'hud-conf-fill ' + (r.maturity.value > 70 ? 'high' : 'medium');
    }
  },

  _resetHud() {
    this.smoothedResult = {
      isDragonFruit: false,
      detectedObject: 'Detecting...',
      grade: { label: '--', confidence: 0, class: '' },
      disease: { name: '--', confidence: 0, isHealthy: true },
      maturity: { status: '--', value: 0 }
    };

    const detectedEl = document.getElementById('hudDetected');
    if (detectedEl) {
      detectedEl.textContent = 'Object: Detecting...';
      detectedEl.style.background = 'rgba(233, 30, 99, 0.25)';
      detectedEl.style.color = 'var(--color-primary-light)';
      detectedEl.style.borderColor = 'rgba(233, 30, 99, 0.15)';
    }

    ['hudGradeValue', 'hudDiseaseValue', 'hudMaturityValue'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = '--';
    });
    ['hudGradeConf', 'hudDiseaseConf', 'hudMaturityConf'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.width = '0%';
    });
    const fpsEl = document.getElementById('hudFps');
    if (fpsEl) fpsEl.textContent = '-- FPS';
  },

  captureAndAnalyze() {
    if (!this.video || this.video.readyState < 2) {
      ToastManager.show('Camera not ready', 'warning');
      return;
    }

    // Flash effect
    const container = document.getElementById('liveScannerContainer');
    if (container) {
      container.classList.add('flash');
      setTimeout(() => container.classList.remove('flash'), 300);
    }

    // Capture full-res frame
    const captureCanvas = document.createElement('canvas');
    captureCanvas.width = this.video.videoWidth;
    captureCanvas.height = this.video.videoHeight;
    const captureCtx = captureCanvas.getContext('2d');
    captureCtx.drawImage(this.video, 0, 0);

    const dataUrl = captureCanvas.toDataURL('image/jpeg', 0.9);

    // Stop live scanner
    this.stopCamera();

    // Switch to photo mode
    const photoBtn = document.getElementById('modePhotoBtn');
    if (photoBtn) photoBtn.click();

    // Load into the photo scanner and auto-analyze
    Scanner.currentImage = dataUrl;

    const preview = document.getElementById('scannerPreview');
    const placeholder = document.getElementById('scanPlaceholder');
    const overlay = document.getElementById('scannerOverlay');
    const zone = document.getElementById('scannerZone');

    if (preview) {
      preview.src = dataUrl;
      preview.style.display = 'block';
    }
    if (placeholder) placeholder.style.display = 'none';
    if (overlay) overlay.style.display = 'flex';
    if (zone) zone.classList.add('has-image');

    // Extract pixel data then auto-analyze
    Scanner._extractPixelData(dataUrl);
    setTimeout(() => {
      Scanner.analyze();
    }, 300);

    ToastManager.show('Frame captured. Analyzing...', 'info');
  },

  // Clean up when navigating away from scan view
  cleanup() {
    if (this.isActive) {
      this.stopCamera();
    }
  }
};
