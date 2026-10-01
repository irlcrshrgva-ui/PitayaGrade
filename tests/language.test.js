const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
function setup() {
  const nodes = [];
  const confirmations = [];
  const context = { WeakMap, NodeFilter: {SHOW_TEXT: 4}, window: {confirm: message => {confirmations.push(message); return false;}},
    document: {body: {}, documentElement: {}, querySelectorAll: () => [],
      createTreeWalker: () => { let index = 0; return {nextNode: () => nodes[index++]}; } } };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/language.js'), 'utf8') + '\nthis.manager = LanguageManager;', context);
  const add = (text, protectedText = false) => {
    const node = {nodeValue: text, parentElement: {closest: () => protectedText}};
    nodes.push(node); return node;
  };
  return {manager: context.manager, add, confirmations};
}
test('switching languages restores English and preserves grades and notes', () => {
  const a = setup(); const heading = a.add('  Settings '), grade = a.add('Grade A'), note = a.add('Settings', true);
  a.manager.setLanguage('fil');
  assert.equal(heading.nodeValue, '  Mga Setting ');
  assert.equal(grade.nodeValue, 'Grade A'); assert.equal(note.nodeValue, 'Settings');
  a.manager.setLanguage('en'); assert.equal(heading.nodeValue, '  Settings ');
});
test('dynamic replacements use the new text instead of stale translations', () => {
  const a = setup(); const node = a.add('Settings');
  a.manager.setLanguage('fil'); node.nodeValue = 'History'; a.manager.apply();
  assert.equal(node.nodeValue, 'Kasaysayan');
  a.manager.setLanguage('en'); assert.equal(node.nodeValue, 'History');
});
test('unknown guidance falls back without removing information', () => {
  const a = setup(); a.manager.language = 'fil';
  assert.equal(a.manager.translate('Expert advice not yet translated'), 'Expert advice not yet translated');
});

test('assessment values translate without altering numeric estimates or stored grade labels', () => {
  const a = setup();
  const values = ['Harvestable Stage', '82% Readiness', 'Developing (43%)', 'Small (150-250g)', 'Grade A', 'Reject'];
  const nodes = values.map(value => a.add(value));
  a.manager.setLanguage('fil');
  assert.deepEqual(nodes.map(node => node.nodeValue), [
    'Yugto na maaari nang anihin', '82% Kahandaan', 'Umuunlad pa (43%)', 'Maliit (150-250g)', 'Grade A', 'Reject'
  ]);
  a.manager.setLanguage('en');
  assert.deepEqual(nodes.map(node => node.nodeValue), values);
});

test('chart labels and weekday locale follow the selected language without changing data', () => {
  const context = {LanguageManager: setup().manager};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../js/dashboard.js'), 'utf8') + '\nthis.dashboard = DashboardManager;', context);
  context.LanguageManager.language = 'fil';
  assert.equal(context.dashboard._text('No quality data yet'), 'Wala pang datos ng kalidad');
  assert.equal(context.dashboard._text('Grade A'), 'Grade A');
  assert.equal(context.dashboard._locale(), 'fil-PH');
  context.LanguageManager.language = 'en';
  assert.equal(context.dashboard._text('No quality data yet'), 'No quality data yet');
  assert.equal(context.dashboard._locale(), 'en-PH');
});

test('dynamic alert text preserves counts, grade categories and English originals', () => {
  const a = setup();
  const source = '12 scans saved. Grade A: 4, Grade B: 3, Grade C: 2, Reject: 3. 5 with image-based disease flags; these are estimates.';
  const summary = a.add(source), title = a.add('Session Summary'), time = a.add('2h ago');
  a.manager.setLanguage('fil');
  assert.equal(title.nodeValue, 'Buod ng Sesyon');
  assert.equal(time.nodeValue, '2 oras ang nakalipas');
  assert.equal(summary.nodeValue, '12 scan ang na-save. Grade A: 4, Grade B: 3, Grade C: 2, Reject: 3. 5 ang may palatandaan ng sakit batay sa larawan; mga tantiya lamang ang mga ito.');
  assert.equal(a.manager.translate('Possible Anthracnose'), 'Posibleng Anthracnose');
  assert.equal(a.manager.translate('91.5% confidence'), '91.5% kumpiyansa');
  a.manager.setLanguage('en');
  assert.equal(summary.nodeValue, source);
  assert.equal(time.nodeValue, '2h ago');
});

test('destructive confirmations use the selected language and preserve cancellation', () => {
  const a = setup(); a.manager.language = 'fil';
  assert.equal(a.manager.confirm('Delete this scan record?'), false);
  assert.equal(a.confirmations[0], 'Burahin ang rekord ng scan na ito?');
  a.manager.language = 'en';
  a.manager.confirm('Delete this scan record?');
  assert.equal(a.confirmations[1], 'Delete this scan record?');
});
