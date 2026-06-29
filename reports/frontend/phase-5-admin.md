# Phase 5 — Admin Dashboard / Responsive (report)

Goal: eliminate horizontal scrolling and verify it across breakpoints.

## Finding (caught by automated validation)
A Playwright responsive sweep (375/768/1280) measured **page-level** horizontal
overflow. Public pages were clean, but **every admin table page overflowed at
375px** (e.g. /admin/audit by 649px, /admin/users by 396px) and /admin/audit
even overflowed at 1280px.

Root cause: the dashboard `.main` is a CSS **grid item**, whose default
`min-width: auto` lets wide table content expand the whole page instead of
scrolling inside its card. (A table wrapper alone would NOT have fixed this —
the grid item itself was blowing out.)

## Fix
- `.main { min-width: 0; }` — defeats the grid min-content blowout.
- `.card:has(> table.table) { overflow-x: auto; }` promoted to **all widths**
  (was mobile-only) so any wide table scrolls within its card at every size.
- Mobile column floor lowered to `min-width: 520px`.

This is global, so it fixes the owner dashboard tables too (same shell).

## Validation
`node scripts/fe-qa/responsive-check.cjs` (seeds tenants, logs in as a
bootstrapped admin, sweeps public + admin pages):

> **responsive-check: 0 overflow failure(s).**

Public pages at 375/768/1280 and admin pages at 375/1280 — **no page-level
horizontal scroll anywhere**. Build green (93 pages); i18n 0/0; hardcoded 0;
size 0; backend untouched.

Reproduce: run the backend (:8000) + `next start` (:3000), then
`npm run check:responsive`.
