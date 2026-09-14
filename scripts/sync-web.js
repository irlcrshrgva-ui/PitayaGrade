const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
for (const directory of ['js', 'css']) {
  fs.cpSync(path.join(root, directory), path.join(root, 'www', directory), { recursive: true });
}
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .replace('src="www/ort.min.js"', 'src="ort.min.js"');
fs.writeFileSync(path.join(root, 'www/index.html'), html);
console.log('Updated Capacitor web assets from existing sources.');
