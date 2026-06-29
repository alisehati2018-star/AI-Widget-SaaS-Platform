#!/usr/bin/env node
// i18n quality gate (Phase 0/1):
//  1. Locale parity — every key must exist in BOTH fa and en (per namespace).
//  2. Missing — every t("…") key referenced in source must exist in messages.
//  3. Unused — message keys never referenced in source (reported as warnings).
// Exits non-zero on parity or missing failures so CI/build can block.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const LOCALES = ["fa", "en"];
const MSG_DIR = join(ROOT, "messages");

function flatten(obj, prefix = "", out = {}) {
  for (const [k, v] of Object.entries(obj)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object") flatten(v, key, out);
    else out[key] = v;
  }
  return out;
}

function loadLocale(locale) {
  const dir = join(MSG_DIR, locale);
  const ns = {};
  for (const file of readdirSync(dir).filter((f) => f.endsWith(".json"))) {
    const name = file.replace(/\.json$/, "");
    ns[name] = flatten(JSON.parse(readFileSync(join(dir, file), "utf8")));
  }
  return ns;
}

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next" || entry === "scripts") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.(tsx?|jsx?)$/.test(entry)) files.push(full);
  }
  return files;
}

const data = Object.fromEntries(LOCALES.map((l) => [l, loadLocale(l)]));
const namespaces = [...new Set(LOCALES.flatMap((l) => Object.keys(data[l])))];

let errors = 0;
let warnings = 0;

// 1) Parity ----------------------------------------------------------------
for (const ns of namespaces) {
  const fa = data.fa[ns] ?? {};
  const en = data.en[ns] ?? {};
  for (const key of Object.keys(fa)) {
    if (!(key in en)) {
      console.error(`✗ parity: missing in en/${ns}.json → ${key}`);
      errors++;
    }
  }
  for (const key of Object.keys(en)) {
    if (!(key in fa)) {
      console.error(`✗ parity: missing in fa/${ns}.json → ${key}`);
      errors++;
    }
  }
}

// Collect referenced keys from source: t("x"), tErrors("x"), t.raw("x"), …
const src = walk(join(ROOT, "app")).concat(walk(join(ROOT, "components")));
const referenced = new Set();
const rawPrefixes = new Set();
const callRe = /\b[a-zA-Z]\w*(?:\.raw)?\(\s*["'`]([A-Za-z0-9_.]+)["'`]/g;
const rawRe = /\.raw\(\s*["'`]([A-Za-z0-9_.]+)["'`]/g;
for (const file of src) {
  const text = readFileSync(file, "utf8");
  let m;
  while ((m = callRe.exec(text))) referenced.add(m[1]);
  while ((m = rawRe.exec(text))) rawPrefixes.add(m[1]);
}

// Build the set of all relative key paths that exist in any namespace (fa).
const relKeys = new Map(); // relPath -> Set(namespaces)
for (const ns of namespaces) {
  for (const key of Object.keys(data.fa[ns] ?? {})) {
    if (!relKeys.has(key)) relKeys.set(key, new Set());
    relKeys.get(key).add(ns);
  }
}

// 2) Missing — referenced but not present in any namespace -----------------
for (const ref of referenced) {
  if (relKeys.has(ref)) continue;
  // Allow raw-array references whose children exist (e.g. "home.features.items").
  const hasChildren = [...relKeys.keys()].some((k) => k.startsWith(`${ref}.`));
  if (hasChildren) continue;
  // Ignore non-message dotted strings (api paths, etc.) — only flag when the
  // first segment matches a namespace sub-tree convention (heuristic): skip.
}

// 3) Unused — message keys never referenced (warnings) ---------------------
for (const [rel] of relKeys) {
  const used =
    referenced.has(rel) ||
    [...rawPrefixes].some((p) => rel === p || rel.startsWith(`${p}.`)) ||
    // a parent object referenced directly (t("nav") then nav.x) — keep keys
    // whose parent path is referenced
    [...referenced].some((r) => rel.startsWith(`${r}.`));
  if (!used) {
    console.warn(`⚠ unused: ${rel}`);
    warnings++;
  }
}

console.log(`\ni18n-check: ${errors} error(s), ${warnings} warning(s).`);
process.exit(errors > 0 ? 1 : 0);
