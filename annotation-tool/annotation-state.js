(function(root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.PitayaAnnotationState = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';

  const SYMPTOMS = ['Anthracnose', 'Stem Canker', 'Soft Rot', 'Pest Damage', 'Sunburn', 'Fungal Spots'];

  function point(value) {
    if (!Array.isArray(value) || value.length !== 2 || value.some(number =>
      typeof number !== 'number' || !Number.isFinite(number) || number < 0 || number > 1)) {
      throw new Error('Each polygon vertex must be a normalized x/y pair.');
    }
    return value.map(number => Math.round(number * 1e6) / 1e6);
  }

  function cross(a, b, c) {
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  }

  function intersects(a, b, c, d) {
    const values = [cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)];
    if (values[0] * values[1] < 0 && values[2] * values[3] < 0) return true;
    const cases = [[a, b, c, values[0]], [a, b, d, values[1]], [c, d, a, values[2]], [c, d, b, values[3]]];
    return cases.some(([start, end, candidate, value]) => Math.abs(value) < 1e-12 &&
      [0, 1].every(axis => Math.min(start[axis], end[axis]) <= candidate[axis] &&
        candidate[axis] <= Math.max(start[axis], end[axis])));
  }

  function polygonError(raw) {
    if (!Array.isArray(raw) || raw.length < 3) return 'A polygon needs at least three points.';
    let points;
    try { points = raw.map(point); } catch (error) { return error.message; }
    if (new Set(points.map(item => item.join(','))).size !== points.length) return 'A polygon has repeated points.';
    const area = points.reduce((sum, item, index) => {
      const next = points[(index + 1) % points.length];
      return sum + item[0] * next[1] - next[0] * item[1];
    }, 0);
    if (Math.abs(area) < 1e-12) return 'A polygon cannot have zero area.';
    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        if (j === i + 1 || (i === 0 && j === points.length - 1)) continue;
        if (intersects(points[i], points[(i + 1) % points.length],
          points[j], points[(j + 1) % points.length])) return 'A polygon cannot cross itself.';
      }
    }
    return null;
  }

  function manifest(value) {
    if (!Array.isArray(value) || !value.length) throw new Error('Annotation manifest must be a non-empty JSON array.');
    const ids = new Set();
    return value.map((row, index) => {
      if (!row || typeof row !== 'object' || Array.isArray(row)) throw new Error(`Row ${index + 1} is invalid.`);
      for (const key of ['id', 'image', 'candidateSplit']) {
        if (typeof row[key] !== 'string' || !row[key].trim()) throw new Error(`${row.id || `Row ${index + 1}`}: missing ${key}.`);
      }
      if (ids.has(row.id)) throw new Error(`Duplicate record ID: ${row.id}`);
      ids.add(row.id);
      if (!['train', 'val', 'test'].includes(row.candidateSplit)) throw new Error(`${row.id}: invalid candidate split.`);
      return { ...row };
    });
  }

  function completed(row, draft, reviewer, reviewedAt) {
    if (!draft || typeof draft !== 'object') throw new Error('No annotation draft is available.');
    if (typeof reviewer !== 'string' || !reviewer.trim()) throw new Error('Enter the human reviewer ID.');
    const healthy = draft.reviewedLabel === 'Healthy';
    const regions = Array.isArray(draft.regions) ? draft.regions.map(region => {
      if (!region || !SYMPTOMS.includes(region.label)) throw new Error('Choose a supported symptom for every polygon.');
      const error = polygonError(region.polygon);
      if (error) throw new Error(error);
      return { label: region.label, polygon: region.polygon.map(point) };
    }) : [];
    if (healthy && regions.length) throw new Error('Healthy records cannot contain symptom polygons.');
    if (!healthy && !regions.length) throw new Error('Draw at least one polygon or mark the crop Healthy.');
    if (!healthy && !SYMPTOMS.includes(draft.reviewedLabel)) throw new Error('Choose the primary reviewed symptom.');
    if (!healthy && !regions.some(region => region.label === draft.reviewedLabel)) {
      throw new Error('The primary symptom must match one of the saved polygons.');
    }
    return {
      ...row,
      task: 'disease',
      imageRole: 'fruit-roi',
      roiSourceId: row.roiSourceId || row.id,
      annotationsComplete: true,
      annotationReviewer: reviewer.trim(),
      annotationReviewedAt: reviewedAt,
      reviewer: reviewer.trim(),
      reviewedAt,
      reviewedLabel: healthy ? 'Healthy' : draft.reviewedLabel,
      maskCoordinateSpace: 'upright',
      regions
    };
  }

  function merge(rows, drafts) {
    return rows.map(row => drafts[row.id] ? completed(row, drafts[row.id],
      drafts[row.id].annotationReviewer, drafts[row.id].annotationReviewedAt) : row);
  }

  function isComplete(row) {
    return row && row.annotationsComplete === true && typeof row.annotationReviewer === 'string' &&
      row.annotationReviewer.trim() && typeof row.annotationReviewedAt === 'string' &&
      (row.reviewedLabel === 'Healthy' ? Array.isArray(row.regions) && row.regions.length === 0 :
        SYMPTOMS.includes(row.reviewedLabel) && Array.isArray(row.regions) && row.regions.length > 0);
  }

  return { SYMPTOMS, point, polygonError, manifest, completed, merge, isComplete };
});
