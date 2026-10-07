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
  selectedModelId: 'yolov8-nano',
  selectedDiseaseModelId: 'yolov8n-disease-seg',

  _isGradeModel(model) {
    return model && ['integrated-detector-grader', 'quality-classifier'].includes(model.role);
  },

  canSelectModel(model) {
    return Boolean(model && model.available && this._isGradeModel(model));
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
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectModel(candidate));
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
    if (model.outputContract === 'quality-softmax-v1') {
      return this._postprocessQuality(outputTensor, model, confidenceThreshold);
    }
    if (model.outputContract === 'yolov8-grade-detection-v1') {
      return this._postprocessGradeDetection(outputTensor, model, confidenceThreshold);
    }
    throw new Error('Unsupported model output contract');
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

  _postprocessDisease(outputs, model, fruitBox = null) {
    const tensors = Object.values(outputs || {});
    const prototypes = tensors.find(tensor => tensor.dims?.length === 4 && tensor.dims[0] === 1);
    const detection = tensors.find(tensor => tensor.dims?.length === 3 && tensor.dims[0] === 1);
    if (!prototypes || !detection) throw new Error('Unsupported disease segmentation outputs');
    const maskChannels = prototypes.dims[1];
    const maskHeight = prototypes.dims[2];
    const maskWidth = prototypes.dims[3];
    const expectedChannels = 4 + model.classes.length + maskChannels;
    if (detection.dims[1] !== expectedChannels || detection.dims[2] < 1 ||
        prototypes.data.length !== maskChannels * maskHeight * maskWidth) {
      throw new Error('Unsupported disease segmentation output shape');
    }

    const count = detection.dims[2];
    const candidates = [];
    for (let index = 0; index < count; index++) {
      let bestClass = -1;
      let bestConfidence = 0;
      for (let classIndex = 0; classIndex < model.classes.length; classIndex++) {
        const confidence = detection.data[(4 + classIndex) * count + index];
        if (confidence > bestConfidence) {
          bestConfidence = confidence;
          bestClass = classIndex;
        }
      }
      if (bestClass < 0 || bestConfidence < this.CONF_THRESHOLD) continue;
      const centerX = detection.data[index];
      const centerY = detection.data[count + index];
      const width = detection.data[2 * count + index];
      const height = detection.data[3 * count + index];
      const box = {
        x: Math.max(0, (centerX - width / 2) / model.inputSize),
        y: Math.max(0, (centerY - height / 2) / model.inputSize),
        right: Math.min(1, (centerX + width / 2) / model.inputSize),
        bottom: Math.min(1, (centerY + height / 2) / model.inputSize)
      };
      if (box.right > box.x && box.bottom > box.y) {
        candidates.push({ index, classIndex:bestClass, confidence:bestConfidence, box });
      }
    }
    if (!candidates.length) return null;
    candidates.sort((left, right) => right.confidence - left.confidence);
    const dominantClass = candidates[0].classIndex;
    const retained = [];
    for (const candidate of candidates.filter(item => item.classIndex === dominantClass)) {
      const overlaps = retained.some(other => {
        const left = Math.max(candidate.box.x, other.box.x);
        const top = Math.max(candidate.box.y, other.box.y);
        const right = Math.min(candidate.box.right, other.box.right);
        const bottom = Math.min(candidate.box.bottom, other.box.bottom);
        const intersection = Math.max(0, right - left) * Math.max(0, bottom - top);
        const candidateArea = (candidate.box.right - candidate.box.x) * (candidate.box.bottom - candidate.box.y);
        const otherArea = (other.box.right - other.box.x) * (other.box.bottom - other.box.y);
        return intersection / (candidateArea + otherArea - intersection) > 0.45;
      });
      if (!overlaps) retained.push(candidate);
    }

    const className = model.classes[dominantClass];
    const bestConfidence = retained[0].confidence;
    let areaPercent = null;
    if (fruitBox &&
        [fruitBox.x, fruitBox.y, fruitBox.right, fruitBox.bottom].every(Number.isFinite)) {
      const left = Math.max(0, Math.min(maskWidth, Math.floor(fruitBox.x * maskWidth)));
      const top = Math.max(0, Math.min(maskHeight, Math.floor(fruitBox.y * maskHeight)));
      const right = Math.max(left + 1, Math.min(maskWidth, Math.ceil(fruitBox.right * maskWidth)));
      const bottom = Math.max(top + 1, Math.min(maskHeight, Math.ceil(fruitBox.bottom * maskHeight)));
      let positive = 0;
      let total = 0;
      for (let y = top; y < bottom; y++) {
        for (let x = left; x < right; x++) {
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

  // ── Public: run full inference on an image element ────────────────────────
  async infer(imgElement, modelId = this.selectedModelId, confidenceThreshold = this.CONF_THRESHOLD) {
    const model = this.MODELS.find(candidate => candidate.id === modelId && this.canSelectModel(candidate));
    if (!model || !await this.load(model.id)) return null; // model unavailable — caller should fall back

    const t0 = performance.now();
    const session = this.sessions[model.id];

    let inputTensor;
    let results;
    try {
    inputTensor = this._preprocess(imgElement, model);
    const feeds = {};
    feeds[session.inputNames[0]] = inputTensor;

    results  = await session.run(feeds);
    const output   = results[session.outputNames[0]];
    const threshold = Number.isFinite(confidenceThreshold)
      ? Math.max(0, Math.min(1, confidenceThreshold)) : this.CONF_THRESHOLD;
    const parsed   = this._postprocess(output, model, threshold);

    parsed.inferenceMs = Math.round(performance.now() - t0);
    parsed.modelId = model.id;
    parsed.modelName = model.name;
    parsed.requiresVisualGate = model.requiresVisualGate !== false;
    parsed.confidenceThreshold = threshold;
    return parsed;
    } catch (err) {
      console.error('[ModelInference] Inference failed:', err);
      return null;
    } finally {
      if (inputTensor) inputTensor.dispose();
      if (results) Object.values(results).forEach(tensor => tensor.dispose());
    }
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
