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
      (scan.notes == null || typeof scan.notes === 'string');
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

  clear() {
    localStorage.removeItem('pg_scans');
    this.warnings.delete('pg_scans');
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
