# Frontend Modernization Roadmap (living document)

Single source of truth for the `apps/web` overhaul. Always reflects completed
work, current progress, remaining tasks, and implementation status so work can
resume at any time. Branch: `claude/gallant-shannon-8b31td`.

## Locked decisions
- **i18n:** next-intl, locale-routed, Persian-first (`fa` default,
  `localePrefix: as-needed`), 8 domain namespaces, per-route scoped providers.
- **Dates:** Jalali (Shamsi) via one abstraction (`lib/datetime.ts`, ICU).
- **Theme:** dark-only. **Manual billing** (no live PSP yet).

## Status at a glance

| Phase | Title | Status | Commit |
|---|---|---|---|
| 0 | i18n foundation + Jalali + QA tooling | ✅ done | `4827472` |
| 1 | Full internationalization (47 routes) | ✅ done | `f026f61` |
| 2 | Architecture (`useResource`, responsive table) | ✅ done | `6b16a59` |
| 3 | Marketing landing redesign | ✅ done | `e321aa5` |
| 4 | Grouped dashboard navigation | ✅ done | `6c8dfa9` |
| — | Verification hardening (real missing-key gate) | ✅ done | `e9b5fd8` |
| 5 | Admin responsive — grid-blowout fix | ✅ done | `7e34ee9` |
| 6 | Full responsive sweep (320–1280) | ✅ done | `2c0bd81` |
| 7 | Content quality | ✅ done | `159af60` |
| 8 | Design-system polish (a11y contrast, reduced motion) | ✅ done | `c765ad4` |
| 9 | Consolidated QA automation | ✅ done | `3c50e76` |
| — | RTL skip-link + verification pass | ✅ done | `4b45db8` |
| 10 | Functional Frontend Completion | ✅ done | `9f49202` |
| **11** | **Iconography — emoji → SVG icon set** | ✅ **done** | _this phase_ |
| 12 | Marketing supporting-page redesign (pricing/docs/contact) | ⏳ planned | — |
| 13 | Measurement (Lighthouse/axe) + localized backend emails | ⏳ planned | — |

> Note: the visual redesign phases (3–9) were already complete when the
> Functional Completion phase was requested, so it lands as Phase 10; the
> remaining **design** items follow as Phases 11–13.

## Phase 10 — Functional Frontend Completion (done)
Audit + connect every available backend API; no page left display-only unless
intentionally read-only. Full audit: `reports/frontend/phase-10-functional.md`.
- Connected `POST /admin/tenants` (admin "Create a tenant" form, one-time key,
  row appears immediately) and `GET /admin/tenants/{id}/export` (tenant export).
- E2E verified: `npm run check:functional` (0 failures, incl. mutation→UI).
- Conclusion: dashboards were already largely functional; read-only pages are
  analytics/monitoring/logs (correctly read-only). No placeholder buttons remain.
- **Needs a backend endpoint first** (not frontend gaps): KB edit, plan editing,
  authenticated change-password/email, lead status. Tracked for backend.

## Phase 11 — Iconography (done)
Replaced every emoji glyph with a cohesive inline-SVG `Icon` set
(`components/icons.tsx`, ~34 line icons, 24×24, currentColor). Rewired the owner
+ admin sidebars, marketing feature/use-case/deep-dive/hero icons, the features
page, and the localized 404. Verified: 14 SVGs render on the landing, 0 emoji
remain, responsive sweep 0 overflow. (`/features` content already done;
`pricing` keeps its data-driven cards — its icons were already non-emoji.)

## Remaining design phases (planned)
- **12 — Marketing supporting pages:** give `/pricing`, `/docs`,
  `/contact` the same section quality as the landing (Phase 3).
- **13 — Measurement & emails:** run Lighthouse + axe, fix findings; localize the
  backend notification emails (verification/reset/invoice) per recipient locale.

## QA system (enforced: CI `check:all` + `prebuild`)
Static gates (fail build): i18n parity+missing+unused · hardcoded strings ·
component size ≤300 · broken routes · missing assets. Reported: dead components.
Live-stack checks (on demand): `check:responsive` (0 overflow, 320–1280,
public+admin+owner), `check:functional` (admin workflows, mutation→UI).
Current: **all green**; `next build` 93 pages; backend 7 passed/3 ES-skipped.

## Reports
`reports/frontend/`: `roadmap.md` (this) · `phase-5-admin.md` ·
`phase-6-responsive.md` · `phase-9-qa.md` · `phase-10-functional.md`.

## Backlog beyond the frontend
- Backend endpoints listed under Phase 10 "needs a backend endpoint".
- Elasticsearch + inference validation phase (search/RAG/analytics, the
  `/admin/insight|analyst|zero-results` panels).
