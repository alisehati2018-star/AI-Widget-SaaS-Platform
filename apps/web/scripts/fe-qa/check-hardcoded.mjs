#!/usr/bin/env node
// Hardcoded-string detector (Phase 1): flags literal JSX *text content* that
// isn't wrapped in a translation call. High-signal only: single-line text
// between > and < that reads like prose (no code punctuation). Attributes and
// {expressions} are out of scope. Brand/proper nouns and the provider-less
// global 404 are allowlisted.

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname, relative } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const ALLOW_FILES = new Set(["app/not-found.tsx"]); // provider-less fallback
const ALLOW_TEXT = new Set(["WooCommerce", "OpenCart", "Vitrin", "ZarinPal", "Stripe"]);

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.tsx$/.test(entry)) files.push(full);
  }
  return files;
}

// Candidate JSX text: a single line segment between > and < with no braces and
// no newline. We then reject anything that looks like code.
const textRe = />([^<>{}\n]+)</g;
// Reject if the candidate contains code punctuation/keywords.
const CODE = /[(){}[\];=$`]|=>|\/\/|\b(useState|useEffect|return|const|let|authFetch|apiFetch|null|true|false|undefined)\b/;

let violations = 0;
for (const file of walk(join(ROOT, "app")).concat(walk(join(ROOT, "components")))) {
  const rel = relative(ROOT, file);
  if (ALLOW_FILES.has(rel)) continue;
  const text = readFileSync(file, "utf8");
  let m;
  while ((m = textRe.exec(text))) {
    const raw = m[1].trim();
    if (!raw || ALLOW_TEXT.has(raw)) continue;
    if (CODE.test(raw)) continue; // looks like code, not prose
    // Require at least two consecutive letters (Latin or Arabic/Persian range).
    if (!/[A-Za-z؀-ۿ]{2}/.test(raw)) continue;
    // Skip url-ish / path-ish tokens.
    if (/^https?:|^\/|^[\w.]+\.[\w.]+$/.test(raw)) continue;
    const line = text.slice(0, m.index).split("\n").length;
    console.error(`✗ hardcoded JSX text: ${rel}:${line} → "${raw}"`);
    violations++;
  }
}

console.log(`\ncheck-hardcoded: ${violations} violation(s).`);
process.exit(violations > 0 ? 1 : 0);
