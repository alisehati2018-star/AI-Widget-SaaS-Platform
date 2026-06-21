# ACIP / Vitrin — Product Recovery & 80+ Execution Plan

> Source of truth: `docs/PRODUCT.md` + `docs/PRODUCT-STRATEGY.md` (retired
> "blueprint"), `reports/blueprint-compliance-audit.md`,
> `reports/gap-closure-audit.md`, the Product/UI/Dashboard audit, the phase
> reports, and the current source (HEAD `9d9c984`).
>
> Goal: raise Product ≥8, Security ≥8, Dashboard ≥8, SaaS ≥8, Production
> Readiness ≥8 → **overall ≥80/100**. This is an execution plan only — no code
> is written until it is approved. Baseline (from the audit) = **47/100**.

## Locked decisions (owner, this revision)

1. **Billing: manual only.** No live payment gateway (Stripe/ZarinPal) this
   cycle. BI-1 (real gateway) moves **P0 → P3 (deferred)**. Phase E is rescoped
   to everything achievable on the manual/invoice model: subscription lifecycle,
   credit top-up as a manual order, invoices/receipts, dunning, and a
   **signature-verified webhook simulation** to prove the activation path.
   *Consequence:* Billing realistically caps at **~7.0–7.5** (no live card
   capture), so **overall ≥80 is reached at Phase G, not Phase F** (see Phase 3).
2. **Auth cutover: dual-support window.** Phase D adds httpOnly+SameSite cookie
   auth **alongside** the existing bearer/localStorage, ships behind a flag,
   then removes localStorage only after the E2E suite (Phase G) is green.
3. **Proceed:** plan revised first (this document); implementation begins only
   on explicit approval.

---

## Phase 0 — Reassessment & Consolidated Gap Inventory

Verified repo state at HEAD `9d9c984`: 8 routers (auth, tenant, billing, admin,
public, v1, health), 6 migrations, 29 web pages, 16 hermetic test files, 0
runtime validation, 0 frontend/E2E tests. Static gates green.

Consolidated gaps grouped by domain (each carries an ID used in traceability):

### Product (PR)
- PR-1 Documentation page missing.
- PR-2 Legal pages (Terms, Privacy, DPA) missing.
- PR-3 Email verification flow missing (`email_verified` never set true).
- PR-4 Contact form non-functional (local `setTimeout`, no endpoint/delivery).
- PR-5 Transactional email absent (verify, reset, invite, contact).
- PR-6 Widget deployment flow incomplete (placeholder CDN host; no real loader/CORS).

### UI/UX (UX)
- UX-1 Mobile dashboards have no navigation (sidebar hidden, no drawer).
- UX-2 RTL never activated (`lang="en"`, no `dir`/i18n) for a Persian-first product.
- UX-3 Accessibility weak (focus, aria, color-only status, skip links).
- UX-4 Inconsistent loading/empty/error states on some pages.
- UX-5 No guided onboarding wizard.

### Dashboard — User (DU)
- DU-1 Chat Analytics page missing.
- DU-2 Sales Analytics page missing.
- DU-3 Knowledge Base management missing.
- DU-4 Dedicated Credits / usage-history page missing.
- DU-5 User-side Audit Log missing.
- DU-6 Team management partial (no remove / role-edit).
- DU-7 GDPR self-serve erase missing.

### Dashboard — Admin (AD)
- AD-1 Security Monitoring page missing (failed logins/lockouts/anomalies).
- AD-2 Synonym Management UI missing (backend exists).
- AD-3 Feature Flags system + UI missing.
- AD-4 System Health page missing (`/readyz` exists, no UI).
- AD-5 Queue Monitoring missing.
- AD-6 Model/Gateway Monitoring missing.
- AD-7 Usage Monitoring dashboard missing.
- AD-8 Admin actions mostly read-only (no suspend / role / plan-edit).

