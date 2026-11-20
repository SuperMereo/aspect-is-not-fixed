#!/usr/bin/env node
import { readFileSync, readdirSync, statSync, existsSync } from 'fs';
import { join, dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import { Lexicons, jsonToLex } from '@atproto/lexicon';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(__dirname, '..', '..');
// Generated records live here (untracked); override with LAYERS_RECORDS_DIR.
const RECORDS = process.env.LAYERS_RECORDS_DIR || resolve(__dirname, 'records');

// Config lives in data/scripts/.env (gitignored), the same file the generator
// reads. Load it into process.env without clobbering anything already set.
const ENV_FILE = resolve(__dirname, '.env');
if (existsSync(ENV_FILE)) {
  for (const line of readFileSync(ENV_FILE, 'utf8').split('\n')) {
    const s = line.trim();
    if (!s || s.startsWith('#') || !s.includes('=')) continue;
    const i = s.indexOf('=');
    const k = s.slice(0, i).trim();
    if (!(k in process.env)) process.env[k] = s.slice(i + 1).trim();
  }
}

// The upstream layers lexicons are not vendored here; validation needs a
// local checkout, pinned to the 0.9.0 release (branch lexicons-v0.9.0). Point
// LAYERS_LEXICONS at it (see .env.example).
const LEXICON_ROOTS = [
  { label: 'layers', dir: process.env.LAYERS_LEXICONS, hint: 'the layers lexicons at v0.9.0 (branch lexicons-v0.9.0)' },
];

const unset = LEXICON_ROOTS.filter(r => !r.dir);
if (unset.length) {
  console.error('Missing lexicon path(s). Set the following in data/scripts/.env (or the environment):');
  for (const r of unset) console.error(`  ${r.label.toUpperCase()}_LEXICONS=<path to ${r.hint}>`);
  process.exit(2);
}

function walk(dir, out = []) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.json')) out.push(p);
  }
  return out;
}

const lexicons = new Lexicons();
let loaded = 0;
for (const { label, dir } of LEXICON_ROOTS) {
  if (!statSync(dir, { throwIfNoEntry: false })) {
    console.error(`  ! ${label} lexicons not found at ${dir}`);
    continue;
  }
  for (const f of walk(dir)) {
    try {
      const doc = JSON.parse(readFileSync(f, 'utf8'));
      if (doc.lexicon && doc.id) {
        lexicons.add(doc);
        loaded++;
      }
    } catch (e) {
      console.error(`  ! Bad lexicon ${f}: ${e.message}`);
    }
  }
}
console.log(`Loaded ${loaded} lexicon documents.\n`);

function* readRecords(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) {
      yield* readRecords(p);
    } else if (e.name.endsWith('.jsonl')) {
      const lines = readFileSync(p, 'utf8').split('\n').filter(Boolean);
      for (let i = 0; i < lines.length; i++) {
        try {
          yield { path: `${p}:${i + 1}`, record: JSON.parse(lines[i]) };
        } catch (err) {
          console.error(`  ! Parse error ${p}:${i + 1}: ${err.message}`);
        }
      }
    } else if (e.name.endsWith('.json') && !['package.json', 'package-lock.json'].includes(e.name)) {
      try {
        yield { path: p, record: JSON.parse(readFileSync(p, 'utf8')) };
      } catch (err) {
        console.error(`  ! Parse error ${p}: ${err.message}`);
      }
    }
  }
}

let total = 0;
let ok = 0;
let bad = 0;
const errors = [];

{
  const dir = RECORDS;
  if (!statSync(dir, { throwIfNoEntry: false })) {
    console.error(`No generated records at ${dir}. Run generate_metadata.py first.`);
    process.exit(2);
  }
  for (const { path, record } of readRecords(dir)) {
    total++;
    const type = record.$type;
    if (!type) {
      bad++;
      errors.push(`${path}: missing $type`);
      continue;
    }
    try {
      // jsonToLex rehydrates blob refs and CIDs from their JSON form into
      // the BlobRef/CID class instances the strict validators expect.
      lexicons.assertValidRecord(type, jsonToLex(record));
      ok++;
    } catch (e) {
      bad++;
      errors.push(`${path} (${type}): ${e.message}`);
    }
  }
}

console.log(`Validated ${total} records: ${ok} ok, ${bad} failed.`);
if (errors.length) {
  console.log('\nErrors:\n' + errors.slice(0, 100).join('\n'));
  if (errors.length > 100) console.log(`...and ${errors.length - 100} more.`);
  process.exit(1);
}
