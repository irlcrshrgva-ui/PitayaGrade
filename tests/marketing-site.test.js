const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.join(__dirname, '..');

test('marketing site contains home, about, contact and direct APK navigation', () => {
  const pages = ['index.html', 'about.html', 'contact.html'];
  for (const page of pages) {
    const html = fs.readFileSync(path.join(root, 'site', page), 'utf8');
    assert.match(html, /PitayaGrade/);
    assert.match(html, /assets\/logo\.png/);
    assert.match(html, /href="index\.html"/);
    assert.match(html, /href="about\.html"/);
    assert.match(html, /href="contact\.html"/);
  }
  const home = fs.readFileSync(path.join(root, 'site', 'index.html'), 'utf8');
  assert.match(home, /downloads\/PitayaGrade-debug\.apk/);
  assert.match(home, /testing build/i);
  assert.match(home, /visible-symptom/i);
});

test('marketing site follows the app design system and supports reduced motion', () => {
  const css = fs.readFileSync(path.join(root, 'site', 'styles.css'), 'utf8');
  assert.match(css, /--pink:\s*#e91e63/i);
  assert.match(css, /--green:\s*#4caf50/i);
  assert.match(css, /--font-body:\s*'Inter'/);
  assert.match(css, /--font-display:\s*'Space Grotesk'/);
  assert.match(css, /prefers-reduced-motion/);
  assert.doesNotThrow(() => new vm.Script(fs.readFileSync(path.join(root, 'site', 'site.js'), 'utf8')));
});

test('packaged marketing site matches editable source', () => {
  for (const file of ['index.html', 'about.html', 'contact.html', 'styles.css', 'site.js']) {
    assert.equal(fs.readFileSync(path.join(root, 'www', 'site', file), 'utf8'),
      fs.readFileSync(path.join(root, 'site', file), 'utf8'));
  }
});