### Security (SE)
- SE-1 Tokens in `localStorage` (XSS → token theft). **Highest standing risk.**
- SE-2 No security headers (CSP, HSTS, X-Frame-Options, Referrer-Policy).
- SE-3 Input validation weak (`dict[str,Any]`, no Pydantic request models).
- SE-4 No IP-based rate limiting on login/signup/reset.
- SE-5 No MFA/2FA.
- SE-6 No CORS policy (widget cross-origin `/v1/*` blocked).
- SE-7 GDPR incomplete (retention, consent records).

### Billing (BI)
- BI-1 No real payment gateway (manual only; `redirect_url` stubbed).
- BI-2 Subscription lifecycle UI incomplete (upgrade/downgrade/cancel).
- BI-3 No credit top-up purchase.
- BI-4 No invoice artifacts (PDF/receipt) or dunning.

### Analytics (AN)
- AN-1 Chat/sales breakdowns absent (see DU-1/DU-2).
- AN-2 Attribution/insight surfaces unverified at runtime.
- AN-3 No global admin analytics aggregation.

### Reliability (RE)
- RE-1 Observability not wired (OTel deps unused; no exporter).
- RE-2 No monitoring/alerting.
- RE-3 No backups / DR.
- RE-4 Resilience primitives unexercised; no load test.

### Infrastructure (IN)
- IN-1 No runtime bring-up validated (PG/ES/Redis).
- IN-2 Assistant SSE streaming faked (`.split()`), not true vLLM streaming.
- IN-3 CI lacks integration/E2E execution against services.

### Validation (VA)
- VA-1 No real Persian golden set / NDCG validation.
- VA-2 KPIs (search p95, first-token) never measured.
- VA-3 Cost-regression replay not run.
- VA-4 Tenant-isolation only unit-tested, not runtime-proven.
- VA-5 Zero frontend/E2E tests.

---

## Phase 1 — Gap Prioritization

### P0 — Critical (block 80+)
| ID | Reason |
|---|---|
| IN-1 | Nothing is proven until the stack runs; gates every "Functional" score. |
| SE-1, SE-2, SE-3 | XSS token theft, missing headers, weak validation — block Security ≥8. |
| SE-4, SE-6 | Brute-force exposure + widget can't function cross-origin. |
| PR-3, PR-5 | Email verification + transactional email are SaaS table stakes. |
| UX-1 | Dashboards unusable on mobile — blocks Dashboard/UX ≥8. |
| BI-2, BI-3, BI-4 | Subscription lifecycle + top-up + invoices on the **manual** model — needed for SaaS ≥8 (BI-1 real gateway deferred to P3 by decision). |
| DU-1, DU-2, DU-4, DU-5 | Core user value (analytics + credits + audit) — blocks Dashboard ≥8. |
| AD-1, AD-4, AD-7 | Ops can't run the platform without security/health/usage views. |
| RE-1, RE-2 | No observability → not production-grade reliability. |
| VA-1, VA-2, VA-4, VA-5 | Acceptance evidence; without it scores stay capped. |
| PR-2 | Legal pages required to lawfully accept signups. |

### P1 — High
PR-1 (docs), PR-4/PR-6 (contact + widget loader), UX-2 (RTL), UX-4 (states),
DU-3 (KB), DU-6/DU-7 (team/GDPR), AD-2/AD-5/AD-6/AD-8 (synonym UI, queue, model,
admin actions), AN-3, RE-4 (load test), IN-2 (true streaming), VA-3 (cost replay).

### P2 — Medium
UX-3 (a11y depth), UX-5 (onboarding wizard), AD-3 (feature flags), BI-4 (invoice
PDF/dunning), SE-7 (retention/consent), AN-2 hardening.

### P3 — Future
**BI-1 (live payment gateway — deferred by owner decision)**, SE-5 (MFA —
strongly recommended but can trail GA), multi-region, advanced recommender/
visual search (v2 per strategy), white-label theming depth.

---

