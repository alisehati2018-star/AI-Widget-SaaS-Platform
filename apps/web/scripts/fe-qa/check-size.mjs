#!/usr/bin/env node
// Component-size gate: no oversized React files. Flags .tsx files in app/ and
// components/ that exceed the line limit so pages get decomposed into smaller
// components.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const LIMIT = 300;

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.tsx$/.test(entry)) files.push(full);
  }
  return files;
}

let violations = 0;
for (const file of walk(join(ROOT, "app")).concat(walk(join(ROOT, "components")))) {
  const lines = readFileSync(file, "utf8").split("\n").length;
  if (lines > LIMIT) {
    console.error(`✗ oversized: ${relative(ROOT, file)} — ${lines} lines (limit ${LIMIT})`);
    violations++;
  }
}

console.log(`\ncheck-size: ${violations} file(s) over ${LIMIT} lines.`);
process.exit(violations > 0 ? 1 : 0);
