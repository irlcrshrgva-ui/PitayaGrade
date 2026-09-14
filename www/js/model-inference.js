/* =============================================
   PitayaGrade - YOLOv8 ONNX Inference Module
   Runs the trained YOLOv8n model via onnxruntime-web.
   Replaces the HSV color heuristic with real model inference.

   Input  : HTMLImageElement at any resolution
   Output : { isDragonFruit, grade, confidence, inferenceMs }
   ============================================= */

const ModelInference = {
  session: null,
  isLoaded: false,
  isLoading: false,

  ASSET_BASE: new URL('.', document.querySelector('script[src$="ort.min.js"]').src).href,
  MODEL_PATH: 'model/best.onnx',
  INPUT_SIZE: 640,
  CONF_THRESHOLD: 0.30,
  CLASSES: ['Grade A', 'Grade B', 'Grade C', 'Reject'],

  // ── Load model (called once on first scan) ────────────────────────────────
  async load() {
    if (this.isLoaded) return true;
    if (this.isLoading) return this.loadingPromise;
    this.isLoading = true;
    this.loadingPromise = this._load();
    return this.loadingPromise;
  },

  async _load() {
    try {
      // Point ORT to the WASM files bundled in www/
      ort.env.wasm.wasmPaths = this.ASSET_BASE;
      ort.env.wasm.numThreads = 1;

      this.session = await ort.InferenceSession.create(this.ASSET_BASE + this.MODEL_PATH, {
        executionProviders: ['wasm'],
        graphOptimizationLevel: 'all',
      });

      this.isLoaded = true;
      console.log('[ModelInference] YOLOv8n loaded. Inputs:', this.session.inputNames, 'Outputs:', this.session.outputNames);
    } catch (err) {
      console.error('[ModelInference] Failed to load model:', err);
      this.isLoaded = false;
    }
    this.isLoading = false;
    return this.isLoaded;
  },

  // ── Preprocess image → Float32 tensor [1, 3, 640, 640] ───────────────────
  _preprocess(imgElement) {
    const S = this.INPUT_SIZE;
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
  _postprocess(outputTensor) {
    const data  = outputTensor.data;
    if (outputTensor.dims.length !== 3 || outputTensor.dims[1] !== 4 + this.CLASSES.length) {
      throw new Error('Unsupported YOLO output shape');
    }
    const nDet  = outputTensor.dims[2];
    const nCls  = this.CLASSES.length; // 4

    let bestConf = 0;
    let bestCls  = -1;

    for (let i = 0; i < nDet; i++) {
      let maxCls  = 0;
      let maxConf = 0;
      for (let c = 0; c < nCls; c++) {
        const score = data[(4 + c) * nDet + i];
        if (score > maxConf) { maxConf = score; maxCls = c; }
      }
      if (maxConf > bestConf) { bestConf = maxConf; bestCls = maxCls; }
    }

    if (bestCls === -1 || bestConf < this.CONF_THRESHOLD) {
      return { isDragonFruit: false, grade: null, confidence: bestConf };
    }

    return {
      isDragonFruit: true,
      grade:         this.CLASSES[bestCls],
      confidence:    bestConf,
    };
  },

  // ── Public: run full inference on an image element ────────────────────────
  async infer(imgElement) {
    const loaded = await this.load();
    if (!loaded) return null; // model unavailable — caller should fall back

    const t0 = performance.now();

    let inputTensor;
    let results;
    try {
    inputTensor = this._preprocess(imgElement);
    const feeds = {};
    feeds[this.session.inputNames[0]] = inputTensor;

    results  = await this.session.run(feeds);
    const output   = results[this.session.outputNames[0]];
    const parsed   = this._postprocess(output);

    parsed.inferenceMs = Math.round(performance.now() - t0);
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