## Phase 2 — Execution Roadmap

> Each phase ends with: audit → tests → gap-analysis → completion report →
> recalculated scores → **STOP for approval** (Phase 7 rules).

### Phase A — Product Completeness (P0/P1)
- **Goal:** every public surface a real SaaS needs, working.
- **Scope:** PR-1..PR-6.
- **Deliverables:** `/docs`, `/legal/terms`, `/legal/privacy`; email-verification
  flow (token + `/auth/verify`); transactional email service (pluggable SMTP;
  console-fallback in dev) wired to verify/reset/invite/contact; functional
  contact endpoint; widget loader endpoint + CORS allowlist.
- **Dependencies:** SE-6 (CORS), email infra (shared with Phase D/E).
- **Acceptance:** signup → verification email → verified login; contact submits
  to backend + audited; legal/docs reachable from nav/footer; widget loads on a
  cross-origin test page.
- **Impact:** Product +2.0, SaaS +0.5.

### Phase B — Dashboard Completion (P0/P1)
- **Goal:** user + admin dashboards feature-complete.
- **Scope:** DU-1..DU-7, AD-1..AD-8.
- **Deliverables:** user Chat/Sales Analytics, Credits & usage history, user
  Audit Log, KB management, team remove/role-edit, GDPR self-erase; admin
  Security Monitoring, Synonym UI, System Health, Queue, Model/Gateway, Usage
  dashboards, feature-flag UI, admin write-actions (suspend/role/plan-edit).
- **Dependencies:** RE-1 (metrics feed health/usage), backend read endpoints.
- **Acceptance:** every page in the audit's three tables renders real data (or a
  correct empty state) from a live endpoint; no read-only-only admin.
- **Impact:** Dashboard +3.0, Admin +3.0, Analytics +1.5.

### Phase C — Mobile & UX (P0/P1/P2)
- **Goal:** usable on mobile; consistent states; RTL.
- **Scope:** UX-1..UX-5.
- **Deliverables:** responsive nav drawer in `shell.tsx`; activate RTL +
  language toggle + Vazirmatn font; standardized Loading/Empty/Error components;
  onboarding wizard; a11y pass (focus, aria, contrast, skip link).
- **Dependencies:** none (frontend-only).
- **Acceptance:** Lighthouse mobile ≥90 perf/a11y on key pages; full nav at
  375px; RTL renders correctly for Persian.
- **Impact:** UI/UX +2.5, Dashboard +0.5.

### Phase D — Security Hardening (P0/P1) — *dual-support cookie window*
- **Goal:** Security ≥8.
- **Scope:** SE-1..SE-7.
- **Deliverables:** httpOnly+SameSite cookie auth **added alongside** the existing
  bearer/localStorage behind a flag (dual-support); `/auth/*` issues cookies +
  CSRF token; web client prefers cookies; localStorage path retained until Phase
  G E2E is green, then removed. Plus: security-headers middleware (CSP, HSTS,
  X-Frame-Options, Referrer-Policy, nosniff); Pydantic request models on all
  routers; IP rate-limit on auth/signup/reset; CORS allowlist; CSRF protection
  for cookie flows; GDPR retention + consent records; MFA/TOTP (P3, optional).
- **Dependencies:** Phase A email (for MFA backup); RE-1 (audit→metrics).
- **Acceptance:** security-header scan A grade; cookie-auth path works end-to-end
  with CSRF; bearer path still green during the window; every endpoint validates
  via a schema; brute-force test blocked by IP limit. *localStorage removal is a
  Phase-G exit item.*
- **Impact:** Security +3.0.

### Phase E — Billing & SaaS Operations (P0/P1) — *manual model only*
- **Goal:** complete, auditable monetization + self-service on the manual/invoice
  model (no live card capture this cycle).
