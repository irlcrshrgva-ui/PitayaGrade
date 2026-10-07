const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const state = require('../review-tool/review-state');
const server = require('../scripts/serve-review');

test('visual review drafts require complete evidence', () => {
  const complete = { reviewedLabel:'Grade A', reviewedSourceGroup:'fruit-1', reviewer:'reviewer-1', reviewedAt:'2026-10-04T10:00:00+08:00' };
  assert.equal(state.validateDraft(complete, 'quality'), null);
  assert.match(state.validateDraft({ ...complete, reviewer:'' }, 'quality'), /reviewer/);
  assert.match(state.validateDraft({ ...complete, reviewedLabel:'Fresh' }, 'quality'), /label/);
});

test('visual review export preserves rows and refuses retained conflicts', () => {
  const manifest = [{ id:'one', task:'quality', reviewedLabel:null }];
  const draft = { one:{ reviewedLabel:'Grade B', reviewedSourceGroup:'fruit-1', reviewer:'r1', reviewedAt:'2026-10-04T10:00:00Z' } };
  const merged = state.mergeDrafts(manifest, draft);
  assert.equal(merged[0].reviewedLabel, 'Grade B');
  assert.match(state.csv(merged), /one.*Grade B/);
  assert.throws(() => state.mergeDrafts([{ ...manifest[0], reviewedLabel:'Grade A' }], draft), /refusing to overwrite/);
});

test('model proposals remain separate and require explicit human review', () => {
  const manifest = [{ id:'one', task:'quality', reviewedLabel:null }];
  const proposal = { id:'one', proposedLabel:'Grade B', confidence:.7, reviewPriority:.3,
    modelSha256:'a'.repeat(64), status:'unverified-model-proposal', humanReviewRequired:true };
  const mapped = state.suggestionMap({ schemaVersion:1, proposals:[proposal] }, manifest);
  assert.equal(mapped.one.proposedLabel, 'Grade B');
  assert.equal(manifest[0].reviewedLabel, null);
  assert.throws(() => state.suggestionMap({ schemaVersion:1, proposals:[{ ...proposal,
    humanReviewRequired:false }] }, manifest), /human review/);
  assert.throws(() => state.suggestionMap({ schemaVersion:1, proposals:[{ ...proposal,
    proposedLabel:'Fresh' }] }, manifest), /incompatible/);
});

test('review server exposes only the tool, manifest and prepared images', () => {
  assert.ok(server.resolveRequestPath('/').endsWith(path.join('review-tool','index.html')));
  assert.ok(server.resolveRequestPath('/research/public-review-manifest.json'));
  assert.ok(server.resolveRequestPath('/dataset/public/prepared/quality/example.jpg'));
  assert.equal(server.resolveRequestPath('/.git/config'), null);
  assert.equal(server.resolveRequestPath('/PitayaGrade_Capstone_Paper.md'), null);
  assert.equal(server.resolveRequestPath('/dataset/public/prepared/quality/example.exe'), null);
  assert.equal(server.resolveRequestPath('/%2e%2e/package.json'), null);
  assert.equal(server.resolveRequestPath('/review-tool/%2e%2e/package.json'), null);
  assert.equal(server.resolveRequestPath('/review-tool/..%2fpackage.json'), null);
});

test('browser review application parses as JavaScript', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'review-tool', 'app.js'), 'utf8');
  assert.doesNotThrow(() => new vm.Script(source));
});
