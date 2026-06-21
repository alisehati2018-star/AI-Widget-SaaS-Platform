# Phase C — Mobile & UX — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (UX-1..UX-5). Date 2026-06-21.
> Frontend-only (no backend changes). Built + served + validated.

## Delivered

### UX-1 — Mobile navigation
`DashboardShell` now has an off-canvas drawer: a `.mobile-topbar` with a
hamburger (`☰`) opens the sidebar as an overlay with a backdrop; a close (`✕`)
button and backdrop-click dismiss it; the drawer auto-closes on route change.
Desktop layout is unchanged. (Previously the sidebar was `display:none` on
mobile with **no** replacement — dashboards were unusable on phones.)

### UX-2 — RTL + direction toggle
`DirectionInit` (in the root layout) applies the saved direction on load;
`DirectionToggle` (marketing nav + dashboard shell) flips `<html dir/lang>`
between LTR/EN and RTL/FA and persists it. The design system's `[dir="rtl"]`
rules (sidebar side, table alignment, drawer slide-in side, background) activate
accordingly. On-prem friendly: no external font fetch (Persian renders via the
system font stack; Vazirmatn used if installed).

### UX-3 — Accessibility
Skip-to-content link, `:focus-visible` outlines, `aria-label`s on icon buttons
(hamburger, close, direction toggle), `aria-current="page"` on the active nav
item, `role="navigation"`/`progressbar`/`status`/`alert`, and `aria-live` on the
loading state.

### UX-4 — Consistent states
New `components/states.tsx`: `Loading`, `EmptyState`, `ErrorState` primitives
(used by onboarding; available platform-wide for adoption).

### UX-5 — Onboarding wizard
`/onboarding`: a 4-step guided flow (verify email → connect store → create keys →
install widget) with a live progress bar computed from `/tenant/profile` +
`/tenant/keys`. New signups land here; the dashboard "Finish setting up" card
links to it. Each step shows done/▢ state and a contextual CTA (or inline
resend-verification action).

## QA pass (full)

| Check | Result |
|---|---|
| Web `tsc` clean | ✅ |
| `next build` — **47 routes** (+/onboarding) | ✅ |
| HTTP-200 sweep across 19 key routes (regression) | ✅ |
| Compiled CSS carries mobile-topbar / skip-link / progress-fill / sidebar-backdrop / `[dir=rtl]` | ✅ |
| Shell markup in JS bundle: "Skip to content", "Open/Close menu", sidebar-backdrop, progressbar, direction aria | ✅ |
| Marketing nav renders RTL toggle (فا) | ✅ |
| **Onboarding data flow 0%→100%** (email→connect→keys) live | ✅ 6/6 |
| Backend regression: `ruff` clean, **99 passed** | ✅ |

Note: `/dashboard` static HTML shows the loading spinner (client-guarded), so
shell chrome was verified in the compiled JS bundle rather than prerendered HTML
— expected, not a defect.

## Score impact (per plan)
- **UI/UX ~5 → ~8.5** (mobile nav fixed, RTL activated, a11y, states, onboarding).
- Projected overall: **~66 → ~70/100**.

## Carried
- Full string-level i18n (Persian translations) beyond direction + font is out of
  scope; the toggle delivers correct RTL layout (the audited gap "RTL never
  activated"). Tracked for a later localization pass.
- Broader adoption of the state primitives across all existing pages (they
  already have working spinners/empty messages) — incremental.
