#!/usr/bin/env node
// Broken-route detection: every internal Link/router href must resolve to a
// real app route. Routes are derived from app/[locale]/**/page.tsx (route
// groups stripped, dynamic [param] segments matched as wildcards).

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const LOCALE_ROOT = join(ROOT, "app", "[locale]");

// Build the route table from the filesystem.
function routesFrom(dir, base = "", out = []) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (!statSync(full).isDirectory()) {
      if (entry === "page.tsx") out.push(base === "" ? "/" : base);
      continue;
    }
    const seg = entry.startsWith("(") && entry.endsWith(")") ? "" : `/${entry}`; // strip groups
    routesFrom(full, base + seg, out);
  }
  return out;
}
const ROUTES = existsSync(LOCALE_ROOT) ? routesFrom(LOCALE_ROOT) : [];
const ROUTE_SEGS = ROUTES.map((r) => r.split("/").filter(Boolean));

function matches(hrefSegs) {
  return ROUTE_SEGS.some(
    (rs) =>
      rs.length === hrefSegs.length &&
      rs.every((seg, i) => seg.startsWith("[") || hrefSegs[i] === ":d" || seg === hrefSegs[i]),
  );
}

function walk(dir, files = []) {
  for (const entry of readdirSync(dir)) {
    if (entry === "node_modules" || entry === ".next") continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, files);
    else if (/\.tsx?$/.test(entry)) files.push(full);
  }
  return files;
}

// Collect hrefs from Link href="..." / href={`...`} and router.push/replace("...").
const hrefRe = /\bhref=(?:"([^"]+)"|\{`([^`]+)`\})|\brouter\.(?:push|replace)\(\s*[`"']([^`"']+)[`"']/g;
let bad = 0;
const seen = new Set();
for (const file of walk(join(ROOT, "app")).concat(walk(join(ROOT, "components")))) {
  const text = readFileSync(file, "utf8");
  let m;
  while ((m = hrefRe.exec(text))) {
    let href = m[1] ?? m[2] ?? m[3];
    if (!href || !href.startsWith("/")) continue; // external / anchors / mailto
    if (href.startsWith("/api") || href.startsWith("//")) continue;
    href = href.split("#")[0].split("?")[0]; // drop hash/query
    const segs = href.split("/").filter(Boolean).map((s) => (s.includes("${") ? ":d" : s));
    const key = segs.join("/");
    if (seen.has(key)) continue;
    seen.add(key);
    if (!matches(segs)) {
      console.error(`✗ broken route: href "${href}" matches no app route`);
      bad++;
    }
  }
}

console.log(`\ncheck-routes: ${ROUTES.length} routes, ${bad} broken reference(s).`);
process.exit(bad > 0 ? 1 : 0);
