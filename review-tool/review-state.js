(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.ReviewState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const LABELS = Object.freeze({
    quality: Object.freeze(['Grade A', 'Grade B', 'Grade C', 'Reject']),
    maturity: Object.freeze(['Mature Dragon Fruit', 'Immature Dragon Fruit'])
  });

  function validateDraft(draft, task) {
    const allowed = LABELS[task];
    if (!allowed) return 'Unsupported review task';
    if (!draft || !allowed.includes(draft.reviewedLabel)) return 'Select a valid reviewed label';
    if (!String(draft.reviewedSourceGroup || '').trim()) return 'Enter a source-fruit group';
    if (!String(draft.reviewer || '').trim()) return 'Enter an anonymous reviewer ID';
    const reviewedAt = new Date(draft.reviewedAt);
    if (!draft.reviewedAt || Number.isNaN(reviewedAt.valueOf()) ||
        !/(Z|[+-]\d\d:\d\d)$/.test(draft.reviewedAt)) return 'Use a timezone-aware review time';
    return null;
  }

  function mergeDrafts(manifest, drafts) {
    return manifest.map(row => {
      const draft = drafts[row.id];
      if (!draft) return { ...row };
      const error = validateDraft(draft, row.task);
      if (error) throw new Error(`${row.id}: ${error}`);
      for (const key of ['reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt']) {
        if (row[key] != null && row[key] !== '' && row[key] !== draft[key]) {
          throw new Error(`${row.id}: refusing to overwrite existing ${key}`);
        }
      }
      return { ...row, reviewedLabel: draft.reviewedLabel,
        reviewedSourceGroup: String(draft.reviewedSourceGroup).trim(),
        reviewer: String(draft.reviewer).trim(), reviewedAt: draft.reviewedAt };
    });
  }

  function progress(rows, drafts) {
    const reviewed = rows.filter(row => Boolean(row.reviewedLabel || drafts[row.id])).length;
    return { reviewed, total: rows.length, percent: rows.length ? Math.round(reviewed / rows.length * 100) : 0 };
  }

  function csv(rows) {
    const fields = ['id', 'image', 'candidateSplit', 'sourceDataset', 'sourceLabel',
      'reviewedLabel', 'reviewedSourceGroup', 'reviewer', 'reviewedAt'];
    const escape = value => {
      const text = String(value == null ? '' : value);
      return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    return [fields.join(','), ...rows.map(row => fields.map(field => escape(row[field])).join(','))].join('\r\n') + '\r\n';
  }

  return { LABELS, validateDraft, mergeDrafts, progress, csv };
});

