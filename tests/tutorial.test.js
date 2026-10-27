const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');

test('tutorial card stays above the spotlight mask and supports short screens', () => {
  const css = fs.readFileSync(path.join(root, 'css', 'styles.css'), 'utf8');
  assert.match(css, /#tutorialOverlay\.spotlight-mode\s*\{[\s\S]*?background:\s*transparent/);
  assert.match(css, /\.tutorial-card\s*\{[\s\S]*?z-index:\s*10001/);
  assert.match(css, /@media \(max-height: 650px\)/);
  assert.match(css, /safe-area-inset-bottom/);
});

test('tutorial spotlight is clamped inside the viewport', () => {
  const app = fs.readFileSync(path.join(root, 'js', 'app.js'), 'utf8');
  assert.doesNotThrow(() => new vm.Script(app));
  assert.match(app, /Math\.max\(edge, r\.left - pad\)/);
  assert.match(app, /Math\.min\(window\.innerWidth - edge, r\.right \+ pad\)/);
  assert.doesNotMatch(app, /disease rate/);
});

test('tutorial dialog semantics and packaged sources are current', () => {
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  assert.match(html, /id="tutorialOverlay" role="dialog" aria-modal="true"/);
  const packagedHtml = fs.readFileSync(path.join(root, 'www', 'index.html'), 'utf8');
  assert.equal(packagedHtml, html.replace('src="www/ort.min.js"', 'src="ort.min.js"'));
  for (const file of ['css/styles.css', 'js/app.js']) {
    assert.equal(fs.readFileSync(path.join(root, 'www', file), 'utf8'), fs.readFileSync(path.join(root, file), 'utf8'));
  }
});
