# Phase 9 — Frontend QA automation (consolidated report)

A single, enforced quality system for `apps/web`. The gates run via
`npm run check:all` (and `prebuild`, so local builds block) and in CI
(`.github/workflows/ci.yml` → frontend job → "Frontend QA gates"). Build-gating
checks fail on any issue; dead-component detection is reported as a warning.

## Checks & latest results

| Check | Script | Gate | Result |
|---|---|---|---|
| Missing / unused / locale-parity translations | `i18n-check.mjs` | fail | **0 errors, 0 unused** |
| Hardcoded JSX strings | `check-hardcoded.mjs` | fail | **0** |
| Component size (≤300 lines) | `check-size.mjs` | fail | **0 oversized** |
| Broken routes (Link/router → app route) | `check-routes.mjs` | fail | **46 routes, 0 broken** |
| Missing / broken assets | `check-assets.mjs` | fail | **0 missing** |
| Dead components (exported, never imported) | `check-dead.mjs` | warn | **0** |
| TypeScript | `tsc --noEmit` (CI) | fail | clean |
| Production build | `next build` | fail | **93 pages** |
| Responsive — no horizontal scroll | `responsive-check.cjs` | manual* | **0 overflow** |

\* Responsive needs a live web+backend stack, so it runs on demand
(`npm run check:all` covers the static gates; `npm run check:responsive` runs
the Playwright sweep). Coverage: public @ 320/375/768/1280, admin + owner @
375/1280.

## Dead code removed this phase
`TableWrap`, `EmptyState`, `ErrorState` (exported, never imported — the
responsive fix used CSS, not a wrapper), plus the now-unused
`common.states.errorTitle` and `.table-wrap` CSS.

## Outcome
The frontend overhaul (Phases 0–9) is complete: fully localized (fa-first,
RTL/LTR, Jalali), architecturally clean (shared hook/primitives, grouped IA),
redesigned marketing landing, responsive with no horizontal scroll, AA-contrast
and reduced-motion aware, and continuously verified by an enforced QA suite.
