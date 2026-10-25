const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const state = require('../annotation-tool/annotation-state');
const server = require('../scripts/serve-review');

const row = { id:'disease:1', image:'dataset/fruit.png', candidateSplit:'train',
  fileSha256:'a'.repeat(64), pixelSha256:'b'.repeat(64), reviewedSourceGroup:'fruit-1' };

test('disease annotation polygons reject malformed evidence', () => {
  assert.equal(state.polygonError([[.1,.1],[.8,.1],[.8,.8],[.1,.8]]), null);
  assert.match(state.polygonError([[.1,.1],[.9,.9],[.1,.9],[.9,.1]]), /zero area|cross/);
  assert.match(state.polygonError([[.1,.1],[.2,.2]]), /three/);
  assert.match(state.polygonError([[.1,.1],[.8,.1],[2,.8]]), /normalized/);
});

test('disease annotation completion preserves explicit human evidence', () => {
  const result = state.completed(row, { reviewedLabel:'Sunburn', regions:[{
    label:'Sunburn', polygon:[[.1,.1],[.8,.1],[.8,.8],[.1,.8]]
  }] }, 'reviewer-01', '2026-10-25T10:00:00Z');
  assert.equal(result.imageRole, 'fruit-roi');
  assert.equal(result.maskCoordinateSpace, 'upright');
  assert.equal(result.annotationReviewer, 'reviewer-01');
  assert.equal(state.isComplete(result), true);
  assert.throws(() => state.completed(row, { reviewedLabel:'Healthy', regions:result.regions },
    'reviewer-01', '2026-10-25T10:00:00Z'), /Healthy/);
});

test('healthy annotation requires an explicit empty region list', () => {
  const result = state.completed(row, { reviewedLabel:'Healthy', regions:[] },
    'reviewer-02', '2026-10-25T10:00:00Z');
  assert.deepEqual(result.regions, []);
  assert.equal(state.isComplete(result), true);
});

test('annotation manifest rejects duplicates and invalid splits', () => {
  assert.equal(state.manifest([row]).length, 1);
  assert.throws(() => state.manifest([row, row]), /Duplicate/);
  assert.throws(() => state.manifest([{...row, candidateSplit:'validation'}]), /split/);
});

test('annotation browser app parses and is exposed by the local evidence server', () => {
  const root = path.join(__dirname, '..');
  const app = fs.readFileSync(path.join(root, 'annotation-tool', 'app.js'), 'utf8');
  const page = fs.readFileSync(path.join(root, 'annotation-tool', 'index.html'), 'utf8');
  assert.doesNotThrow(() => new vm.Script(app));
  assert.match(app, /document\.addEventListener\('keydown'/);
  assert.match(app, /event\.ctrlKey && event\.key === 'Enter'/);
  assert.match(page, /H marks Healthy, Ctrl\+Enter saves/);
  assert.ok(server.resolveRequestPath('/annotation-tool/index.html').endsWith(path.join('annotation-tool','index.html')));
  assert.equal(server.resolveRequestPath('/annotation-tool/%2e%2e/package.json'), null);
});

test('packaged annotation desk matches editable sources', () => {
  const root = path.join(__dirname, '..');
  for (const file of ['index.html','styles.css','annotation-state.js','app.js']) {
    assert.equal(fs.readFileSync(path.join(root, 'www', 'annotation-tool', file), 'utf8'),
      fs.readFileSync(path.join(root, 'annotation-tool', file), 'utf8'));
  }
});
