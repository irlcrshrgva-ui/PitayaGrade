Warning: truncated output (original token count: 7184)
Total output lines: 627

/* =============================================
   PitayaGrade - YOLOv8 ONNX Inference Module
   Runs the trained YOLOv8n model via onnxruntime-web.
   Replaces the HSV color heuristic with real model inference.

   Input  : HTMLImageElement at any resolution
   Output : { isDragonFruit, grade, confidence, inferenceMs }
   ============================================= */

const ModelInference = {
  session: null,
  sessions: {},
  loadingPromises: {},
  isLoaded: false,
  isLoading: false,

  ASSET_BASE: new URL('.', document.querySelector('script[src$="ort.min.js"]').src).href,
  CONF_THRESHOLD: 0.30,
  MODELS: PitayaModelRegistry.map(model => ({ ...model, classes: Array.from(model.classes) })),
  selectedModelId: 'efficientnet-b3-quality',
  selectedDiseaseModelId: 'yolov8n-disease-seg',
  OBJECT_GATE_THRESHOLD: 0.25,

  _isGradeModel(model) {
    return model && ['integrated-detector-grader', 'quality-classifier'].includes(model.role);
  },

  _isPresenceModel(model) {
    return Boolean(model && model.role === 'object-presence-gate');
  },

  canSelectModel(model) {
    return Boolean(model && model.available && model.selectable !== false && this._isGradeModel(model));
  },

  _isDiseaseModel(model) {
    return model && model.role === 'disease-segmenter';
  },

  canSelectDiseaseModel(model) {
    return Boolean(model && model.available && this._isDiseaseModel(model));
  },

  getAvailableModels() {
    return this.MODELS.filter(model => this.canSelectModel(model));
  },

  getModelCatalog() {
    return this.MODELS.slice();
  },

  getDiseaseModelCatalog() {
    return this.MODELS.filter(model => this._isDiseaseModel(model));
  },

  getSelectedDiseaseModel() {
    return this.MODELS.find(model => this.canSelectDiseaseModel(model) && model.id === this.selectedDiseaseModelId) || null;
  },

  getSelectedModel() {
    return this.MODELS.find(model => this.canSelectModel(model) && model.id === this.selectedModelId) ||
      this.getAvailableModels()[0];
  },

  selectModel(modelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectModel(candidate));
    if (!model) return false;
    this.selectedModelId = model.id;
    this.session = this.sessions[model.id] || null;
    this.isLoaded = Boolean(this.session);
    return true;
  },

  selectDiseaseModel(modelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectDiseaseModel(candidate));
    if (!model) return false;
    this.selectedDiseaseModelId = model.id;
    return true;
  },

  // ── Load the selected model once, then reuse its session ───────────────────
  async load(modelId = this.selectedModelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && candidate.available);
    if (!model) return false;
    if (this.sessions[model.id]) {
      this.session = this.sessions[model.id];
      this.isLoaded = true;
      return true;
    }
    if (this.loadingPromises[model.id]) return this.loadingPromises[model.id];
    this.isLoading = true;
    this.loadingPromise = this._load(model);
    this.loadingPromises[model.id] = this.loadingPromise;
    return this.loadingPromise;
  },

  async loadDisease(modelId = this.selectedDiseaseModelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectDiseaseModel(candidate));
    if (!model) return false;
    if (this.sessions[model.id]) return true;
    if (this.loadingPromises[model.id]) return this.loadingPromises[model.id];
    this.isLoading = true;
    const promise = this._load(model);
    this.loadingPromises[model.id] = promise;
    return promise;
  },

  async _load(model) {
    try {
      // Point ORT to the WASM files bundled in www/
      ort.env.wasm.wasmPaths = this.ASSET_BASE;
      ort.env.wasm.numThreads = 1;

      const session = await ort.InferenceSession.create(this.ASSET_BASE + model.modelPath, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all',
      });

      this.sessions[model.id] = session;
      if (this._isGradeModel(model)) {
        this.session = session;
        this.isLoaded = true;
      }
      console.log('[ModelInference] ' + model.name + ' loaded. Inputs:', session.inputNames, 'Outputs:', session.outputNames);
    } catch (err) {
      console.error('[ModelInference] Failed to load model:', err);
      if (this._isGradeModel(model)) this.isLoaded = false;
    }
    delete this.loadingPromises[model.id];
    this.isLoading = false;
    return Boolean(this.sessions[model.id]);
  },

  // ── Preprocess image using the selected model's registry contract ─────────
  _preprocess(imgElement, model) {
    const S = model.inputSize;
    const canvas = document.createElement('canvas');
    canvas.width  = S;
    canvas.height = S;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(imgElement, 0, 0, S, S);
    const { data } = ctx.getImageData(0, 0, S, S);

    const tensor = new Float32Array(3 * S * S);
    const stride = S * S;
    const imagenet = model.preprocessing === 'rgb-imagenet-normalized';
    if (!imagenet && model.preprocessing !== 'rgb-zero-to-one') {
      throw new Error('Unsupported preprocessing contract');
    }
    const means = [0.485, 0.456, 0.406];
    const deviations = [0.229, 0.224, 0.225];
    for (let i = 0; i < stride; i++) {
      for (let channel = 0; channel < 3; channel++) {
        let value = data[i * 4 + channel] / 255.0;
        if (imagenet) value = (value - means[channel]) / deviations[channel];
        tensor[channel * stride + i] = value;
      }
    }
    return new ort.Tensor('float32', tensor, [1, 3, S, S]);
  },

  // ── Postprocess a verified registry output contract ──────────────────────
  _postprocess(outputTensor, model = this.getSelectedModel(), confidenceThreshold = this.CONF_THRESHOLD) {
    if (model.outputContract === 'binary-presence-logits-v1') {
      return this._postprocessPresence(outputTensor, model, confidenceThreshold);
    }
    if (model.outputContract === 'quality-softmax-v1') {
      return this._postprocessQuality(outputTensor, model, confidenceThreshold);
    }
    if (model.outputContract === 'yolov8-grade-detection-v1') {
      return this._postprocessGradeDetection(outputTensor, model, confidenceThreshold);
    }
    if (model.outputContract === 'yolov8-fruit-detection-v1') {
      return this._postprocessFruitDetection(outputTensor, model, confidenceThreshold);
    }
    throw new Error('Unsupported model output contract');
  },

  _postprocessPresence(outputTensor, model, confidenceThreshold = model.threshold) {
    const dims = Array.from(outputTensor.dims || []);
    const values = Array.from(outputTensor.data || []);
    const validShape = (dims.length === 1 && dims[0] === 2) ||
      (dims.length === 2 && dims[0] === 1 && dims[1] === 2);
    if (!validShape || values.length !== 2 || !values.every(Number.isFinite)) {
      throw new Error('Unsupported presence-gate output shape');
    }
    const maximum = Math.max(...values);
    const exponentials = values.map(value => Math.exp(value - maximum));
    const denominator = exponentials[0] + exponentials[1];
    const nonFruitProbability = exponentials[0] / denominator;
    const dragonFruitProbability = exponentials[1] / denominator;
    const threshold = Number.isFinite(confidenceThreshold) ? confidenceThreshold : model.threshold;
    return {
      isDragonFruit: dragonFruitProbability >= threshold && dragonFruitProbability > nonFruitProbability,
      grade: null,
      confidence: dragonFruitProbability,
      nonFruitProbability,
      presenceGate: true
    };
  },

  // Classifier exports may contain probabilities or raw logits. The result is
  // explicitly marked classification-only because it has no localization box.
  _postprocessQuality(outputTensor, model, confidenceThreshold = this.CONF_THRESHOLD) {
    const dims = Array.from(outputTensor.dims || []);
    const values = Array.from(outputTensor.data || []);
    const validShape = (dims.length === 1 && dims[0] === model.classes.length) ||
      (dims.length === 2 && dims[0] === 1 && dims[1] === model.classes.length);
    if (!validShape || values.length !== model.classes.length || !values.every(Number.isFinite)) {
      throw new Error('Unsupported quality classifier output shape');
    }
    const total = values.reduce((sum, value) => sum + value, 0);
    const alreadyProbabilities = values.every(value => value >= 0 && value <= 1) &&
      Math.abs(total - 1) < 0.001;
    const probabilities = alreadyProbabilities ? values : (() => {
      const maximum = Math.max(...values);
      const exponentials = values.map(value => Math.exp(value - maximum));
      const denominator = exponentials.reduce((sum, value) => sum + value, 0);
      return exponentials.map(value => value / denominator);
    })();
    const bestIndex = probabilities.reduce((best, value, index) =>
      value > probabilities[best] ? index : best, 0);
    const confidence = probabilities[bestIndex];
    return {
      isDragonFruit: confidence >= confidenceThreshold,
      grade: confidence >= confidenceThreshold ? model.classes[bestIndex] : null,
      confidence,
      classificationOnly: true
    };
  },

  // ── Postprocess YOLOv8 output → best detection ────────────────────────────
  // YOLOv8n output shape: [1, 4+numClasses, 8400]
  //   dim 0..3  : x_c, y_c, w, h  (normalised to INPUT_SIZE)
  //   dim 4..7  : class scores (Grade A, B, C, Reject)
  _postprocessGradeDetection(outputTensor, model, confidenceThreshold = this.CONF_THRESHOLD) {
    const data  = outputTensor.data;
    if (outputTensor.dims.length !== 3 || outputTensor.dims[1] !== 4 + model.classes.length) {
      throw new Error('Unsupported YOLO output shape');
    }
    const nDet  = outputTensor.dims[2];
    const nCls  = model.classes.length;

    let bestConf = 0;
    let bestCls  = -1;
    let bestIndex = -1;

    for (let i = 0; i < nDet; i++) {
      let maxCls  = 0;
      let maxConf = 0;
      for (let c = 0; c < nCls; c++) {
        const score = data[(4 + c) * nDet + i];
        if (score > maxConf) { maxConf = score; maxCls = c; }
      }
      if (maxConf > bestConf) { bestConf = maxConf; bestCls = maxCls; bestIndex = i; }
    }

    if (bestCls === -1 || bestConf < confidenceThreshold) {
      return { isDragonFruit: false, grade: null, confidence: bestConf };
    }

    return {
      isDragonFruit: true,
      grade:         model.classes[bestCls],
      confidence:    bestConf,
      box: {
        x: Math.max(0, (data[bestIndex] - data[2 * nDet + bestIndex] / 2) / model.inputSize),
        y: Math.max(0, (data[nDet + bestIndex] - data[3 * nDet + bestIndex] / 2) / model.inputSize),
        right: Math.min(1, (data[bestIndex] + data[2 * nDet + bestIndex] / 2) / model.inputSize),
        bottom: Math.min(1, (data[nDet + bestIndex] + data[3 * nDet + bestIndex] / 2) / model.inputSize)
      },
    };
  },

  _postprocessFruitDetection(outputTensor, model, confidenceThreshold = model.threshold) {
    const dims = Array.from(outputTensor.dims || []);
    const data = outputTensor.data || [];
    if (dims.length !== 3 || dims[0] !== 1 || dims[1] !== 5 || dims[2] < 1 || data.length !== 5 * dims[2]) {
      throw new Error('Unsupported single-class fruit detector output shape');
    }
    const count = dims[2];
    let bestIndex = -1;
    let bestConfidence = 0;
    for (let i = 0; i < count; i++) {
      const confidence = data[4 * count + i];
      if (Number.isFinite(confidence) && c…1184 tokens truncated…let x = left; x < right; x++) {
          const normalizedX = (x + 0.5) / maskWidth;
          const normalizedY = (y + 0.5) / maskHeight;
          let covered = false;
          for (const candidate of retained) {
            if (normalizedX < candidate.box.x || normalizedX > candidate.box.right ||
                normalizedY < candidate.box.y || normalizedY > candidate.box.bottom) continue;
            let logit = 0;
            for (let channel = 0; channel < maskChannels; channel++) {
              const coefficient = detection.data[(4 + model.classes.length + channel) * count + candidate.index];
              logit += coefficient * prototypes.data[channel * maskHeight * maskWidth + y * maskWidth + x];
            }
            if (logit >= 0) { covered = true; break; }
          }
          if (covered) positive++;
          total++;
        }
      }
      areaPercent = total ? positive / total * 100 : null;
    }
    return {
      name: className,
      confidence: bestConfidence,
      isHealthy: false,
      areaPercent,
      severityMeasured: Number.isFinite(areaPercent),
      analysisMethod: 'YOLOv8 disease segmentation ONNX'
    };
  },

  async _inferSingle(imgElement, model, confidenceThreshold) {
    if (!model || !await this.load(model.id)) return null;
    const t0 = performance.now();
    const session = this.sessions[model.id];
    let inputTensor;
    let results;
    try {
      inputTensor = this._preprocess(imgElement, model);
      results = await session.run({ [session.inputNames[0]]: inputTensor });
      const output = results[session.outputNames[0]];
      const parsed = this._postprocess(output, model, confidenceThreshold);
      parsed.inferenceMs = Math.round(performance.now() - t0);
      parsed.modelId = model.id;
      parsed.modelName = model.name;
      parsed.requiresVisualGate = model.requiresVisualGate !== false;
      parsed.confidenceThreshold = confidenceThreshold;
      return parsed;
    } catch (err) {
      console.error('[ModelInference] Inference failed:', err);
      return null;
    } finally {
      if (inputTensor) inputTensor.dispose();
      if (results) Object.values(results).forEach(tensor => tensor.dispose());
    }
  },

  _cropToBox(imgElement, box) {
    if (!box || ![box.x, box.y, box.right, box.bottom].every(Number.isFinite) ||
        box.x < 0 || box.y < 0 || box.right > 1 || box.bottom > 1 ||
        box.right <= box.x || box.bottom <= box.y) return null;
    const width = imgElement.naturalWidth || imgElement.videoWidth || imgElement.width;
    const height = imgElement.naturalHeight || imgElement.videoHeight || imgElement.height;
    if (!width || !height) return null;
    const padding = 0.04;
    const left = Math.max(0, box.x - padding);
    const top = Math.max(0, box.y - padding);
    const right = Math.min(1, box.right + padding);
    const bottom = Math.min(1, box.bottom + padding);
    const sx = Math.floor(left * width);
    const sy = Math.floor(top * height);
    const sw = Math.max(1, Math.ceil((right - left) * width));
    const sh = Math.max(1, Math.ceil((bottom - top) * height));
    const crop = document.createElement('canvas');
    crop.width = sw;
    crop.height = sh;
    crop.getContext('2d').drawImage(imgElement, sx, sy, sw, sh, 0, 0, sw, sh);
    return crop;
  },

  // Quality classifiers use the fruit gate and locator to guard closed-set
  // grading. Full-frame graders use a verified full photo rather than a crop;
  // ordinary crop graders retain the localized-crop route.
  async infer(imgElement, modelId = this.selectedModelId, confidenceThreshold = this.CONF_THRESHOLD,
    { allowPhotoRecovery = false } = {}) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectModel(candidate));
    if (!model) return null;
    const threshold = Number.isFinite(confidenceThreshold)
      ? Math.max(0, Math.min(1, confidenceThreshold)) : this.CONF_THRESHOLD;
    const presenceGate = this.MODELS.find(candidate => candidate.available && this._isPresenceModel(candidate));
    const presence = presenceGate
      ? await this._inferSingle(imgElement, presenceGate, presenceGate.threshold)
      : null;
    if (!presence) return null;
    // A wider frame can dilute the fruit signal. Allow localization when the
    // scene score is borderline, then require stronger evidence on the crop.
    if (!presence.isDragonFruit && presence.confidence < 0.25) {
      return {
        isDragonFruit: false,
        grade: null,
        confidence: presence.confidence,
        nonFruitProbability: presence.nonFruitProbability,
        confidenceThreshold: presenceGate.threshold,
        detectionConfidence: presence.confidence,
        detectionThreshold: presenceGate.threshold,
        modelId: model.id,
        requestedModelId: model.id,
        rejectionReason: 'The full image scored too low for dragon fruit. Move closer and center one fruit.',
        modelName: `${presenceGate.name} → non-dragon-fruit (grading skipped)`,
        gradingSkipped: true,
        requiresVisualGate: true
      };
    }
    // The v7 EfficientNetB3 checkpoint was trained and evaluated on complete
    // fruit photos. When the full-frame presence gate confirms fruit, grade
    // the same full frame instead of feeding it a detector crop (a different
    // image domain). Ambiguous scenes still need YOLO localization plus crop
    // verification below before the full-frame grade is accepted.
    const fullFrameGrader = model.inferenceMode === 'full-frame-when-fruit-verified';
    if (fullFrameGrader && presence.isDragonFruit) {
      const classification = await this._inferSingle(imgElement, model, 0);
      if (!classification) return null;
      return {
        ...classification,
        modelId: model.id,
        requestedModelId: model.id,
        presenceConfidence: presence.confidence,
        classificationInput: 'full-frame',
        modelName: `${presenceGate.name} + ${model.name} (full-frame grade)`,
        requiresVisualGate: true
      };
    }
    const detector = model.role === 'integrated-detector-grader' ? model
      : this.MODELS.find(candidate => candidate.id === 'yolov8-fruit-locator-negative-aware' && candidate.available);
    if (!detector) return null;
    const gateThreshold = Math.max(threshold, this.OBJECT_GATE_THRESHOLD);
    const recoveryConfidence = model.photoRecoveryGradeConfidence;
    const allowRecovery = allowPhotoRecovery && Number.isFinite(recoveryConfidence) &&
      gateThreshold === this.OBJECT_GATE_THRESHOLD && presence.isDragonFruit && presence.confidence >= .9;
    const locationThreshold = allowRecovery ? .25 : gateThreshold;
    const detection = await this._inferSingle(imgElement, detector, locationThreshold);
    if (!detection) return null;
    if (!detection.isDragonFruit || !detection.box) {
      return {
        ...detection,
        isDragonFruit: false,
        grade: null,
        modelId: model.id,
        requestedModelId: model.id,
        modelName: `${detector.name} object gate → ${model.name} (grading skipped)`,
        gradingSkipped: true,
        detectionConfidence: detection.confidence,
        detectionThreshold: gateThreshold,
        rejectionReason: 'The detector could not locate a fruit confidently. Center the fruit and keep its outline in view.',
        presenceConfidence: presence.confidence,
        requiresVisualGate: true
      };
    }

    const crop = this._cropToBox(imgElement, detection.box);
    const recovered = allowRecovery && detection.confidence < gateThreshold;
    // Scene context must not stand in for the object itself. Recheck the
    // localized crop with the independently trained binary presence gate.
    const cropThreshold = recovered ? .95
      : presence.isDragonFruit ? presenceGate.threshold : Math.max(presenceGate.threshold, 0.85);
    const cropPresence = crop ? await this._inferSingle(crop, presenceGate, cropThreshold) : null;
    if (crop && !cropPresence) return null;
    if (!cropPresence?.isDragonFruit) {
      return {
        isDragonFruit: false, grade: null,
        confidence: cropPresence?.confidence || 0,
        confidenceThreshold: cropThreshold,
        detectionConfidence: cropPresence?.confidence || 0,
        detectionThreshold: cropThreshold,
        rejectionReason: 'The detected crop could not be verified as dragon fruit. Try a clear photo with the whole fruit visible.',
        modelId: model.id, requestedModelId: model.id,
        modelName: `${presenceGate.name} object crop → verification failed (grading skipped)`,
        gradingSkipped: true, requiresVisualGate: true
      };
    }
    if (model.role === 'integrated-detector-grader' && !model.cropGraderId) {
      return {
        ...detection, presenceConfidence: presence.confidence,
        cropPresenceConfidence: cropPresence.confidence,
        detectionConfidence: detection.confidence, detectionThreshold: gateThreshold,
        modelName: `${presenceGate.name} + ${detector.name}`,
        requiresVisualGate: true
      };
    }
    // Object presence is already established by the detector. A four-class
    // softmax score is grade confidence, not object confidence, so it must not
    // turn a detected fruit into "No Dragon Fruit" merely because no grade is
    // above the user's object-detection threshold.
    const cropGrader = model.cropGraderId
      ? this.MODELS.find(candidate => candidate.id === model.cropGraderId && candidate.available)
      : model;
    if (!cropGrader) return null;
    const classificationImage = fullFrameGrader ? imgElement : crop;
    const classification = await this._inferSingle(classificationImage, cropGrader, 0);
    if (!classification) return null;
    if (recovered && !(classification.confidence >= recoveryConfidence)) {
      return {
        isDragonFruit: false, grade: null, detectionConfidence: detection.confidence, detectionThreshold: gateThreshold,
        rejectionReason: 'A possible fruit was found. Move closer and center it for a reliable grade.',
        requiresVisualGate: true
      };
    }
    return {
      ...classification,
      box: detection.box,
      detectionConfidence: detection.confidence,
      detectionThreshold: recovered ? locationThreshold : gateThreshold,
      presenceConfidence: presence.confidence,
      cropPresenceConfidence: cropPresence.confidence,
      classificationInput: fullFrameGrader ? 'full-frame-after-object-verification' : 'detector-crop',
      modelName: `${presenceGate.name} + ${detector.name} + ${cropGrader.name}` +
        (fullFrameGrader ? ' (full-frame grade)' : ''),
      requiresVisualGate: true
    };
  },

  async inferDisease(imgElement, modelId = this.selectedDiseaseModelId, fruitBox = null) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectDiseaseModel(candidate));
    if (!model || !await this.loadDisease(model.id)) return null;
    const started = performance.now();
    const session = this.sessions[model.id];
    let inputTensor;
    let results;
    try {
      inputTensor = this._preprocess(imgElement, model);
      results = await session.run({ [session.inputNames[0]]: inputTensor });
      const parsed = this._postprocessDisease(results, model, fruitBox);
      if (!parsed) return null;
      parsed.inferenceMs = Math.round(performance.now() - started);
      parsed.modelId = model.id;
      parsed.modelName = model.name;
      return parsed;
    } catch (error) {
      console.error('[ModelInference] Disease inference failed:', error);
      return null;
    } finally {
      if (inputTensor) inputTensor.dispose();
      if (results) Object.values(results).forEach(tensor => tensor.dispose());
    }
  },
};

