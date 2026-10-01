const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function setup(raw = '[]') {
  let saved = raw;
  const list = { innerHTML: '', textContent: '', appendChild() {} };
  const context = { Date, console, setTimeout() {}, clearTimeout() {},
    document: { getElementById: id => id === 'notifList' ? list : null,
      createElement: () => ({}) },
    localStorage: { getItem: () => saved, setItem: (_, v) => { saved = v; } } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(require('node:path').join(__dirname, '../js/notifications.js'), 'utf8') + '\nthis.manager = NotificationManager;', context);
  context.manager.load();
  return { context, manager: context.manager, list, saved: () => saved };
}
test('corrupt notification data survives additions and clear attempts', () => {
  const a = setup('{broken');
  assert.equal(a.manager.add({ title: 'test', body: 'body' }), null);
  assert.equal(a.manager.clearAll(), false);
  assert.equal(a.saved(), '{broken');
});
test('notification read state persists and storage failure leaves it unchanged', () => {
  const a = setup(); a.manager.add({ title: 'test', body: 'body' });
  assert.equal(a.manager.getUnreadCount(), 1);
  a.context.localStorage.setItem = () => { throw Error('quota'); };
  assert.equal(a.manager.markAllRead(), false);
  assert.equal(a.manager.getUnreadCount(), 1);
  assert.equal(JSON.parse(a.saved())[0].read, false);
});
test('saved notification content is escaped and read state survives reload', () => {
  const a = setup(); a.manager.add({ title: '<img onerror=alert(1)>', body: '<script>bad</script>' });
  assert.ok(!a.list.innerHTML.includes('<script>'));
  assert.ok(a.list.innerHTML.includes('&lt;script&gt;'));
  assert.equal(a.manager.markAllRead(), true);
  a.manager.load(); assert.equal(a.manager.getUnreadCount(), 0);
});
test('disease alerts identify estimates instead of confirmed diagnoses', () => {
  const a = setup();
  a.manager.generateScanAlert({ grade: { label: 'Grade B', confidence: .8 }, disease: { name: 'Anthracnose', confidence: .9 } });
  assert.equal(a.manager.notifications[0].title, 'Possible Anthracnose');
  assert.match(a.manager.notifications[0].body, /not a confirmed diagnosis/);
});

test('grade alerts require inspection before market or use decisions', () => {
  const a = setup();
  for (const label of ['Grade A', 'Reject']) {
    a.manager.generateScanAlert({grade: {label, confidence: .95}, disease: {name: 'Healthy'}});
    assert.match(a.manager.notifications[0].body, /95\.0% confidence/);
    assert.match(a.manager.notifications[0].body, /Verify/);
    assert.doesNotMatch(a.manager.notifications[0].body, /Ready for premium market|Remove from harvest batch/);
  }
});

test('disabling scan alerts preserves existing notifications', () => {
  const a = setup();
  a.manager.add({ title: 'Existing alert', body: 'Keep this' });
  a.context.PitayaApp = { settings: { scanAlerts: false } };
  a.manager.generateScanAlert({ grade: { label: 'Reject', confidence: .9 }, disease: { name: 'Soft Rot', confidence: .8 } });
  assert.equal(a.manager.notifications.length, 1);
  assert.equal(a.manager.notifications[0].title, 'Existing alert');
});

test('session grouping uses a fixed sixty-minute window', () => {
  const a = setup();
  const start = Date.parse('2026-09-19T10:00:00Z');
  const rows = [0, 59, 60, 75].map((minute, id) => ({id, timestamp: new Date(start + minute * 60000).toISOString()}));
  assert.deepEqual(Array.from(a.manager._latestSession(rows), r => r.id), [2, 3]);
});

test('completed session summary is saved once and includes the grade distribution', () => {
  const a = setup(); const values = new Map();
  a.context.localStorage = {getItem: k => values.get(k) ?? null, setItem: (k,v) => values.set(k,v)};
  a.context.ScanStore = {getScans: () => [{id: 1, timestamp: '2026-09-19T10:00:00Z', grade: {label: 'Grade B'}, disease: {name:'Healthy'}}]};
  a.manager.scheduleSessionSummary(Date.parse('2026-09-19T11:00:00Z'));
  a.manager.scheduleSessionSummary(Date.parse('2026-09-19T11:01:00Z'));
  assert.equal(a.manager.notifications.length, 1);
  assert.match(a.manager.notifications[0].body, /Grade B: 1/);
  a.manager.clearAll();
  a.manager.scheduleSessionSummary(Date.parse('2026-09-19T11:02:00Z'));
  assert.equal(a.manager.notifications.length, 0);
});
