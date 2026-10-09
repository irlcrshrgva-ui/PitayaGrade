(async function () {
  const STORAGE = 'pitayagrade_review_drafts_v1';
  const els = Object.fromEntries(['status','task','filter','reviewer','sourceGroup','labels','save','clear',
    'progressText','progressPercent','progress','image','imageError','recordId','split','sourceLabel',
    'imagePath','previous','next','position','exportJson','exportCsv','backup','restore','proposalFile',
    'suggestionText','useSuggestion','groupProposalFile','sourceSuggestionText','useSourceSuggestion','toast',
    'datasetFolder','datasetStatus']
    .map(id => [id, document.getElementById(id)]));
  let manifest = [], rows = [], index = 0;
  let suggestions = {};
  let sourceSuggestions = {};
  let localImages = new Map();
  let activeImageUrl = '';
  let drafts = readDrafts();

  function readDrafts() {
    try { const value = JSON.parse(localStorage.getItem(STORAGE) || '{}'); return value && typeof value === 'object' ? value : {}; }
    catch { return {}; }
  }
  function persist() { localStorage.setItem(STORAGE, JSON.stringify(drafts)); }
  function toast(message) { els.toast.textContent = message; els.toast.classList.add('show'); setTimeout(() => els.toast.classList.remove('show'), 2400); }
  function current() { return rows[index]; }
  function normalizePath(value) { return String(value || '').replace(/\\/g, '/').replace(/^\/+/, ''); }
  function preparedRelative(value) { return normalizePath(value).replace(/^dataset\/public\/prepared\//, ''); }
  function registerLocalImages(files) {
    const candidates = new Map();
    for (const file of files) {
      if (!file.type.startsWith('image/')) continue;
      const parts = normalizePath(file.webkitRelativePath || file.name).split('/');
      for (let start = 0; start < parts.length; start += 1) {
        const key = parts.slice(start).join('/');
        if (!candidates.has(key)) candidates.set(key, file);
        else if (candidates.get(key) !== file) candidates.set(key, null);
      }
    }
    localImages = new Map(Array.from(candidates).filter(([, file]) => file));
    return new Set(localImages.values()).size;
  }
  function localImage(row) {
    const path = normalizePath(row?.image);
    return localImages.get(path) || localImages.get(preparedRelative(path)) || localImages.get(path.split('/').pop());
  }
  function displayImage(row) {
    if (activeImageUrl) { URL.revokeObjectURL(activeImageUrl); activeImageUrl = ''; }
    const local = localImage(row);
    if (local) {
      activeImageUrl = URL.createObjectURL(local);
      els.image.src = activeImageUrl;
      return;
    }
    els.image.src = new URL('../' + normalizePath(row.image), window.location.href).href;
  }
  function rebuild() {
    const taskRows = manifest.filter(row => row.task === els.task.value);
    if (els.filter.value === 'reviewed') rows = taskRows.filter(row => row.reviewedLabel || drafts[row.id]);
    else if (els.filter.value === 'unreviewed') rows = taskRows.filter(row => !row.reviewedLabel && !drafts[row.id]);
    else rows = taskRows;
    if (els.filter.value === 'priority') {
      rows = taskRows.filter(row => !row.reviewedLabel && !drafts[row.id]).sort((left, right) =>
        (suggestions[right.id]?.reviewPriority ?? -1) - (suggestions[left.id]?.reviewPriority ?? -1));
    }
    index = Math.min(index, Math.max(0, rows.length - 1));
    render();
  }
  function renderLabels(task, selected) {
    els.labels.innerHTML = '';
    for (const label of ReviewState.LABELS[task] || []) {
      const wrapper = document.createElement('label');
      const input = document.createElement('input');
      input.type = 'radio'; input.name = 'reviewedLabel'; input.value = label; input.checked = label === selected;
      wrapper.append(input, document.createTextNode(label)); els.labels.appendChild(wrapper);
    }
  }
  function render() {
    const taskRows = manifest.filter(row => row.task === els.task.value);
    const summary = ReviewState.progress(taskRows, drafts);
    els.progressText.textContent = `${summary.reviewed} / ${summary.total}`;
    els.progressPercent.textContent = `${summary.percent}%`; els.progress.value = summary.percent;
    const row = current();
    els.position.textContent = rows.length ? `${index + 1} of ${rows.length}` : '0 of 0';
    for (const button of [els.previous, els.next, els.save, els.clear]) button.disabled = !row;
    if (!row) { els.image.removeAttribute('src'); els.recordId.textContent = 'No matching records';
      els.suggestionText.textContent = 'No proposal for this view.'; els.useSuggestion.disabled = true;
      renderLabels(els.task.value); return; }
    const draft = drafts[row.id] || row;
    renderLabels(row.task, draft.reviewedLabel);
    els.sourceGroup.value = draft.reviewedSourceGroup || '';
    if (draft.reviewer) els.reviewer.value = draft.reviewer;
    els.recordId.textContent = row.id; els.split.textContent = row.candidateSplit;
    els.sourceLabel.textContent = row.sourceLabel || '—'; els.imagePath.textContent = row.image;
    const proposal = suggestions[row.id];
    els.useSuggestion.disabled = !proposal?.proposedLabel;
    els.suggestionText.textContent = proposal
      ? (proposal.proposedLabel
        ? `${proposal.proposedLabel} at ${(proposal.confidence * 100).toFixed(1)}% — confirm visually before saving.`
        : `No label reached the threshold (${(proposal.confidence * 100).toFixed(1)}% best confidence).`)
      : 'No model proposal loaded for this record.';
    const sourceProposal = sourceSuggestions[row.id];
    els.useSourceSuggestion.disabled = !sourceProposal;
    els.sourceSuggestionText.textContent = sourceProposal
      ? `${sourceProposal.suggestedSourceGroup} · ${sourceProposal.memberCount} visually similar records${sourceProposal.crossesCandidateSplits ? ' · crosses candidate splits' : ''}. Confirm the physical source before saving.`
      : 'No source-group suggestion loaded for this record.';
    els.imageError.hidden = true; els.image.hidden = false; displayImage(row);
  }
  function selectedLabel() { return document.querySelector('input[name="reviewedLabel"]:checked')?.value || ''; }
  function saveReview() {
    const row = current(); if (!row) return;
    const draft = { reviewedLabel:selectedLabel(), reviewedSourceGroup:els.sourceGroup.value,
      reviewer:els.reviewer.value, reviewedAt:new Date().toISOString() };
    const error = ReviewState.validateDraft(draft, row.task); if (error) return toast(error);
    drafts[row.id] = draft; persist(); toast('Review saved locally');
    if (els.filter.value === 'unreviewed') rebuild(); else { index = Math.min(index + 1, rows.length - 1); render(); }
  }
  function download(name, content, type) {
    const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([content], { type }));
    link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  }
  function dateTag() { return new Date().toISOString().slice(0,10); }

  els.task.addEventListener('change', () => { index = 0; rebuild(); }); els.filter.addEventListener('change', () => { index = 0; rebuild(); });
  els.previous.addEventListener('click', () => { index = Math.max(0, index - 1); render(); });
  els.next.addEventListener('click', () => { index = Math.min(rows.length - 1, index + 1); render(); });
  els.save.addEventListener('click', saveReview);
  els.useSuggestion.addEventListener('click', () => {
    const proposal = suggestions[current()?.id]; if (!proposal?.proposedLabel) return;
    const radio = Array.from(document.querySelectorAll('input[name="reviewedLabel"]'))
      .find(input => input.value === proposal.proposedLabel);
    if (radio) { radio.checked = true; toast('Proposal copied to the draft; review it before saving'); }
  });
  els.useSourceSuggestion.addEventListener('click', () => {
    const proposal = sourceSuggestions[current()?.id]; if (!proposal) return;
    els.sourceGroup.value = proposal.suggestedSourceGroup;
    toast('Source-group proposal copied to the draft; confirm the physical source before saving');
  });
  els.clear.addEventListener('click', () => { const row=current(); if (!row || !drafts[row.id]) return; if (confirm('Clear this local draft review?')) { delete drafts[row.id]; persist(); rebuild(); } });
  els.image.addEventListener('error', () => { els.image.hidden = true; els.imageError.hidden = false; });
  els.reviewer.addEventListener('change', () => localStorage.setItem('pitayagrade_reviewer_id', els.reviewer.value));
  els.datasetFolder.addEventListener('change', () => {
    const count = registerLocalImages(els.datasetFolder.files || []);
    els.datasetStatus.textContent = count
      ? `${count.toLocaleString()} local images available for this browser session.`
      : 'No supported images were found in that folder.';
    render();
    if (count) toast(`${count.toLocaleString()} local dataset images loaded`);
  });
  els.exportJson.addEventListener('click', () => { try { download(`pitayagrade-reviewed-${dateTag()}.json`, JSON.stringify(ReviewState.mergeDrafts(manifest,drafts),null,2)+'\n','application/json'); } catch(e) { toast(e.message); } });
  els.exportCsv.addEventListener('click', () => { try { const merged=ReviewState.mergeDrafts(manifest,drafts).filter(r=>r.task===els.task.value); download(`${els.task.value}-review-${dateTag()}.csv`,ReviewState.csv(merged),'text/csv'); } catch(e) { toast(e.message); } });
  els.backup.addEventListener('click', () => download(`review-draft-${dateTag()}.json`, JSON.stringify(drafts,null,2)+'\n','application/json'));
  els.proposalFile.addEventListener('change', async () => { try {
    const record = JSON.parse(await els.proposalFile.files[0].text());
    suggestions = ReviewState.suggestionMap(record, manifest); rebuild();
    toast(`${Object.keys(suggestions).length} unverified proposals loaded locally`);
  } catch(e) { toast(e.message); } finally { els.proposalFile.value=''; } });
  els.groupProposalFile.addEventListener('change', async () => { try {
    const record = JSON.parse(await els.groupProposalFile.files[0].text());
    sourceSuggestions = ReviewState.sourceSuggestionMap(record, manifest); render();
    toast(`${Object.keys(sourceSuggestions).length} source-group suggestions loaded locally`);
  } catch(e) { toast(e.message); } finally { els.groupProposalFile.value=''; } });
  els.restore.addEventListener('change', async () => { try { const value=JSON.parse(await els.restore.files[0].text()); if (!value || typeof value!=='object' || Array.isArray(value)) throw new Error('Invalid draft backup'); drafts=value; ReviewState.mergeDrafts(manifest,drafts); persist(); rebuild(); toast('Draft backup restored'); } catch(e) { toast(e.message); } finally { els.restore.value=''; } });

  try {
    const response = await fetch(new URL('../research/public-review-manifest.json', window.location.href), { cache:'no-store' });
    if (!response.ok) throw new Error(`Manifest request failed (${response.status})`);
    manifest = await response.json();
    if (!Array.isArray(manifest) || !manifest.length) throw new Error('Manifest is empty or invalid');
    els.reviewer.value = localStorage.getItem('pitayagrade_reviewer_id') || '';
    els.status.textContent = `${manifest.length.toLocaleString()} candidate records loaded`;
    try {
      const groupResponse = await fetch(new URL('../research/source-group-suggestions-2026-10-10.json', window.location.href), { cache:'no-store' });
      if (groupResponse.ok) sourceSuggestions = ReviewState.sourceSuggestionMap(await groupResponse.json(), manifest);
    } catch { /* Review remains usable without optional suggestions. */ }
    rebuild();
  } catch (error) { els.status.textContent = error.message; els.status.style.color = '#ff9bad'; }
})();
