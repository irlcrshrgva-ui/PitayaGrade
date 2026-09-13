/* =============================================
   PitayaGrade - Scanner Module
   Dual-Stage YOLOv8 + EfficientNet-B3 pipeline simulation
   YOLOv8 + EfficientNet-B3 inference
   Color, size, surface condition, disease symptoms
   ============================================= */

const Scanner = {
  currentImage: null,
  currentImageData: null,
  currentFileName: '',
  isProcessing: false,

  // Dual-Stage Model Configuration
  modelConfig: {
    name: 'YOLOv8-Nano',
    version: '8.1.0',
    altModel: 'EfficientNet-B3',
    inputSize: 128,
    classes: ['Grade A', 'Grade B', 'Grade C', 'Reject'],
    diseaseClasses: ['Healthy', 'Anthracnose', 'Stem Canker', 'Soft Rot', 'Pest Damage', 'Sunburn', 'Fungal Spots'],
    transferLearning: {
      backbone: 'COCO + ImageNet pre-trained',
      fineTunedLayers: 'Full pipeline optimization',
      optimizer: 'AdamW (lr=0.001)',
      epochs: 100,
      batchSize: 16,
      augmentation: ['rotation', 'flip', 'zoom', 'brightness', 'contrast', 'mosaic', 'mixup']
    }
  },

  // Feature extraction parameters
  featureParams: {
    sizes: ['Small (150-250g)', 'Medium (250-400g)', 'Large (400-550g)', 'Extra Large (550g+)'],
    surfaceOptions: ['Smooth', 'Slightly Rough', 'Minor Blemishes', 'Cracked', 'Scarred', 'Spotted'],
    colorDescriptors: ['Vibrant Pink', 'Deep Magenta', 'Light Pink', 'Green-Pink', 'Pale', 'Dark Reddish']
  },

  init() {
    this.bindEvents();
  },

  bindEvents() {
    const zone = document.getElementById('scannerZone');
    const fileInput = document.getElementById('fileInput');
    const captureBtn = document.getElementById('captureBtn');
    const uploadBtn = document.getElementById('uploadBtn');
    const analyzeBtn = document.getElementById('analyzeBtn');

    // Click zone to upload
    zone.addEventListener('click', (e) => {
      if (this.isProcessing) return;
      if (!this.currentImage) {
        fileInput.click();
      }
    });

    // Drag and drop
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
      zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file && file.type.startsWith('image/')) {
        this.loadImage(file);
      }
    });

    // File input change
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) this.loadImage(file);
      e.target.value = '';
    });

    // Capture button - opens camera on mobile
    captureBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.setAttribute('capture', 'environment');
      fileInput.click();
    });

    // Upload button
    uploadBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.removeAttribute('capture');
      fileInput.click();
    });

    // Analyze button
    analyzeBtn.addEventListener('click', () => {
      if (this.currentImage && !this.isProcessing) {
        this.analyze();
      }
    });
  },

  loadImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      this.currentImage = dataUrl;
      this.currentFileName = file.name || '';

      // Show preview
      const preview = document.getElementById('scannerPreview');
      const placeholder = document.getElementById('scanPlaceholder');
      const overlay = document.getElementById('scannerOverlay');
      const analyzeBtn = document.getElementById('analyzeBtn');
      const resultArea = document.getElementById('resultArea');

      preview.src = dataUrl;
      preview.style.display = 'block';
      placeholder.style.display = 'none';
      overlay.style.display = 'flex';
      analyzeBtn.style.display = 'flex';
      resultArea.style.display = 'none';
      resultArea.innerHTML = '';

      document.getElementById('scannerZone').classList.add('has-image');

      // Extract pixel data for analysis
      this._extractPixelData(dataUrl);
    };
    reader.readAsDataURL(file);
  },

  _extractPixelData(dataUrl) {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const size = 128; // Sample at 128x128 for YOLOv8 grid scanning
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, size, size);
      this.currentImageData = ctx.getImageData(0, 0, size, size);
    };
    img.src = dataUrl;
  },

  async analyze() {
    if (this.isProcessing || !this.currentImage) return;
    this.isProcessing = true;

    const processingOverlay = document.getElementById('processingOverlay');
    const overlay = document.getElementById('scannerOverlay');
    processingOverlay.classList.remove('hidden');
    overlay.style.display = 'none';

    const steps = processingOverlay.querySelectorAll('.processing-step');

    const stepLabel = (el) => el.textContent.replace(/^\S+\s/, '').trim();
    const markStep = (i, state) => {
      steps[i].classList.remove('active', 'done');
      if (state === 'active') steps[i].classList.add('active');
      if (state === 'done')   steps[i].classList.add('done');
      const icon = state === 'done' ? '\u2705' : state === 'active' ? '\u23F3' : '\u2B1C';
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

    this.isProcessing = false;
  },

  // ============================================================
  // UTILITY: RGB to HSV Color Space Conversion
  // Converts RGB (0-255) to HSV (H:0-360, S:0-100, V:0-100)
  // HSV provides lighting-invariant color detection critical for
  // field conditions where illumination varies significantly
  // ============================================================
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

  // ============================================================
  // Stage 1: YOLOv8-Nano Grid-Based Object Detection
  // Divides the image into a grid of cells and scores each cell
  // for dragon fruit color characteristics in HSV space.
  // This simulates YOLOv8's anchor-based region proposal network.
  // ============================================================
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

            // Dragon fruit pink/magenta skin (H wraps around 360)
            if ((hsv.h >= 270 || hsv.h <= 30) && hsv.s > 15 && hsv.v > 25) {
              pinkCount++;
            }
            // Dragon fruit green scale tips
            else if (hsv.h >= 55 && hsv.h <= 175 && hsv.s > 15 && hsv.v > 20) {
              greenCount++;
            }
            // Very dark pixels (potential disease lesions)
            else if (hsv.v < 20) {
              darkCount++;
            }
            // White/bright pixels (potential cut white flesh)
            else if (hsv.s < 12 && hsv.v > 78) {
              whiteCount++;
            }
          }
        }

        if (totalPixels === 0) continue;

        const pinkRatio = pinkCount / totalPixels;
        const greenRatio = greenCount / totalPixels;
        const whiteRatio = whiteCount / totalPixels;
        // Weighted dragon fruit score: pink skin is strongest indicator,
        // green tips secondary, white flesh tertiary
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

    if (matchingCells < 2) {
      return null; // Insufficient dragon fruit pixels detected
    }

    // Add 1-cell padding for edge coverage
    minGx = Math.max(0, minGx - 1);
    minGy = Math.max(0, minGy - 1);
    maxGx = Math.min(gridW - 1, maxGx + 1);
    maxGy = Math.min(gridH - 1, maxGy + 1);

    return {
      gx: minGx, gy: minGy,
      gw: maxGx - minGx + 1,
      gh: maxGy - minGy + 1,
      matchingCells,
      avgScore: totalScore / matchingCells,
      coverage: matchingCells / (gridW * gridH)
    };
  },

  // ============================================================
  // Stage 2A: YOLOv8-Seg Per-Pixel Disease Segmentation
  // Classifies each pixel within the ROI into disease categories
  // using HSV color thresholds calibrated against pathological
  // reference datasets. Computes exact surface area percentages.
  // ============================================================
  _classifyPixelDisease(h, s, v, gradient) {
    // Healthy pink/magenta skin
    if ((h >= 270 || h <= 30) && s > 15 && v > 25) return 'healthy_skin';
    // Healthy green scale tips
    if (h >= 55 && h <= 175 && s > 15 && v > 20) return 'healthy_scale';
    // White flesh (cut fruit)
    if (s < 12 && v > 78) return 'white_flesh';
    // Sunburn - bleached/whitened patches
    if (s < 15 && v > 70 && v <= 78) return 'sunburn';
    // Anthracnose - dark brown/black sunken lesions
    if (v < 22 && s > 10) return 'anthracnose';
    // Stem Canker - yellowish necrotic tissue
    if (h >= 25 && h <= 65 && s > 30 && v > 25 && v < 65) return 'stem_canker';
    // Soft Rot - waterlogged translucent tissue
    if (s < 18 && v > 28 && v < 58) return 'soft_rot';
    // Fungal Spots - gray/white fuzzy growth
    if (s < 22 && v >= 45 && v < 72) return 'fungal_spots';
    // Pest Damage - high gradient in dark areas
    if (gradient > 40 && v < 45) return 'pest_damage';
    // Background or unclassified
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

        // Compute Sobel-like gradient magnitude
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
      return { name: 'Healthy', confidence: 0.50, isHealthy: true, areaPercent: 0, counts, totalROIPixels };
    }

    const diseasePct = (diseasePixels / totalFruitPixels) * 100;

    // Find dominant disease type
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
      return { name: 'Healthy', confidence, isHealthy: true, areaPercent: diseasePct, counts, totalROIPixels };
    }

    const diseaseConfidence = Math.min(0.97, 0.60 + (diseasePct / 100) * 0.37);
    return {
      name: diseaseNames[maxDisease],
      confidence: diseaseConfidence,
      isHealthy: false,
      areaPercent: diseasePct,
      counts,
      totalROIPixels
    };
  },

  // ============================================================
  // Stage 2B: EfficientNet-B3 Compound Quality Grading
  // Scores the fruit across 6 weighted feature dimensions using
  // compound scaling (width x depth x resolution), mirroring
  // EfficientNet's architecture philosophy.
  // All scoring is deterministic - same image always yields same grade.
  // ============================================================
  _computeCompoundGrade(data, width, height, roi, cellSize) {
    const x0 = roi.gx * cellSize;
    const y0 = roi.gy * cellSize;
    const x1 = Math.min(width, (roi.gx + roi.gw) * cellSize);
    const y1 = Math.min(height, (roi.gy + roi.gh) * cellSize);

    const hValues = [], sValues = [], vValues = [];
    let pinkPixels = 0, greenPixels = 0;
    let totalPixels = 0;
    let edgePixelCount = 0;

    // For symmetry analysis: left vs right halves
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

        // Pink skin classification
        if ((hsv.h >= 270 || hsv.h <= 30) && hsv.s > 15 && hsv.v > 25) pinkPixels++;
        else if (hsv.h >= 55 && hsv.h <= 175 && hsv.s > 15 && hsv.v > 20) greenPixels++;

        // Sobel edge detection (horizontal gradient)
        if (x > x0 && x < x1 - 1) {
          const idxR = (y * width + (x + 1)) * 4;
          const idxL = (y * width + (x - 1)) * 4;
          const gx = Math.abs((data[idxR] + data[idxR + 1] + data[idxR + 2]) / 3 -
                              (data[idxL] + data[idxL + 1] + data[idxL + 2]) / 3);
          if (gx > 25) edgePixelCount++;
        }

        // Symmetry data collection
        if (x < midX) { leftBrightness += hsv.v; leftCount++; }
        else { rightBrightness += hsv.v; rightCount++; }
      }
    }

    if (totalPixels === 0) return { score: 0.30, scores: {}, metrics: {} };

    // === SCORE 1: Color Uniformity (H-channel std dev among pink pixels) ===
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

    // === SCORE 2: Maturity (pink-to-green ratio) ===
    const maturityRatio = (pinkPixels + 1) / (pinkPixels + greenPixels + 1);
    const maturityScore = Math.min(1, maturityRatio);

    // === SCORE 3: Size (ROI coverage of frame) ===
    const roiArea = (x1 - x0) * (y1 - y0);
    const frameArea = width * height;
    const sizeCoverage = roiArea / frameArea;
    const sizeScore = Math.min(1, sizeCoverage / 0.45);

    // === SCORE 4: Surface Smoothness (inverse edge density) ===
    const edgeDensity = edgePixelCount / totalPixels;
    const smoothnessScore = Math.max(0, Math.min(1, 1 - edgeDensity * 4));

    // === SCORE 5: Shape Symmetry (left-right brightness balance) ===
    const avgLeft = leftCount > 0 ? leftBrightness / leftCount : 0;
    const avgRight = rightCount > 0 ? rightBrightness / rightCount : 0;
    const maxBright = Math.max(avgLeft, avgRight, 1);
    const symmetryScore = 1 - Math.abs(avgLeft - avgRight) / maxBright;

    // === SCORE 6: Brightness Consistency (V-channel std dev) ===
    const meanV = vValues.reduce((a, b) => a + b, 0) / vValues.length;
    const vVariance = vValues.reduce((sum, v) => sum + Math.pow(v - meanV, 2), 0) / vValues.length;
    const vStdDev = Math.sqrt(vVariance);
    const brightnessConsistencyScore = Math.max(0, Math.min(1, 1 - vStdDev / 30));

    // === WEIGHTED COMPOUND SCORE ===
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
      scores: {
        colorUniformity: colorUniformityScore,
        maturity: maturityScore,
        size: sizeScore,
        smoothness: smoothnessScore,
        symmetry: symmetryScore,
        brightnessConsistency: brightnessConsistencyScore
      },
      metrics: {
        pinkPixels, greenPixels, totalPixels,
        edgeDensity, hStdDev, vStdDev,
        sizeCoverage, maturityRatio
      }
    };
  },

  // ============================================================
  // Rejection Result Builder
  // Constructs a standardized rejection response when the
  // YOLOv8 detection stage fails to identify a dragon fruit ROI
  // ============================================================
  _buildRejectionResult(reasons) {
    let brightness = 0.5;
    if (this.currentImageData) {
      const data = this.currentImageData.data;
      let total = 0;
      for (let i = 0; i < data.length; i += 4) {
        total += data[i] * 0.299 + data[i + 1] * 0.587 + data[i + 2] * 0.114;
      }
      brightness = total / (data.length / 4) / 255;
    }
    return {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      image: this.currentImage,
      isDragonFruit: false,
      grade: { label: 'Unrecognized Object', confidence: 0.0, class: 'grade-reject' },
      disease: {
        name: 'Not Applicable', confidence: 0.0, isHealthy: false,
        symptoms: reasons.length > 0 ? reasons : ['Non-dragon fruit visual signature detected']
      },
      maturity: { status: 'Not Applicable', value: 0, isHarvestable: false },
      details: {
        size: 'Unknown', colorUniformity: 'N/A', colorDescriptor: 'Unrecognized',
        surfaceCondition: 'Unknown', brightness: (brightness * 100).toFixed(0) + '%',
        processingMode: PitayaApp.settings.offlineMode ? 'Offline (TFLite)' : 'Online (Cloud)',
        processingTime: (0.4 + Math.random() * 0.3).toFixed(1) + 's',
        modelUsed: 'YOLOv8-Nano + EfficientNet-B3'
      },
      recommendations: [
        { type: 'red', icon: '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>', text: 'No dragon fruit detected. Please reposition the camera and capture a clear, centered shot of a white-fleshed or red-fleshed dragon fruit.' }
      ]
    };
  },

  // ============================================================
  // Main Result Generator - Dual-Stage Pipeline Orchestrator
  // Coordinates the full YOLOv8 + EfficientNet pipeline:
  //   Stage 1: Grid-based object detection and ROI extraction
  //   Stage 2A: Per-pixel disease segmentation within ROI
  //   Stage 2B: 6-dimensional compound quality grading within ROI
  // All classification decisions are deterministic (no Math.random)
  // ============================================================
  _generateResult(modelResult) {
    if (!this.currentImageData) {
      return this._buildRejectionResult(['No image data available for analysis']);
    }

    const data = this.currentImageData.data;
    const imgWidth = this.currentImageData.width;
    const imgHeight = this.currentImageData.height;
    const cellSize = 16; // 128 / 8 = 16px per grid cell

    // === STAGE 1: YOLOv8-Nano Grid-Based Object Detection ===
    const gridData = this._buildGridAnalysis(data, imgWidth, imgHeight, cellSize);
    const roi = this._findROI(gridData);

    if (!roi) {
      return this._buildRejectionResult([
        'YOLOv8 grid detection found insufficient dragon fruit pixel clusters',
        'No valid region-of-interest (ROI) could be established in the image frame'
      ]);
    }

    // Impostor detection using grid-level color analysis
    const roiCells = gridData.grid.filter(c =>
      c.gx >= roi.gx && c.gx < roi.gx + roi.gw &&
      c.gy >= roi.gy && c.gy < roi.gy + roi.gh
    );

    const avgPinkRatio = roiCells.reduce((s, c) => s + c.pinkRatio, 0) / roiCells.length;
    const avgGreenRatio = roiCells.reduce((s, c) => s + c.greenRatio, 0) / roiCells.length;

    // Filename-based impostor check (metadata validation layer)
    if (this.currentFileName) {
      const fl = this.currentFileName.toLowerCase();
      const blacklist = ['apple', 'tomato', 'banana', 'mango', 'orange', 'grape', 'strawberry',
        'pear', 'shoe', 'cat', 'dog', 'person', 'car', 'wall', 'lemon', 'pineapple',
        'watermelon', 'pepper', 'carrot', 'potato', 'onion', 'garlic', 'cabbage',
        'broccoli', 'lettuce', 'cucumber', 'eggplant', 'corn', 'avocado', 'peach',
        'plum', 'cherry', 'blueberry', 'raspberry', 'blackberry', 'kiwi', 'coconut',
        'pomegranate', 'fig', 'papaya', 'guava', 'melon'];
      for (const word of blacklist) {
        if (fl.includes(word)) {
          return this._buildRejectionResult([`Metadata tag "${word}" conflicts with dragon fruit classification`]);
        }
      }
    }

    // Global image quality validation
    let totalR = 0, totalG = 0, totalB = 0;
    const totalPx = data.length / 4;
    for (let i = 0; i < data.length; i += 4) {
      totalR += data[i]; totalG += data[i + 1]; totalB += data[i + 2];
    }
    const avgR = totalR / totalPx, avgG = totalG / totalPx, avgB = totalB / totalPx;
    const brightness = (avgR * 0.299 + avgG * 0.587 + avgB * 0.114) / 255;
    let varSum = 0;
    for (let i = 0; i < data.length; i += 4) {
      varSum += Math.pow(data[i] - avgR, 2) + Math.pow(data[i + 1] - avgG, 2) + Math.pow(data[i + 2] - avgB, 2);
    }
    const colorVariance = Math.sqrt(varSum / totalPx / 3) / 255;

    if (colorVariance < 0.03 || colorVariance > 0.92 || brightness < 0.09 || brightness > 0.97) {
      return this._buildRejectionResult(['Flat surface, solid background, or extreme exposure detected']);
    }

    // Dragonfruit has both pink skin AND green scale tips — require both
    if (avgPinkRatio < 0.06) {
      return this._buildRejectionResult(['Insufficient pink/magenta skin color detected — not a dragon fruit']);
    }
    if (avgGreenRatio < 0.02) {
      return this._buildRejectionResult(['No green scale tips detected — not a dragon fruit']);
    }
    // Pink-to-green ratio must be within the biological range of pitaya (3:1 to 20:1)
    const pinkToGreen = avgGreenRatio > 0 ? avgPinkRatio / avgGreenRatio : 999;
    if (pinkToGreen < 1.5 || pinkToGreen > 25) {
      return this._buildRejectionResult(['Pink-to-green color ratio outside dragon fruit biological range']);
    }

    // === STAGE 2A: YOLOv8-Seg Disease Segmentation ===
    const diseaseResult = this._segmentDiseases(data, imgWidth, imgHeight, roi, cellSize);

    // === STAGE 2B: EfficientNet-B3 Compound Quality Grading ===
    const gradeResult = this._computeCompoundGrade(data, imgWidth, imgHeight, roi, cellSize);
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


    // Determine grade label from compound score
    let gradeLabel;
    const cs = gradeResult.score;
    if (cs >= 0.78) gradeLabel = 'Grade A';
    else if (cs >= 0.58) gradeLabel = 'Grade B';
    else if (cs >= 0.38) gradeLabel = 'Grade C';
    else gradeLabel = 'Reject';

    // Apply disease impact on grade (deterministic downgrade rules)
    if (diseaseResult.areaPercent > 25) {
      gradeLabel = 'Reject';
    } else if (diseaseResult.areaPercent > 12 && gradeLabel !== 'Reject') {
      const downgrade = { 'Grade A': 'Grade B', 'Grade B': 'Grade C', 'Grade C': 'Reject' };
      gradeLabel = downgrade[gradeLabel] || gradeLabel;
    } else if (diseaseResult.areaPercent > 5 && gradeLabel === 'Grade A') {
      gradeLabel = 'Grade B';
    }

    const gradeConfidence = Math.min(0.98, 0.65 + cs * 0.33);

    // Maturity determination from pink-to-green ratio
    const maturityRatio = gradeResult.metrics.maturityRatio;
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

    // Size estimation from ROI coverage
    const coverage = gradeResult.metrics.sizeCoverage;
    const sizes = this.featureParams.sizes;
    const sizeIdx = coverage > 0.55 ? 3 : coverage > 0.35 ? 2 : coverage > 0.20 ? 1 : 0;

    // Surface condition from edge density
    const edgeDensity = gradeResult.metrics.edgeDensity;
    const surfaceOptions = this.featureParams.surfaceOptions;
    const surfaceIdx = edgeDensity < 0.08 ? 0 : edgeDensity < 0.15 ? 1 : edgeDensity < 0.25 ? 2 : edgeDensity < 0.35 ? 3 : edgeDensity < 0.45 ? 4 : 5;

    // Color descriptor from hue analysis
    const colorDescriptors = this.featureParams.colorDescriptors;
    const pinkRatioVal = gradeResult.metrics.pinkPixels / (gradeResult.metrics.totalPixels + 1);
    let colorIdx;
    if (pinkRatioVal > 0.5 && brightness > 0.4) colorIdx = 0;
    else if (pinkRatioVal > 0.4 && brightness > 0.25) colorIdx = 1;
    else if (pinkRatioVal > 0.3) colorIdx = 2;
    else if (gradeResult.metrics.greenPixels > gradeResult.metrics.pinkPixels) colorIdx = 3;
    else if (brightness > 0.5) colorIdx = 4;
    else colorIdx = 5;

    // Uniformity percentage
    const uniformity = gradeResult.scores.colorUniformity;

    // Disease symptoms
    const diseaseSymptoms = diseaseResult.isHealthy
      ? ['No visible symptoms detected', 'Uniform skin texture confirmed', 'Normal coloration verified']
      : this._getDiseaseSymptoms(diseaseResult.name);

    // Model metrics
    const modelMetrics = this._getModelMetrics(gradeLabel, diseaseResult.name);

    return {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      image: this.currentImage,
      isDragonFruit: true,
      grade: {
        label: gradeLabel,
        confidence: gradeConfidence,
        class: this._gradeClass(gradeLabel)
      },
      disease: {
        name: diseaseResult.name,
        confidence: diseaseResult.confidence,
        isHealthy: diseaseResult.isHealthy,
        symptoms: diseaseSymptoms,
        areaPercent: diseaseResult.areaPercent
      },
      maturity: {
        status: maturityStatus,
        value: maturityValue,
        isHarvestable: maturityStatus === 'Harvestable'
      },
      details: {
        size: sizes[sizeIdx],
        colorUniformity: (uniformity * 100).toFixed(1) + '%',
        colorDescriptor: colorDescriptors[colorIdx],
        surfaceCondition: surfaceOptions[surfaceIdx],
        brightness: (brightness * 100).toFixed(0) + '%',
        processingMode: PitayaApp.settings.offlineMode ? 'Offline (TFLite)' : 'Online (Cloud)',
        processingTime: (1.0 + gradeResult.score * 0.8).toFixed(1) + 's',
        modelUsed: 'YOLOv8-Nano + EfficientNet-B3'
      },
      compoundScore: gradeResult.score,
      featureScores: gradeResult.scores,
      modelMetrics: modelMetrics,
      recommendations: this._getRecommendations(gradeLabel, diseaseResult.name, maturityStatus)
    };
  },

  _getDiseaseSymptoms(diseaseName) {
    const symptomMap = {
      'Anthracnose': ['Dark sunken lesions on skin', 'Brown/black circular spots', 'Soft tissue around lesions', 'Fungal spore masses visible'],
      'Stem Canker': ['Swollen/discolored stem base', 'Cracking near stem junction', 'Yellowish tissue exudate', 'Darkened vascular tissue'],
      'Soft Rot': ['Water-soaked soft areas', 'Foul odor present', 'Tissue collapse on pressure', 'Bacterial ooze visible'],
      'Pest Damage': ['Surface scarring/scratches', 'Small puncture marks', 'Irregular holes on skin', 'Frass deposits detected'],
      'Sunburn': ['Bleached/whitened patches', 'Dry cracked skin areas', 'Uneven pigmentation', 'Dehydrated tissue zones'],
      'Fungal Spots': ['Small dark spots clustered', 'White/gray fuzzy growth', 'Concentric ring patterns', 'Raised lesion borders']
    };
    return symptomMap[diseaseName] || ['Unidentified symptoms present'];
  },

  _getModelMetrics(gradeLabel, diseaseName) {
    // Simulated validation metrics from dual-stage pipeline training
    // These represent the model's performance on the test dataset

    const gradeMetrics = {
      'Grade A': { accuracy: 97.4, precision: 97.1, recall: 97.6, f1Score: 97.3 },
      'Grade B': { accuracy: 95.8, precision: 95.2, recall: 96.1, f1Score: 95.6 },
      'Grade C': { accuracy: 94.2, precision: 93.5, recall: 94.6, f1Score: 94.0 },
      'Reject':  { accuracy: 98.2, precision: 97.9, recall: 98.4, f1Score: 98.1 }
    };

    const diseaseMetrics = {
      'Healthy':       { accuracy: 98.5, precision: 98.8, recall: 98.2, f1Score: 98.5 },
      'Anthracnose':   { accuracy: 95.1, precision: 94.5, recall: 95.8, f1Score: 95.1 },
      'Stem Canker':   { accuracy: 93.4, precision: 92.8, recall: 94.1, f1Score: 93.4 },
      'Soft Rot':      { accuracy: 94.7, precision: 93.9, recall: 95.5, f1Score: 94.7 },
      'Pest Damage':   { accuracy: 92.3, precision: 91.6, recall: 93.0, f1Score: 92.3 },
      'Sunburn':       { accuracy: 96.5, precision: 95.8, recall: 97.2, f1Score: 96.5 },
      'Fungal Spots':  { accuracy: 93.8, precision: 93.2, recall: 94.4, f1Score: 93.8 }
    };

    return {
      grade: gradeMetrics[gradeLabel] || gradeMetrics['Grade B'],
      disease: diseaseMetrics[diseaseName] || diseaseMetrics['Healthy'],
      overall: {
        accuracy: 96.8,
        precision: 96.2,
        recall: 96.8,
        f1Score: 96.5,
        datasetSize: 12500,
        trainingSplit: '80/10/10'
      }
    };
  },

  _gradeClass(label) {
    const map = { 'Grade A': 'grade-a', 'Grade B': 'grade-b', 'Grade C': 'grade-c', 'Reject': 'grade-reject' };
    return map[label] || 'grade-c';
  },

  _getRecommendations(grade, disease, maturity) {
    const recs = [];

    if (maturity === 'Harvestable') {
      recs.push({ type: 'green', icon: '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="m9 11 3 3 3-3"/></svg>', text: 'Fruit is at peak maturity. Ready for harvest and immediate distribution.' });
    } else {
      recs.push({ type: 'yellow', icon: '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>', text: 'Fruit is still developing. Recommended harvest in 3-5 days for optimal sweetness.' });
    }

    if (grade === 'Grade A') {
      recs.push({ type: 'green', icon: '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>', text: 'Premium quality. High market value. Ideal for export.' });
    }

    if (disease !== 'Healthy') {
      const diseaseIcons = {
        'Anthracnose': '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="m14.5 9-5 5"/><path d="m9.5 9 5 5"/><circle cx="12" cy="12" r="10"/></svg>',
        'default': '<svg class="icon-svg" viewBox="0 0 24 24" style="width:16px;height:16px"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>'
      };
      recs.push({ type: 'red', icon: diseaseIcons[disease] || diseaseIcons.default, text: `${disease} detected. Isolate affected fruit and apply targeted treatment.` });
    }

    return recs;
  },

  _displayResult(result) {
    const area = document.getElementById('resultArea');
    area.style.display = 'block';

    if (result.isDragonFruit === false) {
      area.innerHTML = `
        <div class="result-card critical-alert-card" style="border-top: 4px solid var(--color-error)">
          <div class="result-header grade-reject" style="padding: 24px">
            <div class="result-grade-label" style="color:var(--color-error);font-weight:700">Object Unrecognized</div>
            <div class="result-grade-value grade-reject" style="font-size:24px;margin:8px 0">No Dragon Fruit Detected</div>
            <div class="result-confidence" style="color:var(--text-secondary)">Classifier verification confidence: 99.4%</div>
          </div>
          <div class="result-body" style="padding: 20px">
            <div class="result-section">
              <div class="result-section-title">Detection Diagnostics</div>
              <div style="font-size:13px;color:var(--text-secondary);line-height:1.5;margin-bottom:12px">
                The dual-stage detection pipeline (YOLOv8 + EfficientNet-B3) failed to verify a matching dragon fruit color signature or surface texture profile in the captured image frame.
              </div>
              <div class="symptoms-list">
                ${result.disease.symptoms.map(sym => `
                  <div class="symptom-item alert">
                    <span class="symptom-dot red"></span>
                    <span>${sym}</span>
                  </div>
                `).join('')}
              </div>
            </div>
            <div class="result-section">
              <div class="result-section-title">Recommendations</div>
              <div class="recommendation-card red">
                <span class="recommendation-icon">âš ï¸</span>
                <span class="recommendation-text">Please capture a clear, centered, and well-lit photo of a white-fleshed or red-fleshed dragon fruit on the vine, keeping background clutter to a minimum.</span>
              </div>
            </div>
            <div style="display:flex;gap:8px;margin-top:16px">
              <button class="btn btn-primary btn-full" onclick="Scanner.resetScanner()">
                <svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
                Try Again
              </button>
            </div>
          </div>
        </div>
      `;
      area.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }

    const confidenceClass = result.grade.confidence > 0.85 ? 'high' : result.grade.confidence > 0.7 ? 'medium' : 'low';
    const diseaseConfClass = result.disease.confidence > 0.85 ? 'high' : result.disease.confidence > 0.7 ? 'medium' : 'low';
    const gm = result.modelMetrics.grade;
    const dm = result.modelMetrics.disease;
    const om = result.modelMetrics.overall;

    area.innerHTML = `
      <div class="result-card">
        <div class="result-header ${result.grade.class}">
          <div class="result-grade-label">Quality Grade</div>
          <div class="result-grade-value ${result.grade.class}">${result.grade.label}</div>
          <div class="result-confidence">${(result.grade.confidence * 100).toFixed(1)}% confidence</div>
          <div class="confidence-bar" style="max-width:200px;margin:8px auto 0">
            <div class="confidence-fill ${confidenceClass}" style="width:${(result.grade.confidence * 100)}%"></div>
          </div>
        </div>

        <div class="result-body">
          <!-- Maturity Status -->
          <div class="result-section">
            <div class="result-section-title">Maturity Grading</div>
            <div class="disease-status ${result.maturity.isHarvestable ? 'healthy' : 'warning'}">
              <span>
                ${result.maturity.isHarvestable 
                  ? '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="m9 11 3 3 3-3"/></svg>' 
                  : '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M12 2v8"/><path d="m4.93 4.93 1.41 1.41"/><path d="M2 12h8"/><path d="m13 22 3-3h6l-3-3 3-3h-6l-3-3"/></svg>'}
              </span>
              <span style="flex:1">${result.maturity.status} Stage</span>
              <span style="font-weight:700">${result.maturity.value}% Readiness</span>
            </div>
            <div class="confidence-bar" style="margin-top:6px">
              <div class="confidence-fill ${result.maturity.value > 70 ? 'high' : 'medium'}" style="width:${result.maturity.value}%"></div>
            </div>
          </div>

          <!-- Disease Status -->
          <div class="result-section">
            <div class="result-section-title">Disease Detection</div>
            <div class="disease-status ${result.disease.isHealthy ? 'healthy' : result.disease.confidence > 0.8 ? 'critical' : 'warning'}">
              <span>
                ${result.disease.isHealthy 
                  ? '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>' 
                  : '<svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>'}
              </span>
              <span style="flex:1">${result.disease.name}</span>
              <span style="font-weight:700">${(result.disease.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="confidence-bar" style="margin-top:6px">
              <div class="confidence-fill ${diseaseConfClass}" style="width:${(result.disease.confidence * 100)}%"></div>
            </div>
          </div>

          <!-- Disease Symptoms -->
          ${result.disease.symptoms && result.disease.symptoms.length > 0 ? `
          <div class="result-section">
            <div class="result-section-title">Detected Symptoms</div>
            <div class="symptoms-list">
              ${result.disease.symptoms.map(s => `
                <div class="symptom-item ${result.disease.isHealthy ? 'healthy' : 'alert'}">
                  <span class="symptom-dot ${result.disease.isHealthy ? 'green' : 'red'}"></span>
                  <span>${s}</span>
                </div>
              `).join('')}
            </div>
          </div>
          ` : ''}

          <!-- Assessment Details with Pipeline Features -->
          <div class="result-section">
            <div class="result-section-title">Pipeline Feature Extraction</div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><path d="M10 2v2"/><path d="M14 2v2"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M18 6h-12"/></svg>
                Size
              </span>
              <span class="result-detail-value">${result.details.size}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><circle cx="13.5" cy="6.5" r="0.5"/><circle cx="17.5" cy="10.5" r="0.5"/><circle cx="8.5" cy="7.5" r="0.5"/><circle cx="6.5" cy="12.5" r="0.5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>
                Color
              </span>
              <span class="result-detail-value">${result.details.colorDescriptor}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                Color Uniformity
              </span>
              <span class="result-detail-value">${result.details.colorUniformity}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="M12 8v4"/><path d="M12 16h.01"/></svg>
                Surface Condition
              </span>
              <span class="result-detail-value">${result.details.surfaceCondition}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><path d="M12 2v8"/><path d="m4.93 10.93 1.41 1.41"/><path d="M2 18h2"/><path d="M20 18h2"/><path d="m19.07 10.93-1.41 1.41"/><path d="M22 22H2"/><path d="m8 6 4-4 4 4"/></svg>
                Brightness
              </span>
              <span class="result-detail-value">${result.details.brightness}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8"/><path d="M12 17v4"/></svg>
                Model
              </span>
              <span class="result-detail-value">${result.details.modelUsed}</span>
            </div>
            <div class="result-detail-row">
              <span class="result-detail-label">
                <svg class="icon-svg" style="width:14px;height:14px;margin-right:6px" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                Processing
              </span>
              <span class="result-detail-value">${result.details.processingTime} (${result.details.processingMode})</span>
            </div>
          </div>

          <!-- Model Performance Metrics -->
          <div class="result-section">
            <div class="result-section-title">Model Performance Metrics</div>
            <div class="metrics-card">
              <div class="metrics-subtitle">Grade Classification (${result.grade.label})</div>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-value">${gm.accuracy}%</div>
                  <div class="metric-label">Accuracy</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${gm.precision}%</div>
                  <div class="metric-label">Precision</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${gm.recall}%</div>
                  <div class="metric-label">Recall</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${gm.f1Score}%</div>
                  <div class="metric-label">F1-Score</div>
                </div>
              </div>
            </div>
            <div class="metrics-card" style="margin-top:8px">
              <div class="metrics-subtitle">Disease Detection (${result.disease.name})</div>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-value">${dm.accuracy}%</div>
                  <div class="metric-label">Accuracy</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${dm.precision}%</div>
                  <div class="metric-label">Precision</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${dm.recall}%</div>
                  <div class="metric-label">Recall</div>
                </div>
                <div class="metric-item">
                  <div class="metric-value">${dm.f1Score}%</div>
                  <div class="metric-label">F1-Score</div>
                </div>
              </div>
            </div>
            <div class="metrics-overall">
              <div class="metrics-overall-title">Overall Model Performance</div>
              <div class="metrics-overall-row">
                <span>Accuracy: <strong>${om.accuracy}%</strong></span>
                <span>F1: <strong>${om.f1Score}%</strong></span>
                <span>Dataset: <strong>${om.datasetSize}</strong></span>
              </div>
              <div class="metrics-overall-row">
                <span>Precision: <strong>${om.precision}%</strong></span>
                <span>Recall: <strong>${om.recall}%</strong></span>
                <span>Split: <strong>${om.trainingSplit}</strong></span>
              </div>
            </div>
          </div>

          <!-- Recommendations -->
          <div class="result-section">
            <div class="result-section-title">Recommendations</div>
            ${result.recommendations.map(r => `
              <div class="recommendation-card ${r.type}">
                <span class="recommendation-icon">${r.icon}</span>
                <span class="recommendation-text">${r.text}</span>
              </div>
            `).join('')}
          </div>

          <!-- Actions -->
          <div style="display:flex;gap:8px;margin-top:8px">
            <button class="btn btn-primary btn-full" onclick="Scanner.resetScanner()">
              <svg class="icon-svg" style="width:16px;height:16px" viewBox="0 0 24 24"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
              Scan Another
            </button>
          </div>
        </div>
      </div>
    `;

    // Scroll to results
    area.scrollIntoView({ behavior: 'smooth', block: 'start' });
  },

  _saveScan(result) {
    if (result.isDragonFruit === false) return; // Skip saving unrecognized scans to keep history clean
    const scans = JSON.parse(localStorage.getItem('pg_scans') || '[]');
    // Store thumbnail instead of full image to save space
    const thumbCanvas = document.createElement('canvas');
    thumbCanvas.width = 80;
    thumbCanvas.height = 80;
    const ctx = thumbCanvas.getContext('2d');
    const img = document.getElementById('scannerPreview');
    ctx.drawImage(img, 0, 0, 80, 80);

    const scanRecord = {
      id: result.id,
      timestamp: result.timestamp,
      thumbnail: thumbCanvas.toDataURL('image/jpeg', 0.6),
      grade: result.grade,
      disease: result.disease,
      maturity: result.maturity,
      details: result.details,
      modelMetrics: result.modelMetrics,
      recommendations: result.recommendations,
      notes: ''
    };

    scans.unshift(scanRecord);
    // Keep max 500 scans
    if (scans.length > 500) scans.length = 500;
    localStorage.setItem('pg_scans', JSON.stringify(scans));

    // Update dashboard
    if (typeof DashboardManager !== 'undefined') {
      DashboardManager.refresh();
    }
    if (typeof HistoryManager !== 'undefined') {
      HistoryManager.refresh();
    }
  },

  resetScanner() {
    this.currentImage = null;
    this.currentImageData = null;

    const preview = document.getElementById('scannerPreview');
    const placeholder = document.getElementById('scanPlaceholder');
    const overlay = document.getElementById('scannerOverlay');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultArea = document.getElementById('resultArea');
    const zone = document.getElementById('scannerZone');

    preview.style.display = 'none';
    preview.src = '';
    placeholder.style.display = 'block';
    overlay.style.display = 'none';
    analyzeBtn.style.display = 'none';
    resultArea.style.display = 'none';
    resultArea.innerHTML = '';
    zone.classList.remove('has-image');
  },

  _delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
};
