# Phase F — Observability & Reliability — Completion Report

> Plan ref: `reports/recovery-plan-80plus.md` (RE-1..RE-4). Date 2026-06-21.
> Per owner instruction, **ES/inference-dependent validation is deferred** (true
> vLLM streaming / search KPIs validated later against the real ES server).
> Everything below is implemented + runtime-validated on the local stack.

## Delivered

### RE-1 — OpenTelemetry tracing
`acip_core.obs.setup_telemetry` instruments the FastAPI app (FastAPIInstrumentor)
with a `TracerProvider`. The OTLP exporter is **import-guarded** (optional pkg);
falls back to a console exporter when `OTEL_CONSOLE=true`; wrapped so tracing
**never breaks startup**. Config: `OTEL_ENABLED`, `OTEL_CONSOLE`,
`OTEL_EXPORTER_OTLP_ENDPOINT`.

### RE-1 — Prometheus metrics
Dependency-free in-process registry (`Metrics`: counters, gauges, latency
summaries) rendered at **`GET /metrics`** in Prometheus text format.
`MetricsMiddleware` records `vitrin_http_requests_total{method,status}` and
`vitrin_http_request_duration_seconds_{sum,count}{method}`; `/readyz` emits
`vitrin_readyz_ok` and `vitrin_dependency_up{dep}` gauges.

### RE-2 — Monitoring dashboards + alerts
- Admin **System health / Queue / Models / Usage / Security** pages (Phase B) are
  the operator dashboards; they now sit on top of the metrics + health feeds.
- `infra/prometheus.yml` (scrape config) + `infra/alerts.yml` (alert rules:
  `ApiDown`, `HighErrorRate`, `HighRequestLatency`, `DependencyDegraded`).

### RE-3 — Backups & DR
- `infra/backup.sh` — gzip `pg_dump` of the control plane + Redis `SAVE`
  (ES snapshot deferred). `docs/runbooks/backup-restore.md` — RPO/RTO targets,
  restore steps, monthly verify, and a DR outline.

### RE-4 — Scheduled jobs (reliability)
- Celery beat now schedules **daily** `acip.billing.process_renewals` and
  `acip.billing.run_dunning` (+ existing reconcile). New worker tasks execute the
  billing lifecycle automatically (admin can also trigger them on demand).

### IN-2 — note
True per-token vLLM streaming is inference-dependent and **deferred** with the ES
stack; the SSE endpoint + gateway abstraction remain in place.

## Runtime validation (live) — 16/16

| Check | Result |
|---|---|
| OTel instruments app at startup (`otel.instrumented`) | ✅ |
| `/metrics` exposes build_info + http counters + latency summary | ✅ |
| `/readyz` emits `vitrin_readyz_ok` + `vitrin_dependency_up{dep=postgres}=1` | ✅ |
| Request counter increments across calls (5→8) | ✅ |
| `infra/backup.sh` produces a non-empty pg dump with full schema | ✅ |
| Worker beat: 3 schedule entries + billing tasks registered | ✅ |
| Scheduled `process_renewals_task` / `run_dunning_task` execute vs live PG | ✅ |
| Regression smoke: headers, signup, profile, checkout, admin, **CSRF** intact | ✅ 6/6 |

## Gates
- `ruff` clean, `mypy` clean (91 files), **103 passed / 3 skipped** (+2 obs tests).
- Web unchanged (no frontend changes this phase) — prior build stands (47 routes).

## Score impact (per plan)
- **Reliability ~3 → ~8** (metrics, tracing, alerts, backups, scheduled jobs all
  live & validated), Observability now real.
- Projected overall: **~74 → ~79/100** (the last point to 80+ comes from Phase G
  validation; ES-dependent items stay deferred per instruction).

## Deferred (per owner instruction)
- Elasticsearch snapshots; search/RAG KPI + golden-set + load test (need the
  real ES server). True vLLM token streaming (needs the inference profile).
- Worker-level Celery inspect (active/scheduled) in the queue dashboard — the
  broker depth + reachability are shown today.
