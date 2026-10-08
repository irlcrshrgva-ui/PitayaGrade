/* Shared access to the existing pg_scans and pg_settings local data. */
const ScanStore = {
  warnings: new Set(),

  read(key, fallback, validate = () => true, strict = false) {
    try {
      const raw = localStorage.getItem(key);
      if (raw === null) return fallback;
      const value = JSON.parse(raw);
      if (!validate(value)) throw new Error('Invalid stored data');
      return value;
    } catch (error) {
      this.warnings.add(key);
      if (strict) throw new Error('Stored data could not be read. Existing records were preserved.');
      return fallback;
    }
  },

  validScan(scan) {
    return scan && /^[\w-]+$/.test(String(scan.id)) && Number.isFinite(Date.parse(scan.timestamp)) &&
      ['Grade A', 'Grade B', 'Grade C', 'Reject'].includes(scan.grade?.label) &&
      Number.isFinite(scan.grade.confidence) && scan.grade.confidence >= 0 && scan.grade.confidence <= 1 &&
      typeof scan.disease?.name === 'string' && typeof scan.disease.isHealthy === 'boolean' &&
      Number.isFinite(scan.disease.confidence) && scan.disease.confidence >= 0 && scan.disease.confidence <= 1 &&
      scan.details && typeof scan.details === 'object' &&
      (scan.disease.symptoms == null || (Array.isArray(scan.disease.symptoms) && scan.disease.symptoms.every(s => typeof s === 'string'))) &&
      (scan.recommendations == null || (Array.isArray(scan.recommendations) && scan.recommendations.every(r => r && typeof r.text === 'string'))) &&
      (scan.notes == null || typeof scan.notes === 'string') && this.validReview(scan.review);
  },

  validReview(review) {
    if (review == null) return true;
    const grades = ['Grade A', 'Grade B', 'Grade C', 'Reject', 'Not Applicable', 'Unsure'];
    return review && typeof review === 'object' &&
      ['correct', 'incorrect', 'unsure'].includes(review.verdict) &&
      ['dragon-fruit', 'not-dragon-fruit', 'unsure'].includes(review.actualObject) &&
      grades.includes(review.actualGrade) &&
      typeof review.reviewer === 'string' && review.reviewer.trim().length > 0 && review.reviewer.length <= 100 &&
      typeof review.notes === 'string' && review.notes.length <= 500 &&
      Number.isFinite(Date.parse(review.reviewedAt)) &&
      (review.actualObject !== 'not-dragon-fruit' || review.actualGrade === 'Not Applicable');
  },

  validRejection(record) {
    return record && /^[\w-]+$/.test(String(record.id)) && Number.isFinite(Date.parse(record.timestamp)) &&
      Array.isArray(record.reasons) && record.reasons.length > 0 && record.reasons.every(reason => typeof reason === 'string') &&
      ['dragon-fruit', 'not-dragon-fruit', 'unsure'].includes(record.actualObject) &&
      typeof record.reviewer === 'string' && record.reviewer.trim().length > 0 && record.reviewer.length <= 100 &&
      typeof record.notes === 'string' && record.notes.length <= 500 && Number.isFinite(Date.parse(record.reviewedAt)) &&
      typeof record.model === 'string' && Number.isFinite(record.threshold) && record.threshold >= 0 && record.threshold <= 100 &&
      (record.thumbnail == null || typeof record.thumbnail === 'string');
  },

  getRejections(strict = false) {
    const records = this.read('pg_rejections', [], Array.isArray, strict);
    const valid = records.filter(record => this.validRejection(record));
    if (valid.length !== records.length) {
      this.warnings.add('pg_rejections');
      if (strict) throw new Error('Some rejection feedback is invalid. Existing feedback was preserved.');
    }
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  saveRejectionFeedback(result, values, thumbnail = '') {
    const record = {
      id: result?.id,
      timestamp: result?.timestamp,
      reasons: Array.isArray(result?.disease?.symptoms) ? result.disease.symptoms.slice(0, 10) : [],
      actualObject: String(values?.actualObject || ''),
      reviewer: String(values?.reviewer || '').trim(),
      notes: String(values?.notes || '').trim(),
      reviewedAt: new Date().toISOString(),
      model: String(values?.model || 'Unknown'),
      threshold: Number(values?.threshold),
      thumbnail
    };
    if (!this.validRejection(record)) {
      throw new Error('Choose the actual object and enter the reviewer before saving.');
    }
    const records = this.getRejections(true).filter(item => String(item.id) !== String(record.id));
    records.unshift(record);
    if (records.length > 200) records.length = 200;
    localStorage.setItem('pg_rejections', JSON.stringify(records));
    window.dispatchEvent(new Event('pg:rejections-changed'));
    return record;
  },

  getScans(strict = false) {
    const scans = this.read('pg_scans', [], Array.isArray, strict);
    const valid = scans.filter(scan => this.validScan(scan));
    if (valid.length !== scans.length) {
      this.warnings.add('pg_scans');
      if (strict) throw new Error('Some saved records are invalid. Existing records were preserved.');
    }
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  saveScans(scans) {
    if (!Array.isArray(scans) || !scans.every(scan => this.validScan(scan))) throw new Error('Invalid scan record');
    localStorage.setItem('pg_scans', JSON.stringify(scans));
    this.changed();
  },

  updateNotes(id, notes) {
    if (notes.length > 2000) throw new Error('Notes must contain at most 2,000 characters.');
    const scans = this.getScans(true);
    const scan = scans.find(item => String(item.id) === String(id));
    if (!scan) throw new Error('This record no longer exists.');
    scan.notes = notes;
    this.saveScans(scans);
  },

  updateReview(id, values) {
    const scans = this.getScans(true);
    const scan = scans.find(item => String(item.id) === String(id));
    if (!scan) throw new Error('This record no longer exists.');
    const actualObject = String(values?.actualObject || '');
    const review = {
      verdict: String(values?.verdict || ''),
      actualObject,
      actualGrade: actualObject === 'not-dragon-fruit'
        ? 'Not Applicable'
        : String(values?.actualGrade || ''),
      reviewer: String(values?.reviewer || '').trim(),
      notes: String(values?.notes || '').trim(),
      reviewedAt: new Date().toISOString()
    };
    if (!this.validReview(review)) {
      throw new Error('Complete the validation fields using the available options. Reviewer is required.');
    }
    scan.review = review;
    this.saveScans(scans);
    return review;
  },

  clear() {
    localStorage.removeItem('pg_scans');
    localStorage.removeItem('pg_rejections');
    this.warnings.delete('pg_scans');
    this.warnings.delete('pg_rejections');
    this.changed();
  },

  changed() { window.dispatchEvent(new Event('pg:scans-changed')); },

  localDate(date = new Date()) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  },

  escape(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }
};
