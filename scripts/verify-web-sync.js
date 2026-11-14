const fs = require('node:fs');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const mismatches = [];

function compareTrees(source, destination, label) {
  if (!fs.existsSync(source) || !fs.existsSync(destination)) {
    mismatches.push(label);
    return;
  }
  const sourceNames = fs.readdirSync(source).sort();
  const destinationNames = fs.readdirSync(destination).sort();
  if (JSON.stringify(sourceNames) !== JSON.stringify(destinationNames)) mismatches.push(label);
  for (const name of sourceNames) {
    const from = path.join(source, name);
    const to = path.join(destination, name);
    const stat = fs.statSync(from);
    if (stat.isDirectory()) compareTrees(from, to, `${label}/${name}`);
    else if (!fs.existsSync(to) || !fs.readFileSync(from).equals(fs.readFileSync(to))) {
      mismatches.push(`${label}/${name}`);
    }
  }
}

for (const directory of ['js', 'css', 'review-tool', 'annotation-tool', 'site']) {
  compareTrees(path.join(root, directory), path.join(root, 'www', directory), `www/${directory}`);
}

for (const filename of ['disease-lab.html', 'manifest.webmanifest', 'service-worker.js', 'reset.html']) {
  const source = path.join(root, filename);
  const destination = path.join(root, 'www', filename);
  if (!fs.existsSync(destination) || !fs.readFileSync(source).equals(fs.readFileSync(destination))) {
    mismatches.push(`www/${filename}`);
  }
}

const appSource = fs.readFileSync(path.join(root, 'index.html'), 'utf8')
  .replace('src="www/ort.min.js"', 'src="ort.min.js"');
if (appSource !== fs.readFileSync(path.join(root, 'www/index.html'), 'utf8')) {
  mismatches.push('www/index.html');
}

for (const filename of ['public-review-manifest.json', 'source-group-suggestions-2026-10-10.json', 'review-assignments-3.json']) {
  const source = path.join(root, 'research', filename);
  const destination = path.join(root, 'www/research', filename);
  if (!fs.existsSync(destination) || !fs.readFileSync(source).equals(fs.readFileSync(destination))) {
    mismatches.push(`www/research/${filename}`);
  }
}

if (mismatches.length) {
  console.error('Web bundle is out of sync with editable sources:');
  for (const file of mismatches) console.error(` - ${file}`);
  process.exitCode = 1;
} else {
  console.log('Web bundle matches its editable sources.');
}
