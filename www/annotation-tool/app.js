(function() {
  'use strict';
  const state = window.PitayaAnnotationState;
  const $ = id => document.getElementById(id);
  const elements = Object.fromEntries(['status','manifestFile','imageFolder','reviewer','confirmCrop','excludeCrop','cropStatus','regionLabel','primaryLabel',
    'undoPoint','closeRegion','removeRegion','clearRecord','markHealthy','saveRecord','recordSummary','progressText',
    'progress','canvas','canvasMessage','recordId','split','imagePath','regionCount','previous','position','next',
    'exportDraft','restoreFile','exportFinal','toast'].map(id => [id, $(id)]));
  const context = elements.canvas.getContext('2d');
  let rows = [], drafts = {}, files = new Map(), index = 0, points = [], regions = [], cropDecision = '', bitmap = null;
  const colors = ['#55efb2','#f83f83','#ffd85a','#73b7ff','#d293ff','#ff9955'];

  state.SYMPTOMS.forEach(label => {
    elements.regionLabel.append(new Option(label, label));
    elements.primaryLabel.append(new Option(label, label));
  });

  function toast(message) {
    elements.toast.textContent = message;
    elements.toast.classList.add('show');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => elements.toast.classList.remove('show'), 2600);
  }

  function normalizePath(value) { return String(value || '').replace(/\\/g, '/').replace(/^\.\//, ''); }
  function findFile(row) {
    const wanted = normalizePath(row.image);
    return files.get(wanted) || [...files].find(([path]) => wanted.endsWith(path) || path.endsWith(wanted))?.[1] ||
      [...files.values()].find(file => file.name === wanted.split('/').pop());
  }

  async function readJson(file) {
    if (!file) throw new Error('Choose a JSON file.');
    return JSON.parse(await file.text());
  }

  function draftFor(row) {
    const saved = drafts[row.id] || (row.annotationsComplete ? row : null);
    return saved ? { reviewedLabel:saved.reviewedLabel, cropDecision:saved.excludedFromTraining ? 'excluded' :
      saved.cropReviewStatus === 'human-confirmed' ? 'confirmed' : saved.cropDecision || '', regions:(saved.regions || []).map(region =>
      ({ label:region.label, polygon:region.polygon.map(item => [...item]) })),
      annotationReviewer:saved.annotationReviewer, annotationReviewedAt:saved.annotationReviewedAt } :
      { reviewedLabel:'', cropDecision:'', regions:[] };
  }

  function draw() {
    context.clearRect(0, 0, elements.canvas.width, elements.canvas.height);
    if (bitmap) context.drawImage(bitmap, 0, 0, elements.canvas.width, elements.canvas.height);
    regions.forEach((region, regionIndex) => drawPolygon(region.polygon, colors[regionIndex % colors.length], true));
    if (points.length) drawPolygon(points, '#ffffff', false);
  }

  function drawPolygon(polygon, color, close) {
    context.save(); context.strokeStyle = color; context.fillStyle = color + '35'; context.lineWidth = 4;
    context.beginPath();
    polygon.forEach((item, pointIndex) => {
      const x = item[0] * elements.canvas.width, y = item[1] * elements.canvas.height;
      if (!pointIndex) context.moveTo(x, y); else context.lineTo(x, y);
    });
    if (close) { context.closePath(); context.fill(); }
    context.stroke();
    polygon.forEach(item => { context.beginPath(); context.arc(item[0] * elements.canvas.width,
      item[1] * elements.canvas.height, 6, 0, Math.PI * 2); context.fill(); });
    context.restore();
  }

  async function loadCurrentImage() {
    bitmap?.close?.(); bitmap = null;
    const row = rows[index], file = row && findFile(row);
    if (!file) { elements.canvasMessage.hidden = false; draw(); return; }
    try {
      bitmap = await createImageBitmap(file, { imageOrientation:'from-image' });
      elements.canvas.width = bitmap.width; elements.canvas.height = bitmap.height;
      elements.canvasMessage.hidden = true; draw();
    } catch (error) { elements.canvasMessage.hidden = false; toast('Could not decode this image.'); }
  }

  function update() {
    const row = rows[index];
    if (!row) {
      elements.recordId.textContent = elements.split.textContent = elements.imagePath.textContent = '—';
      elements.position.textContent = '0 of 0'; elements.recordSummary.textContent = 'No record loaded.'; return;
    }
    const draft = draftFor(row); points = []; regions = draft.regions; cropDecision = draft.cropDecision;
    elements.primaryLabel.value = draft.reviewedLabel || '';
    elements.reviewer.value ||= draft.annotationReviewer || '';
    elements.recordId.textContent = row.id; elements.split.textContent = row.candidateSplit;
    elements.imagePath.textContent = row.image; elements.regionCount.textContent = String(regions.length);
    elements.cropStatus.textContent = cropDecision === 'confirmed' ? 'Confirmed usable dragon-fruit crop' :
      cropDecision === 'excluded' ? 'Excluded from training' : 'Awaiting human crop confirmation';
    elements.position.textContent = `${index + 1} of ${rows.length}`;
    elements.recordSummary.textContent = draft.reviewedLabel ? `${draft.reviewedLabel}; ${regions.length} region(s)` : 'Not completed.';
    elements.previous.disabled = index === 0; elements.next.disabled = index >= rows.length - 1;
    const complete = rows.filter(item => state.isComplete(drafts[item.id] || item)).length;
    elements.progressText.textContent = `${complete} / ${rows.length} complete`;
    elements.progress.value = rows.length ? complete / rows.length * 100 : 0;
    elements.exportFinal.disabled = complete !== rows.length || !rows.length;
    elements.status.textContent = rows.length ? `${rows.length} records loaded · ${files.size} local images` : 'Load an annotation manifest to begin.';
    loadCurrentImage();
  }

  elements.manifestFile.addEventListener('change', async event => {
    try { rows = state.manifest(await readJson(event.target.files[0])); drafts = {}; index = 0; update(); toast('Annotation manifest loaded.'); }
    catch (error) { toast(error.message); }
  });
  elements.imageFolder.addEventListener('change', event => {
    files = new Map();
    for (const file of event.target.files) {
      const relative = normalizePath(file.webkitRelativePath || file.name);
      files.set(relative, file);
      const parts = relative.split('/');
      if (parts.length > 1) files.set(parts.slice(1).join('/'), file);
    }
    update(); toast(`${event.target.files.length} local files available.`);
  });
  elements.canvas.addEventListener('pointerdown', event => {
    if (!bitmap || cropDecision !== 'confirmed' || elements.primaryLabel.value === 'Healthy') return;
    const rect = elements.canvas.getBoundingClientRect();
    points.push(state.point([(event.clientX - rect.left) / rect.width, (event.clientY - rect.top) / rect.height])); draw();
  });
  elements.undoPoint.addEventListener('click', () => { points.pop(); draw(); });
  elements.closeRegion.addEventListener('click', () => {
    if (cropDecision !== 'confirmed') return toast('Confirm the fruit crop before drawing symptoms.');
    const error = state.polygonError(points); if (error) return toast(error);
    regions.push({ label:elements.regionLabel.value, polygon:points.map(item => [...item]) });
    points = []; elements.primaryLabel.value ||= regions[0].label; elements.regionCount.textContent = String(regions.length); draw();
  });
  elements.removeRegion.addEventListener('click', () => { regions.pop(); elements.regionCount.textContent = String(regions.length); draw(); });
  elements.clearRecord.addEventListener('click', () => { points = []; regions = []; cropDecision = ''; elements.primaryLabel.value = ''; delete drafts[rows[index]?.id]; update(); });
  elements.confirmCrop.addEventListener('click', () => { cropDecision = 'confirmed'; elements.cropStatus.textContent = 'Confirmed usable dragon-fruit crop'; });
  elements.excludeCrop.addEventListener('click', () => { cropDecision = 'excluded'; points = []; regions = []; elements.primaryLabel.value = ''; elements.cropStatus.textContent = 'Excluded from training'; draw(); });
  elements.markHealthy.addEventListener('click', () => { if (cropDecision !== 'confirmed') return toast('Confirm the fruit crop first.'); points = []; regions = []; elements.primaryLabel.value = 'Healthy'; draw(); });
  elements.saveRecord.addEventListener('click', () => {
    const row = rows[index]; if (!row) return toast('Load a manifest first.');
    try {
      const reviewedAt = new Date().toISOString();
      const result = state.completed(row, { reviewedLabel:elements.primaryLabel.value, regions, cropDecision }, elements.reviewer.value, reviewedAt);
      drafts[row.id] = result;
      const nextIncomplete = rows.findIndex((item, rowIndex) => rowIndex > index && !state.isComplete(drafts[item.id] || item));
      index = nextIncomplete >= 0 ? nextIncomplete : Math.min(index + 1, rows.length - 1); update(); toast('Annotation saved locally.');
    } catch (error) { toast(error.message); }
  });
  elements.previous.addEventListener('click', () => { if (index > 0) { index -= 1; update(); } });
  elements.next.addEventListener('click', () => { if (index < rows.length - 1) { index += 1; update(); } });
  document.addEventListener('keydown', event => {
    const target = event.target;
    if (target?.closest?.('input, select, textarea, button')) return;
    if (event.ctrlKey && event.key === 'Enter') {
      event.preventDefault(); elements.saveRecord.click(); return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key.toLowerCase() === 'h') {
      event.preventDefault(); elements.markHealthy.click();
    } else if (event.key === '[') {
      event.preventDefault(); elements.previous.click();
    } else if (event.key === ']') {
      event.preventDefault(); elements.next.click();
    }
  });

  function download(name, value) {
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + '\n'], {type:'application/json'}));
    link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }
  elements.exportDraft.addEventListener('click', () => download(`pitayagrade-annotation-draft-${new Date().toISOString().slice(0,10)}.json`,
    { schemaVersion:1, purpose:'human disease polygon annotation draft', manifestIds:rows.map(row => row.id), drafts }));
  elements.restoreFile.addEventListener('change', async event => {
    try {
      const backup = await readJson(event.target.files[0]);
      if (!backup || backup.schemaVersion !== 1 || !backup.drafts || !Array.isArray(backup.manifestIds) ||
          backup.manifestIds.join('\n') !== rows.map(row => row.id).join('\n')) throw new Error('Draft backup does not match the loaded manifest.');
      drafts = backup.drafts; update(); toast('Draft backup restored.');
    } catch (error) { toast(error.message); }
  });
  elements.exportFinal.addEventListener('click', () => {
    try {
      const merged = state.merge(rows, drafts);
      if (!merged.every(state.isComplete)) throw new Error('Complete every record before final export.');
      download(`pitayagrade-disease-annotations-${new Date().toISOString().slice(0,10)}.json`, merged);
    } catch (error) { toast(error.message); }
  });
})();
