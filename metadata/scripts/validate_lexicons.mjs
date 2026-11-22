#!/usr/bin/env node
// Strict lexicon validation of every generated record with @atproto/lexicon
// (the reference ATProto implementation): required fields, string formats
// (at-uri, did, datetime, uri, cid), maxLength / maxGraphemes, integer ranges,
// array bounds, blob shape, and record-key syntax (tid / any).
//
// Usage: node scripts/validate_lexicons.mjs --layers <dir> --chive <dir> [--json]
//   --layers  the Layers lexicon tree (scripts/check_metadata.py passes the tree
//             vendored in the pinned lairs install: Layers 0.11.0)
//   --chive   the chive lexicon tree (pub/chive and the com/atproto refs it uses)
import { readFileSync, readdirSync, statSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { Lexicons, jsonToLex } from '@atproto/lexicon';

const META = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const roots = [['layers', opt('--layers')], ['chive', opt('--chive')]];

function walk(dir, out = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.json')) out.push(p);
  }
  return out;
}

const lexicons = new Lexicons();
const loaded = {};
for (const [label, dir] of roots) {
  if (!dir || !statSync(dir, { throwIfNoEntry: false })) {
    console.error(`lexicon tree for ${label} not found: ${dir}`); process.exit(2);
  }
  loaded[label] = 0;
  for (const f of walk(dir).sort()) {
    let doc;
    try { doc = JSON.parse(readFileSync(f, 'utf8')); } catch { continue; }
    if (!doc.lexicon || !doc.id) continue;
    try { lexicons.add(doc); loaded[label]++; }
    catch (e) { if (!/already/.test(e.message)) { console.error(`bad lexicon ${f}: ${e.message}`); process.exit(2); } }
  }
}

const TID = /^[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}$/;
const ANY = /^[A-Za-z0-9._:~-]{1,512}$/;
let total = 0, ok = 0; const errors = []; const byType = {};
for (const sub of ['layers', 'chive']) {
  const dir = join(META, sub);
  for (const name of readdirSync(dir).filter((n) => n.endsWith('.jsonl')).sort()) {
    const lines = readFileSync(join(dir, name), 'utf8').split('\n').filter(Boolean);
    lines.forEach((line, i) => {
      total++;
      const where = `${sub}/${name}:${i + 1}`;
      try {
        const { uri, value } = JSON.parse(line);
        const [, , , collection, rkey] = uri.split('/');
        if (collection !== value.$type) throw new Error(`uri collection ${collection} != $type ${value.$type}`);
        const key = lexicons.getDef(collection)?.key ?? 'any';
        if (key === 'tid' ? !TID.test(rkey) : !ANY.test(rkey) || rkey === '.' || rkey === '..')
          throw new Error(`rkey ${rkey} does not satisfy key=${key}`);
        lexicons.assertValidRecord(collection, jsonToLex(value));
        ok++; byType[collection] = (byType[collection] ?? 0) + 1;
      } catch (e) { errors.push(`${where}: ${e.message}`); }
    });
  }
}
const summary = { lexiconsLoaded: loaded, total, ok, failed: errors.length, byType, errors: errors.slice(0, 50) };
if (args.includes('--json')) console.log(JSON.stringify(summary));
else {
  console.log(`Loaded lexicons: ${JSON.stringify(loaded)}`);
  console.log(`Validated ${total} records: ${ok} ok, ${errors.length} failed.`);
  if (errors.length) console.log(errors.slice(0, 50).join('\n'));
}
process.exit(errors.length ? 1 : 0);
