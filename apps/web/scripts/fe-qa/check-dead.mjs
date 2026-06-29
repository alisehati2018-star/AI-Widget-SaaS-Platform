#!/usr/bin/env node
// Dead-component detection: named component/function exports under components/
// that are never imported anywhere. Default exports (pages/layouts) are wired by
// Next's router and excluded. Type-only exports are ignored.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.tsx?$/.test(entry)) files.push(full);
  }
  return files;
}

const compFiles = walk(join(ROOT, "components"));
const allFiles = walk(join(ROOT, "app")).concat(compFiles);
const corpus = allFiles.map((f) => ({ f, text: readFileSync(f, "utf8") }));

// Exported value symbols (function/const) — skip `export type`/`export interface`.
const exportRe = /export\s+(?:async\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9]*)/g;
let dead = 0;
for (const { f, text } of corpus) {
  if (!f.includes(`${"/"}components${"/"}`)) continue;
  let m;
  while ((m = exportRe.exec(text))) {
    const sym = m[1];
    const importRe = new RegExp(`import[^;]*\\b${sym}\\b[^;]*from`);
    const used = corpus.some(({ f: g, text: t }) => g !== f && importRe.test(t));
    if (!used) {
      console.warn(`⚠ dead component: ${relative(ROOT, f)} → ${sym} (exported, never imported)`);
      dead++;
    }
  }
}

console.log(`\ncheck-dead: ${dead} unused export(s).`);
// Warning-level: report but don't fail the build (avoids false positives on
// intentionally-public primitives). Surfaced in the consolidated report.
process.exit(0);
