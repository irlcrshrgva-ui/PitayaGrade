const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');

function app() {
  const data = new Map(), elements = new Map(), messages = [], events = [];
  const element = id => {
    if (!elements.has(id)) elements.set(id, { value: '', textContent: '', innerHTML: '', style: {},
      classList: { add() {}, remove() {} }, addEventListener() {} });
    return elements.get(id);
  };
  const context = { console, Date, URL, performance, setTimeout, clearTimeout, Event,
    localStorage: { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) },
    window: { dispatchEvent: event => events.push(event.type), open: () => null },
    document: { getElementById: element },
    ToastManager: { show: message => messages.push(message) },
    PitayaApp: { settings: { offlineMode: false } },
    confirm: () => true,
    requestAnimationFrame: () => 1, cancelAnimationFrame() {}
  };
  vm.createContext(context);
  for (const [file, name] of [['storage', 'ScanStore'], ['reports', 'ReportsManager'], ['history', 'HistoryManager'], ['dashboard', 'DashboardManager'], ['scanner', 'Scanner'], ['live-scanner', 'LiveScanner']]) {
    vm.runInContext(fs.readFileSync(path.join(root, 'js', file + '.js'), 'utf8') + `\nthis.${name} = ${name};`, context);
  }
  return { ...context, data, elements, messages, events, element, context };
}
function scan(id = 1, timestamp = new Date().toISOString()) {
  return { id, timestamp, grade: { label: 'Grade A', confidence: .9, class: 'grade-a' },
    disease: { name: 'Healthy', confidence: .8, isHealthy: true },
    details: { size: 'Medium', surfaceCondition: 'Smooth' }, maturity: { value: 20 }, notes: '' };
}
test('malformed storage cannot crash reads or be overwritten during an edit', () => {
  const a = app(); a.data.set('pg_scans', '{broken');
  assert.equal(a.ScanStore.getScans().length, 0);
  assert.throws(() => a.ScanStore.updateNotes(1, 'test'), /preserved/);
  assert.equal(a.data.get('pg_scans'), '{broken');
});
test('invalid rows are skipped for display but preserved on attempted mutation', () => {
  const a = app(); const raw = JSON.stringify([scan(), { id: 2 }]); a.data.set('pg_scans', raw);
  assert.equal(a.ScanStore.getScans().length, 1);
  assert.throws(() => a.ScanStore.getScans(true), /preserved/);
  assert.equal(a.data.get('pg_scans'), raw);
});
test('notes persist, participate in search, and notify related views', () => {
  const a = app(); a.ScanStore.saveScans([scan()]);
  a.ScanStore.updateNotes(1, 'North plot, inspect tomorrow');
  a.HistoryManager.searchQuery = 'north plot';
  assert.equal(a.HistoryManager._getFilteredScans().length, 1);
  assert.equal(a.ScanStore.getScans()[0].notes, 'North plot, inspect tomorrow');
  assert.equal(a.events.length, 2);
  assert.throws(() => a.ScanStore.updateNotes(1, 'a'.repeat(2001)), /2,000/);
});
test('quota failure preserves records and does not broadcast success', () => {
  const a = app(); a.data.set('pg_scans', JSON.stringify([scan()]));
  a.localStorage.setItem = () => { throw new Error('QuotaExceededError'); };
  assert.throws(() => a.ScanStore.updateNotes(1, 'unsaved'), /Quota/);
  assert.equal(a.ScanStore.getScans()[0].notes, '');
  assert.equal(a.events.length, 0);
});
test('report date range includes the full last local day and excludes the next', () => {
  const a = app(); a.element('reportFrom').value = a.element('reportTo').value = '2026-09-14';
  a.ScanStore.saveScans([scan(1, new Date(2026, 8, 14, 23, 59, 59, 999).toISOString()), scan(2, new Date(2026, 8, 15).toISOString())]);
  assert.equal(a.ReportsManager._getFilteredScans().length, 1);
  assert.equal(a.ReportsManager._getFilteredScans()[0].id, 1);
});
test('invalid report dates clear stale preview and show validation', () => {
  const a = app(); a.element('reportPreviewArea').innerHTML = 'stale';
  a.element('reportFrom').value = '2026-09-15'; a.element('reportTo').value = '2026-09-14';
  assert.equal(a.ReportsManager._getFilteredScans(), null);
  assert.equal(a.element('reportPreviewArea').innerHTML, '');
  assert.match(a.messages[0], /valid date range/);
});
test('CSV preserves quotes and multiline notes and neutralizes formulas', () => {
  const a = app();
  assert.equal(a.ReportsManager._csvCell('A,"B"\nC'), '"A,""B""\nC"');
  assert.equal(a.ReportsManager._csvCell('=1+1'), '"\'=1+1"');
  assert.equal(a.ReportsManager._csvCell(null), '""');
});
test('blocked print is reported without a crash', () => {
  const a = app(); a.ReportsManager.printReport();
  assert.match(a.messages[0], /Printing is unavailable/);
});
test('report notes render as text, not executable markup', () => {
  const a = app(); a.element('reportFrom').value = a.element('reportTo').value = a.ScanStore.localDate();
  const record = scan(); record.notes = '<img src=x onerror=alert(1)>';
  a.ScanStore.saveScans([record]); a.ReportsManager.generateReport();
  assert.match(a.element('reportPreviewArea').innerHTML, /&lt;img/);
  assert.ok(!a.element('reportPreviewArea').innerHTML.includes('<img src=x'));
});
test('empty analytics reset totals and gauge uses saved maturity, not grade', () => {
  const a = app(); a.element('analyticsPremium').textContent = '90%';
  a.DashboardManager._updateStats([]);
  assert.equal(a.element('analyticsPremium').textContent, '0%');
  a.DashboardManager._updateGauge([scan()]);
  assert.equal(a.element('gaugeValue').textContent, '20%');
  a.DashboardManager._updateGauge([]);
  assert.equal(a.element('gaugeValue').textContent, '--%');
});
test('trained detection supplies ROI and is not rejected by color or filename heuristics', () => {
  const a = app(); const pixels = { width: 128, height: 128, data: new Uint8ClampedArray(128 * 128 * 4).fill(100) };
  a.Scanner.currentFileName = 'apple-orchard-dragon-fruit.jpg';
  const result = a.Scanner._generateResult({ isDragonFruit: true, grade: 'Grade B', confidence: .8,
    box: { x: .25, y: .25, right: .75, bottom: .75 }, inferenceMs: 20 }, pixels);
  assert.equal(result.grade.label, 'Grade B');
  assert.equal(result.isDragonFruit, true);
  assert.equal(result.modelMetrics, null);
  assert.equal(a.Scanner._modelROI({ x: 0, y: 0, right: 0, bottom: 0 }, 8, 8), null);
});
test('camera stream arriving after navigation is immediately released', async () => {
  const a = app(); let resolve, stopped = false;
  a.context.navigator = { mediaDevices: { getUserMedia: () => new Promise(r => { resolve = r; }) } };
  a.LiveScanner._resetHud = () => {};
  const start = a.LiveScanner.startCamera(); a.LiveScanner.stopCamera();
  resolve({ getTracks: () => [{ stop: () => { stopped = true; } }] });
  await start;
  assert.equal(stopped, true); assert.equal(a.LiveScanner.isActive, false);
});
test('photo failure always releases processing state', async () => {
  const a = app(); a.Scanner.currentImage = 'broken';
  a.element('processingOverlay').querySelectorAll = () => [];
  a.Scanner._extractPixelData = async () => { throw new Error('decode failed'); };
  await a.Scanner.analyze();
  assert.equal(a.Scanner.isProcessing, false);
  assert.match(a.messages[0], /Analysis failed/);
});