- **Scope:** BI-2, BI-3, BI-4 (BI-1 deferred to P3).
- **Deliverables:** subscription lifecycle (upgrade/downgrade/cancel with
  period-end downgrade + proration math); credit **top-up** as a manual order;
  invoice/receipt artifact (PDF + email via Phase A); dunning on `past_due`;
  a **signature-verified webhook simulation** (using the existing
  `/billing/webhook` + `BILLING_WEBHOOK_SECRET`) to prove paid→activate→grant
  without an external provider. Owner can later drop a real gateway into the
  same webhook (BI-1) with no schema change.
- **Dependencies:** Phase D (webhook signing, validation), Phase A (email).
- **Acceptance:** simulated signed webhook → subscription active → credits
  granted → invoice emailed; upgrade/downgrade/cancel reflected in tenant state;
  dunning marks/notifies `past_due`. *No live PSP integration is in scope.*
- **Impact:** Billing +2.0 (capped at ~7.0 without live capture), SaaS +1.5.

### Phase F — Observability & Reliability (P0/P1)
- **Goal:** Reliability ≥8.
- **Scope:** RE-1..RE-4, IN-2.
- **Deliverables:** wire OTel (FastAPIInstrumentor + OTLP exporter); Prometheus
  metrics; health/queue/model dashboards (feed Phase B admin pages); alert rules;
  backup/restore runbook + scheduled PG/ES snapshots; true vLLM token streaming;
  load test harness.
- **Dependencies:** IN-1 running stack.
- **Acceptance:** traces visible; alerts fire on synthetic failure; restore from
  backup verified; SSE streams real tokens; load test produces p95 numbers.
- **Impact:** Reliability +4.0, Assistant +1.0.

### Phase G — Validation & Acceptance (P0/P1)
- **Goal:** prove the KPIs and isolation; add test layers.
- **Scope:** VA-1..VA-5, IN-1, IN-3.
- **Deliverables:** docker compose bring-up validated; ~50-query Persian golden
  set + NDCG@10 run; KPI measurement (search p95<150ms, first-token<1.5s);
  cost-regression replay; runtime tenant-isolation test; Playwright E2E suite +
  CI integration job against service containers.
- **Dependencies:** all prior phases (validates them).
- **Acceptance:** KPIs measured + documented in `reports/`; isolation test green
  on a live cluster; E2E suite green in CI.
- **Impact:** Production Readiness +4.0, Search +1.0, validation unlocks capped scores.

---

## Phase 3 — Score Projection

> Revised for **manual-only billing**: Billing caps at ~7.0–7.5 (no live card
> capture), so the overall crosses 80 **during Phase G**, not Phase F.

| Phase | Product | Security | Dashboard | Billing | Analytics | Reliability | Overall /100 |
|---|---|---|---|---|---|---|---|
| Baseline | 6.5 | 5 | 4.5 | 5 | 4 | 3 | **47** |
| +A | 8.0 | 5 | 4.5 | 5 | 4 | 3 | 52 |
| +B | 8.0 | 5 | 7.5 | 5 | 6 | 3 | 60 |
| +C | 8.5 | 5 | 8.0 | 5 | 6 | 3 | 64 |
| +D | 8.5 | 8.5 | 8.0 | 5.5 | 6 | 3 | 70 |
| +E | 8.5 | 8.5 | 8.0 | 7.0 | 6 | 4 | 74 |
| +F | 8.5 | 8.5 | 8.5 | 7.0 | 7 | 8.0 | 79 |
| +G | 9.0 | 9.0 | 8.5 | 7.5 | 8.0 | 8.5 | **84** |

Target (≥80) is reached **at Phase G** (84/100). Billing is the one category that
stays at ~7.5 by design (manual model); every other category reaches ≥8, so the
overall clears 80 comfortably. If the owner later enables a live gateway (BI-1),
Billing rises to ~8.5 and overall to ~86.

---

## Phase 4 — Detailed Task Breakdown (Epic → Feature → Task → Subtask)

> Abbreviated to representative epics per phase with files + acceptance. Full
> task IDs (`T-A-001` …) are assigned at phase kickoff.

