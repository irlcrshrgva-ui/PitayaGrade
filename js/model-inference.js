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
  MODELS: [
    {
      id: 'yolov8-nano',
      name: 'YOLOv8-Nano',
      modelPath: 'model/best.onnx',
      inputSize: 640,
      classes: ['Grade A', 'Grade B', 'Grade C', 'Reject']
    }
  ],
  selectedModelId: 'yolov8-nano',

  getAvailableModels() {
    return this.MODELS.slice();
  },

  getSelectedModel() {
    return this.MODELS.find(model => model.id === this.selectedModelId) || this.MODELS[0];
  },

  selectModel(modelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId);
    if (!model) return false;
    this.selectedModelId = model.id;
    this.session = this.sessions[model.id] || null;
    this.isLoaded = Boolean(this.session);
    return true;
  },

  // ── Load the selected model once, then reuse its session ───────────────────
  async load(modelId = this.selectedModelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId);
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
      this.session = session;
      this.isLoaded = true;
      console.log('[ModelInference] ' + model.name + ' loaded. Inputs:', session.inputNames, 'Outputs:', session.outputNames);
    } catch (err) {
      console.error('[ModelInference] Failed to load model:', err);
      this.isLoaded = false;
    }
    delete this.loadingPromises[model.id];
    this.isLoading = false;
    return Boolean(this.sessions[model.id]);
  },

  // ── Preprocess image → Float32 tensor [1, 3, 640, 640] ───────────────────
  _preprocess(imgElement, inputSize) {
    const S = inputSize;
    const canvas = document.createElement('canvas');
    canvas.width  = S;
    canvas.height = S;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(imgElement, 0, 0, S, S);
    const { data } = ctx.getImageData(0, 0, S, S);

    const tensor = new Float32Array(3 * S * S);
    const stride = S * S;
    for (let i = 0; i < stride; i++) {
      tensor[i]            = data[i * 4]     / 255.0; // R
      tensor[stride + i]   = data[i * 4 + 1] / 255.0; // G
      tensor[stride*2 + i] = data[i * 4 + 2] / 255.0; // B
    }
    return new ort.Tensor('float32', tensor, [1, 3, S, S]);
  },

  // ── Postprocess YOLOv8 output → best detection ────────────────────────────
  // YOLOv8n output shape: [1, 4+numClasses, 8400]
  //   dim 0..3  : x_c, y_c, w, h  (normalised to INPUT_SIZE)
  //   dim 4..7  : class scores (Grade A, B, C, Reject)
  _postprocess(outputTensor, model) {
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

    if (bestCls === -1 || bestConf < this.CONF_THRESHOLD) {
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

  // ── Public: run full inference on an image element ────────────────────────
  async infer(imgElement, modelId = this.selectedModelId) {
    const model = this.MODELS.find(candidate => candidate.id === modelId);
    if (!model || !await this.load(model.id)) return null; // model unavailable — caller should fall back

    const t0 = performance.now();
    const session = this.sessions[model.id];

    let inputTensor;
    let results;
    try {
    inputTensor = this._preprocess(imgElement, model.inputSize);
    const feeds = {};
    feeds[session.inputNames[0]] = inputTensor;

    results  = await session.run(feeds);
    const output   = results[session.outputNames[0]];
    const parsed   = this._postprocess(output, model);

    parsed.inferenceMs = Math.round(performance.now() - t0);
    parsed.modelId = model.id;
    parsed.modelName = model.name;
    return parsed;
    } catch (err) {
      console.error('[ModelInference] Inference failed:', err);
      return null;
    } finally {
      if (inputTensor) inputTensor.dispose();
      if (results) Object.values(results).forEach(tensor => tensor.dispose());
    }
  },
};
