'use strict';
(() => {
  const el = id => document.getElementById(id);
  let session, report, photoUrl;
  const status = message => { el('status').textContent = message; };
  el('task').onchange = async () => {
    el('photo').disabled = el('analyze').disabled = true;
    el('results').replaceChildren();
    el('preview').hidden = true;
    el('photo').value = '';
    if (session) await session.release();
    session = report = null;
    el('load').disabled = false;
    el('model-status').textContent = 'Load the selected experimental model to begin.';
    el('evaluation').textContent = 'No model loaded.';
    status('Task changed.');
  };
  el('load').onclick = async () => {
    el('load').disabled = true;
    el('task').disabled = true;
    const task = el('task').value;
    try {
      status('Checking model and evaluation…');
      const [evaluation, model] = await Promise.all([
        fetch(`model/${task}/evaluation.json`), fetch(`model/${task}/classifier.onnx`)]);
      if (!evaluation.ok || !model.ok) throw new Error('No evaluated model is installed. Run the disease training workflow first.');
      report = await evaluation.json();
      const bytes = await model.arrayBuffer();
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)))
        .map(x => x.toString(16).padStart(2, '0')).join('');
      if (digest !== report.modelSha256 || report.task !== task || report.status !== 'experimental-evaluated-image-classifier' ||
          !Array.isArray(report.classes) || report.classes.length < 2 || report.preprocessing.size !== 160 ||
          !Number.isFinite(report.test?.metrics?.accuracy)) throw new Error('Model or evaluation contract mismatch.');
      ort.env.wasm.wasmPaths = './';
      session = await ort.InferenceSession.create(bytes, {executionProviders: ['wasm']});
      el('photo').disabled = false;
      el('task').disabled = false;
      el('model-status').textContent = 'Experimental MobileNetV3-small classifier · local inference';
      el('evaluation').textContent = `Held-out test: ${report.test.count} images; accuracy ${(100 * report.test.metrics.accuracy).toFixed(1)}%; macro F1 ${report.test.metrics['macro avg']['f1-score'].toFixed(3)}. Checkpoint selected by validation loss. These results apply to the source dataset split.`;
      status('Model verified. Choose a photo.');
    } catch (error) { status(error.message); el('load').disabled = false; el('task').disabled = false; }
  };
  el('photo').onchange = async () => {
    el('analyze').disabled = true;
    el('results').replaceChildren();
    el('preview').hidden = true;
    if (photoUrl) URL.revokeObjectURL(photoUrl);
    const file = el('photo').files[0];
    if (!file) return;
    photoUrl = URL.createObjectURL(file);
    el('preview').src = photoUrl;
    try {
      await el('preview').decode();
      el('preview').hidden = false;
      el('analyze').disabled = !session;
      status('Photo ready.');
    } catch { status('Unable to read this image. Choose another photo.'); }
  };
  el('analyze').onclick = async () => {
    el('analyze').disabled = true;
    el('task').disabled = true;
    el('results').replaceChildren();
    try {
      status('Analyzing locally…');
      const size = report.preprocessing.size;
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = size;
      const context = canvas.getContext('2d');
      context.drawImage(el('preview'), 0, 0, size, size);
      const rgba = context.getImageData(0, 0, size, size).data;
      const data = new Float32Array(3 * size * size);
      for (let c = 0; c < 3; c++) for (let i = 0; i < size * size; i++)
        data[c * size * size + i] = (rgba[i * 4 + c] / 255 - report.preprocessing.mean[c]) / report.preprocessing.std[c];
      const input = new ort.Tensor('float32', data, [1, 3, size, size]);
      let output, logits;
      try {
        output = await session.run({images: input});
        logits = Array.from(output.logits.data);
      } finally {
        input.dispose();
        if (output) Object.values(output).forEach(t => t.dispose());
      }
      if (logits.length !== report.classes.length || !logits.every(Number.isFinite)) throw new Error('Invalid classifier output.');
      const max = Math.max(...logits), values = logits.map(x => Math.exp(x - max));
      const total = values.reduce((a, b) => a + b, 0);
      values.map((v, i) => ({score: v / total, label: report.classes[i]}))
        .sort((a, b) => b.score - a.score).slice(0, 3).forEach(result => {
          const li = document.createElement('li');
          li.textContent = `${result.label.replaceAll('_', ' ')} — ${(100 * result.score).toFixed(1)}% model score`;
          el('results').append(li);
        });
      status('Experimental label predictions. This is not a diagnosis.');
    } catch (error) { status(error.message); }
    finally { el('analyze').disabled = false; el('task').disabled = false; }
  };
})();