### Phase A
- **Epic A1 — Transactional email + verification**
  - Feature: email service. Task: `packages/acip_notify/` SMTP+console provider.
    Files: new package, `config.py`. AC: dev logs email; prod sends SMTP.
  - Feature: verify flow. Task: `/auth/verify-request`, `/auth/verify-confirm`,
    set `email_verified`. Files: `routers/auth.py`, migration (verify tokens).
    AC: unverified users gated from sensitive actions.
- **Epic A2 — Public pages.** Tasks: `/docs`, `/legal/terms`, `/legal/privacy`,
  real `/contact` (`routers/public.py` POST). Files: `apps/web/app/*`,
  `components/marketing.tsx`. AC: reachable, submit persists+audits.
- **Epic A3 — Widget loader + CORS.** Files: `routers/v1.py` (CORS), widget host.

### Phase B
- **Epic B1 — User analytics.** Tasks: Chat Analytics, Sales Analytics, Credits
  history pages + backend `/tenant/usage`, `/tenant/credits`. Files:
  `apps/web/app/dashboard/*`, `routers/tenant.py`, `acip_billing`.
- **Epic B2 — User audit + GDPR.** Tasks: `/tenant/audit`, self-erase. Files:
  `routers/tenant.py`, `apps/web/app/dashboard/audit`, `.../settings`.
- **Epic B3 — Admin ops pages.** Tasks: Security, Health, Queue, Model, Usage,
  Synonym UI, Feature Flags, write-actions. Files: `routers/admin.py`,
  `apps/web/app/admin/*`, new `feature_flags` table.

### Phase C
- **Epic C1 — Responsive shell.** Files: `components/shell.tsx`, `globals.css`.
- **Epic C2 — RTL + i18n.** Files: `app/layout.tsx`, locale toggle, font.
- **Epic C3 — State primitives + onboarding.** Files: `components/ui.tsx`, new
  `components/states.tsx`, onboarding route.

### Phase D
- **Epic D1 — Cookie auth.** Files: `routers/auth.py` (Set-Cookie), `lib/auth.tsx`
  (drop localStorage), CSRF token endpoint.
- **Epic D2 — Headers + CORS middleware.** Files: `services/api/main.py`,
  `packages/acip_core/middleware.py`.
- **Epic D3 — Pydantic validation.** Files: all `routers/*.py` (request models).
- **Epic D4 — IP rate limiting + MFA(opt).** Files: `acip_core/ratelimit.py`,
  `routers/auth.py`.

### Phase E (manual model)
- **Epic E1 — Webhook simulation + activation proof.** Files: `routers/billing.py`,
  `eval/` or a test helper that POSTs a signed body. AC: signed webhook →
  paid → activate → grant, verified in an integration test.
- **Epic E2 — Lifecycle + top-up + invoices + dunning.** Files:
  `acip_billing/subscription.py`, `routers/billing.py`, `packages/acip_notify`
  (invoice email/PDF), dashboard billing page, admin billing page. AC:
  upgrade/downgrade/cancel + manual top-up order + emailed receipt + `past_due`
  dunning all work and are audited.

### Phase F
- **Epic F1 — OTel + metrics.** Files: `services/api/main.py`, `acip_core/obs.py`.
- **Epic F2 — Monitoring dashboards + alerts.** Files: admin pages, infra.
- **Epic F3 — Backups/DR + true streaming + load test.** Files: `infra/`,
  `acip_gateway/llm_client.py`, `eval/load_test.py`.

### Phase G
- **Epic G1 — Runtime bring-up + golden set + KPIs.** Files: `eval/`, `reports/`.
- **Epic G2 — E2E + CI integration.** Files: `apps/web/e2e/`, `.github/workflows/ci.yml`.

---

## Phase 5 — Risk Analysis

