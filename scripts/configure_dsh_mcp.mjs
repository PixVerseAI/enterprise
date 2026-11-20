/** Merge a real plugin insertion into the selected native DeepSeek profile. */
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {randomUUID} from 'node:crypto';

const [binary, file, url, ...flags] = process.argv.slice(2);
try {
  const require = createRequire(binary);
  const YAML = require('yaml');
  if (fs.existsSync(file) && fs.lstatSync(file).isSymbolicLink()) throw Error();
  const original = fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '[]\n';
  const document = YAML.parseDocument(original, {
    customTags: [{tag: 'tag:yaml.org,2002:js', resolve: value => value}],
  });
  if (document.errors.length || !YAML.isSeq(document.contents)) throw Error();
  const matches = [];
  function visit(node) {
    if (YAML.isMap(node)) {
      const config = node.get('config', true);
      if (node.get('name') === '@deepseek-ai/dsh-mcp-client' &&
          YAML.isMap(config) && config.get('serverName') === 'pixverse') matches.push(node);
      for (const pair of node.items) visit(pair.value);
    } else if (YAML.isSeq(node)) {
      for (const item of node.items) visit(item);
    }
  }
  visit(document.contents);
  if (matches.length > 1) throw Error();
  const existing = matches[0];
  if (existing && existing.get('id') !== 'pixverse-enterprise-mcp' && !flags.includes('--replace')) {
    throw Error();
  }
  const entry = document.createNode({
    id: 'pixverse-enterprise-mcp', name: '@deepseek-ai/dsh-mcp-client',
    config: {serverName: 'pixverse', transport: 'streamable-http', url,
      headers: {Authorization: '`Bearer ${process.env.PIXVERSE_OPENAPI_KEY}`'}},
  });
  entry.get('config', true).get('headers', true).get('Authorization', true).tag = 'tag:yaml.org,2002:js';
  if (existing) {
    // Only entries previously installed in an insert list are managed automatically.
    // A bare id patch is an override, not a new plugin: reject it instead of pretending it loads.
    let inserted = false;
    for (const patch of document.contents.items) {
      const list = YAML.isMap(patch) ? patch.get('insert', true) : null;
      if (YAML.isSeq(list) && list.items.includes(existing)) {
        list.items[list.items.indexOf(existing)] = entry;
        inserted = true;
      }
    }
    if (!inserted) throw Error();
  } else {
    const insertion = document.createNode({insert: []});
    insertion.get('insert', true).add(entry);
    document.contents.add(insertion);
  }
  const rendered = document.toString();
  if (!flags.includes('--check') && rendered !== original) {
    const temporary = path.join(path.dirname(file), `.pixverse-mcp-${randomUUID()}`);
    try {
      fs.writeFileSync(temporary, rendered, {mode: 0o600, flag: 'wx'});
      fs.renameSync(temporary, file);
    } finally {
      if (fs.existsSync(temporary)) fs.unlinkSync(temporary);
    }
  }
  const action = !existing ? 'install' : rendered === original ? 'noop' : 'reconfigure';
  process.stdout.write(JSON.stringify({ok: true, path: file, check_only: flags.includes('--check'), action}));
} catch {
  process.stderr.write('Cannot merge the selected DeepSeek profile.\n');
  process.exitCode = 2;
}
