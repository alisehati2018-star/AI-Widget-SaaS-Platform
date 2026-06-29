# Frontend Modernization Roadmap (Locked)

Single source of truth for the frontend overhaul of `apps/web` (Next.js 16,
React 19). Locked decisions: **next-intl, locale-routed, Persian-first**;
**Jalali (Shamsi) dates**; **dark-only theme**. Each phase ends green on
build + runtime + regression before the next begins.

## Locked architectural decisions
- **i18n:** `next-intl` v4, locale-routed. `defaultLocale: "fa"`,
  `localePrefix: "as-needed"` → Persian at clean root URLs (`/`, `/pricing`),
  English prefixed (`/en/...`). Locale persisted via `NEXT_LOCALE` cookie.
- **Namespaces (domain-based, no monolith):** `common`, `marketing`, `auth`,
  `dashboard`, `admin`, `billing`, `errors`, `validation`. Client components get
  only the namespaces their route needs via scoped `NextIntlClientProvider`.
- **Dates/numbers:** one abstraction (`lib/datetime.ts`) — `formatDate`,
  `formatDateTime`, `formatNumber`, `formatCurrency`. fa → Jalali via ICU
  (`Intl` `calendar: "persian"`); en → Gregorian. No manual conversion, no
  duplicate date logic. The module is the single swap point for the engine.
- **Direction:** derived from locale (`fa`=rtl, `en`=ltr), server-rendered on
  `<html dir lang>` — no client flash.

## Audit headlines (pre-work state)
- No i18n system; all strings hardcoded English; the "فا" toggle only flipped
  `dir` (RTL English). Persian font referenced but never loaded.
- Tables had no responsive strategy (admin horizontal-scroll risk).
- Numbers/dates not localized; marketing thin; no `public/` assets; no FE
  quality tooling.
- Components were already small/clean (largest 227 lines) — the real
  architecture win is shared hooks/primitives, not file splitting.

## Phases
- **Phase 0 — Foundation & tooling:** next-intl wiring (routing/request/
  navigation/middleware/plugin), 8×2 namespace files, fonts (Vazirmatn/Inter),
  `public/` assets, `lib/datetime.ts`, i18n QA scripts (parity / unused /
  hardcoded / missing), ESLint, roadmap commit.
- **Phase 1 — Internationalization:** move all routes under `app/[locale]/`,
  swap to locale-aware navigation, externalize every string into namespaces,
  localized numbers + Jalali dates + currency + validation/error messages,
  locale switch replacing `direction.tsx`. Decompose where useful; shared
  primitives; no duplicate logic.
- **Phase 2 — Architecture:** `useResource` data hook, Modal/Toast/responsive
  Table primitives, feature-folder grouping.
- **Phase 3 — Marketing redesign.** **Phase 4 — Dashboard UX.**
  **Phase 5 — Admin redesign (kill horizontal scroll).**
  **Phase 6 — Responsive.** **Phase 7 — Content.** **Phase 8 — Design polish.**
  **Phase 9 — FE QA automation.**

## Quality gates (every phase)
Build (`next build`) · runtime walkthrough (EN + FA) · regression (backend
integration suite unaffected; cookie-auth flow intact) · i18n checks at zero.

## Git strategy
Roadmap committed here. Each phase (and build-green slice within a phase) is a
separate, traceable commit on `claude/gallant-shannon-8b31td`.
