const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

for (const directory of ['js', 'www/js']) {
  test(`${directory} modules parse without executing browser code`, () => {
    for (const name of fs.readdirSync(path.join(__dirname, '..', directory))) {
      if (!name.endsWith('.js')) continue;
      const filename = path.join(__dirname, '..', directory, name);
      new vm.Script(fs.readFileSync(filename, 'utf8'), { filename });
    }
  });
}
