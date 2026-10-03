(async function () {
  const STORAGE = 'pitayagrade_review_drafts_v1';
  const els = Object.fromEntries(['status','task','filter','reviewer','sourceGroup','labels','save','clear',
    'progressText','progressPercent','progress','image','imageError','recordId','split','sourceLabel',
    'imagePath','previous','next','position','exportJson','exportCsv','backup','restore','toast']
    .map(id => [id, document.getElementById(id)]));
  let manifest = [], rows = [], index = 0;
  let drafts = readDrafts();

  function readDrafts() {
    try { const value = JSON.parse(localStorage.getItem(STORAGE) || '{}'); return value && typeof value === 'object' ? value : {}; }
    catch { return {}; }
  }
  function persist() { localStorage.setItem(STORAGE, JSON.stringify(drafts)); }
  function toast(message) { els.toast.textContent = message; els.toast.classList.add('show'); setTimeout(() => els.toast.classList.remove('show'), 2400); }
  function current() { return rows[index]; }
  function rebuild() {
    const taskRows = manifest.filter(row => row.task === els.task.value);
    if (els.filter.value === 'reviewed') rows = taskRows.filter(row => row.reviewedLabel || drafts[row.id]);
    else if (els.filter.value === 'unreviewed') rows = taskRows.filter(row => !row.reviewedLabel && !drafts[row.id]);
    else rows = taskRows;
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
    if (!row) { els.image.removeAttribute('src'); els.recordId.textContent = 'No matching records'; renderLabels(els.task.value); return; }
    const draft = drafts[row.id] || row;
    renderLabels(row.task, draft.reviewedLabel);
    els.sourceGroup.value = draft.reviewedSourceGroup || '';
    if (draft.reviewer) els.reviewer.value = draft.reviewer;
    els.recordId.textContent = row.id; els.split.textContent = row.candidateSplit;
    els.sourceLabel.textContent = row.sourceLabel || '—'; els.imagePath.textContent = row.image;
    els.imageError.hidden = true; els.image.hidden = false; els.image.src = '/' + row.image.replace(/^\/+/, '');
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
  els.clear.addEventListener('click', () => { const row=current(); if (!row || !drafts[row.id]) return; if (confirm('Clear this local draft review?')) { delete drafts[row.id]; persist(); rebuild(); } });
  els.image.addEventListener('error', () => { els.image.hidden = true; els.imageError.hidden = false; });
  els.reviewer.addEventListener('change', () => localStorage.setItem('pitayagrade_reviewer_id', els.reviewer.value));
  els.exportJson.addEventListener('click', () => { try { download(`pitayagrade-reviewed-${dateTag()}.json`, JSON.stringify(ReviewState.mergeDrafts(manifest,drafts),null,2)+'\n','application/json'); } catch(e) { toast(e.message); } });
  els.exportCsv.addEventListener('click', () => { try { const merged=ReviewState.mergeDrafts(manifest,drafts).filter(r=>r.task===els.task.value); download(`${els.task.value}-review-${dateTag()}.csv`,ReviewState.csv(merged),'text/csv'); } catch(e) { toast(e.message); } });
  els.backup.addEventListener('click', () => download(`review-draft-${dateTag()}.json`, JSON.stringify(drafts,null,2)+'\n','application/json'));
  els.restore.addEventListener('change', async () => { try { const value=JSON.parse(await els.restore.files[0].text()); if (!value || typeof value!=='object' || Array.isArray(value)) throw new Error('Invalid draft backup'); drafts=value; ReviewState.mergeDrafts(manifest,drafts); persist(); rebuild(); toast('Draft backup restored'); } catch(e) { toast(e.message); } finally { els.restore.value=''; } });

  try {
    const response = await fetch('/research/public-review-manifest.json', { cache:'no-store' });
    if (!response.ok) throw new Error(`Manifest request failed (${response.status})`);
    manifest = await response.json();
    if (!Array.isArray(manifest) || !manifest.length) throw new Error('Manifest is empty or invalid');
    els.reviewer.value = localStorage.getItem('pitayagrade_reviewer_id') || '';
    els.status.textContent = `${manifest.length.toLocaleString()} candidate records loaded locally`;
    rebuild();
  } catch (error) { els.status.textContent = error.message; els.status.style.color = '#ff9bad'; }
})();

