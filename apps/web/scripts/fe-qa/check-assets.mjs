#!/usr/bin/env node
// Missing/broken-asset detection: every local asset referenced in code
// (src/href "/foo.svg|png|…") must exist under public/ or app/ (Next file
// conventions). External URLs are ignored.

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const PUBLIC = join(ROOT, "public");

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.tsx?$/.test(entry)) files.push(full);
  }
  return files;
}

const assetRe = /(?:src|href)=["'](\/[A-Za-z0-9_./-]+\.(?:svg|png|jpe?g|webp|gif|ico|woff2?|avif))["']/g;
let missing = 0;
const seen = new Set();
for (const file of walk(join(ROOT, "app")).concat(walk(join(ROOT, "components")))) {
  const text = readFileSync(file, "utf8");
  let m;
  while ((m = assetRe.exec(text))) {
    const ref = m[1];
    if (seen.has(ref)) continue;
    seen.add(ref);
    const inPublic = existsSync(join(PUBLIC, ref.replace(/^\//, "")));
    const inApp = existsSync(join(ROOT, "app", ref.replace(/^\//, "")));
    if (!inPublic && !inApp) {
      console.error(`✗ missing asset: "${ref}" not found in public/ or app/`);
      missing++;
    }
  }
}

console.log(`\ncheck-assets: ${seen.size} local asset ref(s), ${missing} missing.`);
process.exit(missing > 0 ? 1 : 0);
