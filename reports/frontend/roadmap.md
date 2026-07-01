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
| 11 | Iconography — emoji → SVG icon set | ✅ done | `cd80b29` |
| 12 | Marketing supporting-page redesign (pricing/docs/contact) | ✅ done | `e658336` |
| **13** | **Measurement (axe) + localized backend emails** | ✅ **done** | _this phase_ |

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
  change-email, lead status. Tracked for backend.
- ✅ **Authenticated change-password** added (full-stack): `POST /auth/change-password`
  (verifies current password) + a form in owner Settings. E2E-verified — old
  password is invalidated, new one works, wrong current → 403.
- ✅ **Persian content nativized** — replaced literal translations (e.g. «مستأجر»
  → «فروشگاه», «دروازه» → «موتور هوش مصنوعی») with native, function-based copy.

## Phase 11 — Iconography (done)
Replaced every emoji glyph with a cohesive inline-SVG `Icon` set
(`components/icons.tsx`, ~34 line icons, 24×24, currentColor). Rewired the owner
+ admin sidebars, marketing feature/use-case/deep-dive/hero icons, the features
page, and the localized 404. Verified: 14 SVGs render on the landing, 0 emoji
remain, responsive sweep 0 overflow. (`/features` content already done;
`pricing` keeps its data-driven cards — its icons were already non-emoji.)

## Phase 12 — Marketing supporting pages (done)
- **Pricing:** added an "In every plan" feature strip (SVG icons + copy) below
  the plan cards.
- **Contact:** two-column layout — contact-method cards (Sales / Support /
  Security) beside the form.
- **Docs:** added a "Quick widget install" code-snippet card.
- Bilingual copy in `marketing.json`; new CSS responsive at 880/560px; full
  responsive sweep 0 overflow.

## Phase 13 — Measurement & localized emails (done)
- **axe a11y audit** (`npm run check:a11y`): found 1 critical (unlabelled form
  controls); fixed `Field` to wrap the input in its `<label>` → **0 serious/
  critical** across public pages. Report: `reports/frontend/phase-13-measurement.md`.
- **Localized emails:** verification/reset/invite templates render fa/en; auth
  endpoints pass the recipient's `NEXT_LOCALE` cookie through.

## Status: frontend roadmap complete (Phases 0–13)
All planned frontend + functional + design phases are done. Remaining work is
outside the frontend (see backlog).

## Phase 14 — Backend completion: ES control, agent console, widget, plugins
Full-stack expansion driven by `reports/backend/gap-analysis.md`:
- **Semantic brand/category indexing** — `CanonicalProduct.embedding_text()` now
  embeds title + brand + categories + attributes + description (worker uses it),
  so brand/category are indexed *with* the product semantically, not only as
  BM25 keyword fields.
- **Admin Elasticsearch control panel** — new `/admin/es/*` endpoints (health,
  indices, mapping, tenant-count, ensure-index, reindex+alias-swap, alias,
  delete-index) wired to `acip_search.index_admin`, plus `/admin/elasticsearch`
  UI (cluster health, index table, mapping viewer, zero-downtime reindex).
- **Agent test console** — `/admin/agent/test` + `/admin/agent/search` run the
  RAG assistant / hybrid search against a chosen tenant's data with operator
  auth; `/admin/agent` UI (tenant picker, chat + raw-search tabs, rung/latency/
  citations).
- **Widget** — self-contained single-line loader (`/widget/v1.js` →
  `apps/dashboard/widget/loader.js`), `/v1/widget/config` (global defaults ←
  tenant overrides), admin `/admin/widget-defaults` + `/admin/widget` UI,
  dashboard widget page now shows the real one-line embed (gated on active store
  + widget key) and per-store widget behaviour settings.
- **Remaining functional items** — KB edit (`PATCH /tenant/kb/{id}`), lead
  status/notes (`POST /tenant/leads/{id}` + migration 0010), admin plan editing
  (`GET/PATCH /admin/plans` + editable UI), authenticated change-email
  (`POST /auth/change-email`), all wired in the UI.
- **Store integrations** — new root `integrations/` folder with a full OpenCart
  3.x module (admin/catalog controllers + model + twig + language + OCMOD) and a
  WordPress/WooCommerce plugin (settings, real-time + bulk sync, widget
  injection, search replacement).
- Gates: backend 103 passed/10 ES-skipped, ruff clean, mypy clean (87 files);
  web typecheck + i18n 0/0 + hardcoded 0 + size 0 + routes 0 + dead 0.

## Phase 15 — Full-page layout + admin/dashboard completeness pass
Layout audit found `.main` capped at 1080px (huge dead space on wide screens)
and several pages were a single narrow floating card. Full page-by-page audit
(two Explore agents, admin + owner dashboard) then fixed every finding:
- **Layout system**: `.main` widened to 1760px; new `.dash-2col` /
  `.dash-2col-even` / `.dash-3col` / `.card-stack` grid utilities so related
  panels sit side-by-side instead of stacking in one column.
- **admin/plans**: rebuilt as a list+detail layout (table + sticky edit panel).
- **admin/analytics**: tenant selector moved into the header; added
  most-wanted + zero-results + an **Insight** narrative + **funnel** panel +
  an **"Ask the analyst"** NL question box — wiring the previously-unused
  `GET /admin/insight` and `POST /admin/analyst` endpoints.
- **admin/synonyms**, **admin/agent**: tenant selector moved into the header;
  agent console gained a "Store context" panel (tenant id + live indexed-doc
  count via the previously-unused `GET /admin/es/tenant-count`).
- **admin/elasticsearch**: added a per-store document-count widget.
- **admin/users**: added `POST /admin/users/{email}/role` (promote/demote
  platform_admin ↔ store roles) with an inline role editor — closes the only
  admin capability gap found (no way to grant a second platform admin without
  the raw operator token).
- **admin/settings**: was pure display; now has working change-password +
  change-email forms (same endpoints as the owner dashboard) alongside the
  security/platform info panels.
- **admin/health**: added a "related diagnostics" quick-link panel.
- **admin/widget**, **dashboard/widget**: added a live preview panel (launcher
  + greeting bubble reflecting the actual color/position/greeting settings).
- **dashboard/knowledge**: rebuilt as a list+detail layout (matches admin/plans).
- **dashboard/settings**: split into store/tracking/privacy (left) and
  password/email security (right).
- Verified live in-browser (Playwright, real PG+Redis+API, fresh admin +
  store-owner accounts): screenshotted every redesigned page, and ran a full
  create→edit→publish→save round trip on the knowledge-base feature against
  the real backend. Elasticsearch was intentionally left down for this pass
  (per instruction, ES testing is the user's own responsibility) — pages
  degrade to honest "unavailable" states rather than crashing.
- Gates: web typecheck + i18n 0/0 + hardcoded/size/routes/dead 0, `next build`
  99 pages; backend 103 passed/10 ES-skipped, ruff + mypy clean (87 files).
- **integrations/opencart3**: added a "Test connection" check (admin
  controller + `Acip::ping()`), a Persian (`fa`) admin language pack alongside
  `en-gb`, and fixed the OCMOD to register the widget-injection event through
  the OC3 event table (not an OC4-style startup patch).
- **integrations/wordpress**: rebuilt to full plugin conventions — enqueued
  `assets/js/admin.js` + `assets/css/admin.css` (no more inline `<script>`),
  `uninstall.php` (clean option removal, multisite-aware), a "Test connection"
  AJAX check, a Settings link on the Plugins list, `languages/` with a
  `.pot` template plus a compiled `fa_IR` translation (`.po` + `.mo`), and
  `index.php` directory-listing guards in every subfolder.

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
