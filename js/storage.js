/* Shared access to the existing pg_scans and pg_settings local data. */
const ScanStore = {
  warnings: new Set(),
  nativeDatabase: null,
  scanCache: null,
  rejectionCache: null,
  persistQueue: Promise.resolve(),

  async init() {
    const capacitor = window.Capacitor;
    if (!capacitor?.isNativePlatform?.() || capacitor.getPlatform?.() !== 'android') return;
    if (capacitor.isPluginAvailable && !capacitor.isPluginAvailable('PitayaGradeDatabase')) {
      this.warnings.add('native_database');
      return;
    }
    const plugin = capacitor.Plugins?.PitayaGradeDatabase || capacitor.registerPlugin?.('PitayaGradeDatabase');
    if (!plugin) return;
    this.nativeDatabase = plugin;
    try {
      const result = await plugin.loadAll();
      if (result?.initialized) {
        this.scanCache = this._validatedScans(result.scans || []);
        this.rejectionCache = this._validatedRejections(result.rejections || []);
        return;
      }

      // First launch after upgrade: move legacy browser records into SQLite.
      const oldScans = this._validatedScans(this.read('pg_scans', [], Array.isArray, true));
      const oldRejections = this._validatedRejections(this.read('pg_rejections', [], Array.isArray, true));
      if (this.warnings.has('pg_scans') || this.warnings.has('pg_rejections')) {
        throw new Error('Legacy scan data needs review before it can be migrated.');
      }
      await plugin.saveAll({ scans: oldScans, rejections: oldRejections });
      this.scanCache = oldScans;
      this.rejectionCache = oldRejections;
    } catch (error) {
      this.nativeDatabase = null;
      this.warnings.add('native_database');
      console.error('[ScanStore] SQLite initialization failed; retaining legacy records.', error);
    }
  },

  _validatedScans(scans) {
    const valid = Array.isArray(scans) ? scans.filter(scan => this.validScan(scan)) : [];
    if (Array.isArray(scans) && valid.length !== scans.length) this.warnings.add('pg_scans');
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  _validatedRejections(records) {
    const valid = Array.isArray(records) ? records.filter(record => this.validRejection(record)) : [];
    if (Array.isArray(records) && valid.length !== records.length) this.warnings.add('pg_rejections');
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  _persistNative() {
    if (!this.nativeDatabase) return;
    const scans = this.scanCache || [];
    const rejections = this.rejectionCache || [];
    this.persistQueue = this.persistQueue
      .catch(() => {})
      .then(() => this.nativeDatabase?.saveAll({ scans, rejections }))
      .catch(error => {
        this.warnings.add('native_database');
        console.error('[ScanStore] SQLite save failed.', error);
        throw error;
      });
    return this.persistQueue;
  },

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
      (record.skinColor == null || record.skinColor === '' ||
        (record.actualObject === 'dragon-fruit' && ['pink-red', 'yellow', 'other', 'unsure'].includes(record.skinColor))) &&
      typeof record.reviewer === 'string' && record.reviewer.trim().length > 0 && record.reviewer.length <= 100 &&
      typeof record.notes === 'string' && record.notes.length <= 500 && Number.isFinite(Date.parse(record.reviewedAt)) &&
      typeof record.model === 'string' && Number.isFinite(record.threshold) && record.threshold >= 0 && record.threshold <= 100 &&
      (record.thumbnail == null || typeof record.thumbnail === 'string');
  },

  getRejections(strict = false) {
    if (this.rejectionCache) return this.rejectionCache.map(record => JSON.parse(JSON.stringify(record)));
    const records = this.read('pg_rejections', [], Array.isArray, strict);
    const valid = records.filter(record => this.validRejection(record));
    if (valid.length !== records.length) {
      this.warnings.add('pg_rejections');
      if (strict) throw new Error('Some rejection feedback is invalid. Existing feedback was preserved.');
    }
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  async saveRejectionFeedback(result, values, thumbnail = '') {
    const record = {
      id: result?.id,
      timestamp: result?.timestamp,
      reasons: Array.isArray(result?.disease?.symptoms) ? result.disease.symptoms.slice(0, 10) : [],
      actualObject: String(values?.actualObject || ''),
      skinColor: String(values?.actualObject || '') === 'dragon-fruit' ? String(values?.skinColor || '') : '',
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
    const previous = this.rejectionCache;
    if (this.rejectionCache) this.rejectionCache = records;
    else localStorage.setItem('pg_rejections', JSON.stringify(records));
    try {
      await this._persistNative();
    } catch (error) {
      this.rejectionCache = previous;
      throw error;
    }
    window.dispatchEvent(new Event('pg:rejections-changed'));
    return record;
  },

  getScans(strict = false) {
    if (this.scanCache) return this.scanCache.map(scan => JSON.parse(JSON.stringify(scan)));
    const scans = this.read('pg_scans', [], Array.isArray, strict);
    const valid = scans.filter(scan => this.validScan(scan));
    if (valid.length !== scans.length) {
      this.warnings.add('pg_scans');
      if (strict) throw new Error('Some saved records are invalid. Existing records were preserved.');
    }
    return valid.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
  },

  async saveScans(scans) {
    if (!Array.isArray(scans) || !scans.every(scan => this.validScan(scan))) throw new Error('Invalid scan record');
    const previous = this.scanCache;
    if (this.scanCache) this.scanCache = this._validatedScans(scans);
    else localStorage.setItem('pg_scans', JSON.stringify(scans));
    try {
      await this._persistNative();
    } catch (error) {
      this.scanCache = previous;
      throw error;
    }
    this.changed();
  },

  async updateNotes(id, notes) {
    if (notes.length > 2000) throw new Error('Notes must contain at most 2,000 characters.');
    const scans = this.getScans(true);
    const scan = scans.find(item => String(item.id) === String(id));
    if (!scan) throw new Error('This record no longer exists.');
    scan.notes = notes;
    await this.saveScans(scans);
  },

  async updateReview(id, values) {
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
    await this.saveScans(scans);
    return review;
  },

  async clear() {
    if (this.nativeDatabase) {
      const previousScans = this.scanCache;
      const previousRejections = this.rejectionCache;
      this.scanCache = [];
      this.rejectionCache = [];
      try {
        await this._persistNative();
      } catch (error) {
        this.scanCache = previousScans;
        this.rejectionCache = previousRejections;
        throw error;
      }
    } else {
      localStorage.removeItem('pg_scans');
      localStorage.removeItem('pg_rejections');
    }
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
