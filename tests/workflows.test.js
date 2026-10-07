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

test('unrecognized results do not invent classifier confidence or save a grade', () => {
  const a = app();
  a.element('resultArea').scrollIntoView = () => {};
  const result = a.Scanner._buildRejectionResult(['No detection above the threshold']);
  a.Scanner._displayResult(result);
  a.Scanner._saveScan(result);
  assert.match(a.element('resultArea').innerHTML, /No grading confidence is available/);
  assert.doesNotMatch(a.element('resultArea').innerHTML, /99\.4%/);
  assert.equal(a.ScanStore.getScans().length, 0);
});

test('history treats saved fields as text and never renders stored recommendation markup', () => {
  const a = app();
  const record = scan();
  record.disease.name = '<img src=x onerror=alert(1)>';
  record.disease.isHealthy = false;
  record.details.size = '<script>bad</script>';
  record.grade.class = 'grade-a" onmouseover="bad';
  record.thumbnail = 'x" onerror="bad';
  record.recommendations = [{text: '<b>advice</b>', type: 'red" onclick="bad', icon: '<svg onload="bad"></svg>'}];
  record.notes = 'Keep <my> notes';
  record.details.processingTime = '<img src=x onerror=alert(1)>';
  a.ScanStore.saveScans([record]);
  const before = a.data.get('pg_scans');
  a.HistoryManager.refresh();
  a.HistoryManager.showDetail(record.id);
  a.DashboardManager._renderRecentScans(a.ScanStore.getScans());
  for (const id of ['historyList', 'modalBody', 'dashRecentScans']) {
    const html = a.element(id).innerHTML;
    assert.doesNotMatch(html, /<script>|<img src=x|onerror="bad|onmouseover="bad|<svg onload/);
  }
  assert.match(a.element('modalBody').innerHTML, /&lt;script&gt;bad&lt;\/script&gt;/);
  assert.match(a.element('dashRecentScans').innerHTML, /&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.match(a.element('modalBody').innerHTML, /&lt;b&gt;advice&lt;\/b&gt;/);
  assert.match(a.element('modalBody').innerHTML, /Keep &lt;my&gt; notes/);
  assert.equal(a.data.get('pg_scans'), before);
});
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
test('report disease names and size fields cannot introduce markup', () => {
  const a = app(); a.element('reportFrom').value = a.element('reportTo').value = a.ScanStore.localDate();
  const record = scan();
  record.disease = {name: '<img src=x onerror=alert(1)>', confidence: .8, isHealthy: false};
  record.details.size = '<script>bad()</script>';
  a.ScanStore.saveScans([record]); a.ReportsManager.generateReport();
  const html = a.element('reportPreviewArea').innerHTML;
  assert.ok(!html.includes('<img src=x'));
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
});
test('recommendations distinguish estimates from confirmed findings', () => {
  const a = app(); const recs = a.Scanner._getRecommendations('Grade A', 'Anthracnose', 'Harvestable');
  const text = recs.map(r => r.text).join(' ');
  assert.match(text, /Possible Anthracnose/);
  assert.match(text, /Confirm ripeness/);
  assert.ok(!text.includes('Ideal for export'));
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
  assert.equal(result.details.size, 'Not measured');
  assert.equal(result.details.imageCoveragePercent, 25);
  assert.equal(result.grade.analysisMethod, 'ONNX grade detector');
  assert.equal(result.disease.analysisMethod, 'HSV color heuristic');
  assert.match(result.details.processingMode, /^Local/);
  assert.doesNotMatch(result.details.modelUsed, /EfficientNet|TFLite|Cloud/);
  assert.ok(result.disease.symptoms.every(text => !/confirmed|verified/.test(text)));
  const segmented = a.Scanner._generateResult({ isDragonFruit: true, grade: 'Grade B', confidence: .8,
    box: { x: .25, y: .25, right: .75, bottom: .75 }, inferenceMs: 20, modelName:'YOLOv8-Nano' }, pixels,
    { name:'Anthracnose', confidence:.9, isHealthy:false, areaPercent:null,
      severityMeasured:false, analysisMethod:'YOLOv8 disease segmentation ONNX',
      inferenceMs:30, modelName:'YOLOv8-Nano Disease Segmentation' });
  assert.equal(segmented.grade.label, 'Grade B');
  assert.equal(segmented.disease.analysisMethod, 'YOLOv8 disease segmentation ONNX');
  assert.equal(segmented.disease.severityMeasured, false);
  assert.match(segmented.details.modelUsed, /Disease Segmentation.*ONNX/);
  assert.equal(a.Scanner._modelROI({ x: 0, y: 0, right: 0, bottom: 0 }, 8, 8), null);
});
test('scan metadata stays local regardless of the offline preference', () => {
  const a = app();
  const pixels = { width: 128, height: 128, data: new Uint8ClampedArray(128 * 128 * 4).fill(100) };
  const detection = { isDragonFruit: true, grade: 'Grade A', confidence: .9,
    box: { x: .1, y: .1, right: .9, bottom: .9 }, inferenceMs: 20, modelName: 'YOLOv8-Nano' };
  for (const offlineMode of [false, true]) {
    a.PitayaApp.settings.offlineMode = offlineMode;
    const result = a.Scanner._generateResult(detection, pixels);
    assert.match(result.details.processingMode, /^Local/);
    assert.equal(result.details.size, 'Not measured');
    const rejected = a.Scanner._buildRejectionResult([]);
    assert.match(rejected.details.processingMode, /^Local/);
    assert.equal(rejected.details.modelUsed, 'No grade assigned');
  }
  const advice = a.Scanner._getRecommendations('Grade A', 'Healthy', 'Developing', false);
  assert.ok(advice.some(item => item.text.startsWith('The image heuristic assigned')));
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

function nativeReports(a, plugin) {
  a.window.Capacitor = { isNativePlatform: () => true, getPlatform: () => 'android',
    isPluginAvailable: name => name === 'ReportExport', registerPlugin: () => plugin };
  a.element('reportFrom').value = a.element('reportTo').value = a.ScanStore.localDate();
  const record = scan(); record.notes = '=SUM(1,2)\nPreserve this note';
  a.ScanStore.saveScans([record]);
}

test('Android CSV uses the save dialog and preserves CSV escaping', async () => {
  const a = app(); let saved;
  nativeReports(a, { saveCsv: async options => { saved = options; return { cancelled: false }; } });
  const original = a.data.get('pg_scans');
  await a.ReportsManager.exportCSV();
  assert.match(saved.filename, /^PitayaGrade_Report_\d{4}-\d{2}-\d{2}\.csv$/);
  assert.ok(saved.data.startsWith('\uFEFF'));
  assert.ok(saved.data.includes('"\'=SUM(1,2)\nPreserve this note"'));
  assert.equal(a.messages.at(-1), 'CSV exported successfully');
  assert.equal(a.element('exportCSVBtn').disabled, false);
  assert.equal(a.data.get('pg_scans'), original);
});

test('plain-script Android bridge uses its injected plugin without an npm JS bundle', async () => {
  const a = app(); let called = false;
  nativeReports(a, {});
  delete a.window.Capacitor.registerPlugin;
  a.window.Capacitor.Plugins = { ReportExport: { saveCsv: async () => {
    called = true; return { cancelled: false };
  } } };
  await a.ReportsManager.exportCSV();
  assert.equal(called, true);
});

test('Android cancellation is quiet and failed exports can be retried', async () => {
  const a = app();
  nativeReports(a, { saveCsv: async () => ({ cancelled: true }) });
  await a.ReportsManager.exportCSV();
  assert.equal(a.messages.length, 0);
  nativeReports(a, { saveCsv: async () => { throw new Error('disk full'); } });
  await a.ReportsManager.exportCSV();
  assert.match(a.messages.at(-1), /could not be exported/);
  assert.equal(a.ReportsManager.exporting, false);
  assert.equal(a.element('exportCSVBtn').disabled, false);
});

test('repeated export taps open only one Android destination picker', async () => {
  const a = app(); let calls = 0, finish;
  nativeReports(a, { saveCsv: () => { calls++; return new Promise(resolve => { finish = resolve; }); } });
  const first = a.ReportsManager.exportCSV();
  await a.ReportsManager.exportCSV();
  assert.equal(calls, 1);
  assert.equal(a.element('exportCSVBtn').disabled, true);
  finish({ cancelled: true });
  await first;
});

test('Android print receives the report only and does not claim job completion', async () => {
  const a = app(); let printed;
  nativeReports(a, { printHtml: async options => { printed = options.html; } });
  a.element('printableReport').innerHTML = '<h2>Test report</h2>';
  a.window.open = () => { throw new Error('Android must not open a browser popup'); };
  await a.ReportsManager.printReport();
  assert.match(printed, /<h2>Test report<\/h2>/);
  assert.equal(a.messages.length, 0);
});

test('missing native plugin and print failures produce actionable messages', async () => {
  const a = app();
  nativeReports(a, { printHtml: async () => { throw new Error('no print service'); } });
  await a.ReportsManager.printReport();
  assert.match(a.messages.at(-1), /Printing is unavailable/);
  a.window.Capacitor.isPluginAvailable = () => false;
  await a.ReportsManager.exportCSV();
  assert.match(a.messages.at(-1), /could not be exported/);
});