| Risk | Type | Rank | Mitigation |
|---|---|---|---|
| Runtime bring-up reveals integration defects | Technical/Validation | **Critical** | Do IN-1 first (Phase G pre-flight); fix before scoring. |
| Cookie-auth migration breaks existing flows | Architecture/Security | High | **Dual-support window (decided):** cookie added alongside bearer; remove localStorage only after Phase-G E2E green. |
| Manual-only billing caps Billing/SaaS score | Product/Billing | Medium | Accepted by owner; Billing held at ~7.5; overall still ≥80 at Phase G; BI-1 drop-in later raises it. |
| Persian golden set quality (no pilot store) | Validation | High | Seed from synthetic + real queries; document confidence. |
| OTel/monitoring infra overhead on single host | Reliability | Medium | Lightweight exporters; sampling. |
| RTL/i18n regressions in shared components | UX | Medium | Snapshot tests; logical CSS properties. |
| Pydantic model rollout churn across routers | Technical | Medium | Mechanical, test-covered; do per-router. |
| MFA scope creep | Security/Product | Low | Keep P3; ship TOTP only if time allows. |

---

## Phase 6 — Completion Definition (measurable)

### MVP Ready
- Stack runs via `docker compose up`; signup→verify→login works end-to-end.
- All P0 dashboard/admin pages render real data or correct empty states.
- Security headers present; cookie-auth available (localStorage removal tracked
  to Phase G); legal pages live.
- Manual purchase path works end-to-end: order → operator confirm (or signed
  webhook sim) → subscription active → credits granted. Unit + smoke E2E in CI.

### Beta Ready
- All P0 + P1 complete. KPIs measured (p95, first-token) on a seeded catalogue.
- Observability live (traces+metrics+alerts). Backups verified.
- E2E suite covers auth/billing/dashboard. Tenant isolation proven at runtime.
- Overall score ≥80/100.

### Production Candidate
- Load test meets SLOs; cost-regression replay within budget; DR runbook tested.
- Security review (Part 5) clean of Critical/High; MFA available.
- Zero P0/P1 open; ≤ a handful of P2.

### Production Ready
- 99.9% availability demonstrated in staging soak; on-call/alerting wired.
- Full audit re-run scores ≥8 in every category; sign-off recorded in `reports/`.

---

## Phase 7 — Execution Rules & Traceability

**Before coding (this deliverable):** plan ✅, gap inventory ✅, prioritization ✅,
traceability below ✅ — every audit finding maps to a phase/task; no blueprint
requirement dropped (search/RAG/analytics/gateway from Phases 0–4 remain, now
validated in Phase G).

**Per-phase loop:** implement only that phase → `ruff`/`mypy`/`pytest` +
`tsc`/`next build` → `reports/phase-<X>-gap-analysis.md` → re-run relevant audit
→ `reports/phase-<X>-completion-report.md` → recalculate scores → **STOP for
approval.**

### Traceability matrix (gap → phase)
| Gap IDs | Phase |
|---|---|
| PR-1..PR-6 | A |
| DU-1..DU-7, AD-1..AD-8, AN-1/AN-3 | B |
| UX-1..UX-5 | C |
| SE-1..SE-7 | D |
| BI-1..BI-4 | E |
| RE-1..RE-4, IN-2 | F |
| VA-1..VA-5, IN-1, IN-3, AN-2 | G |

No audit finding is unmapped; no P0 gap lacks a task.

---

## Recommended sequence & gating decisions

Decisions are now **locked** (see top): manual billing, dual-support cookie
window. No further gating decisions block kickoff. Recommended order:

1. **G-preflight (IN-1 bring-up) first** — `docker compose up`, migrations apply,
   `/readyz` healthy — so every later phase is validated as built, not at the end.
2. Then **A → D → B → C → E → F → G**, running the per-phase loop (audit → tests →
   gap-analysis → completion report → re-score) and **stopping for approval**
   after each.
3. Overall ≥80 is achieved at Phase G (projected 84/100).
