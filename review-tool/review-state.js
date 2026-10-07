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

  function suggestionMap(record, manifest) {
    if (!record || record.schemaVersion !== 1 || !Array.isArray(record.proposals)) {
      throw new Error('Unsupported proposal file');
    }
    const known = new Map(manifest.filter(row => row.task === 'quality').map(row => [row.id, row]));
    const result = {};
    for (const proposal of record.proposals) {
      if (!proposal || !known.has(proposal.id) || result[proposal.id]) throw new Error('Proposal IDs must be unique known quality records');
      if (proposal.status !== 'unverified-model-proposal' || proposal.humanReviewRequired !== true) {
        throw new Error('Proposal file must require human review');
      }
      if (proposal.proposedLabel !== null && !LABELS.quality.includes(proposal.proposedLabel)) {
        throw new Error('Proposal contains an incompatible quality label');
      }
      if (![proposal.confidence, proposal.reviewPriority].every(value =>
        typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 1)) {
        throw new Error('Proposal confidence values must be between zero and one');
      }
      if (typeof proposal.modelSha256 !== 'string' || !/^[a-f0-9]{64}$/i.test(proposal.modelSha256)) {
        throw new Error('Proposal model checksum is invalid');
      }
      result[proposal.id] = { ...proposal };
    }
    return result;
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

  return { LABELS, validateDraft, mergeDrafts, progress, suggestionMap, csv };
});
