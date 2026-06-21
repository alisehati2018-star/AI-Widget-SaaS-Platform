# Runbook — Backup & Restore (Phase F)

Scope: control-plane **PostgreSQL** (tenants, users, plans, subscriptions,
orders, invoices, credit ledger, audit log) and **Redis** (cache/queue —
rebuildable). **Elasticsearch** snapshots use the ES snapshot API and are wired
when the cluster is connected (deferred).

## What to back up
- **PostgreSQL** — authoritative business data. **RPO target: ≤ 24h** (daily),
  tighten to hourly for production. **RTO target: ≤ 1h**.
- **Redis** — best-effort snapshot; safe to lose (caches + queues rebuild).
- **Secrets / `.env`** — stored in the secret store, backed up separately.

## Backup
```bash
PG_HOST=localhost PG_USER=acip PG_PASSWORD=acip PG_DB=acip \
  ./infra/backup.sh ./backups
# → ./backups/pg-acip-YYYYMMDD-HHMMSS.sql.gz  (+ redis SAVE)
```
Schedule daily via cron / a Kubernetes CronJob; ship the dump off-host
(object storage) and retain ≥ 30 days.

## Restore (PostgreSQL)
```bash
# 1. Stop the API/worker (or put the tenant plane in maintenance).
# 2. Restore into a clean database:
gunzip -c backups/pg-acip-YYYYMMDD-HHMMSS.sql.gz \
  | psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB"
# The dump uses --clean --if-exists, so it drops+recreates objects safely.
# 3. Verify:
psql -h "$PG_HOST" -U "$PG_USER" -d "$PG_DB" -c \
  "SELECT version FROM schema_migrations ORDER BY version;"
# 4. Restart services; confirm /readyz reports postgres: ok.
```

## Verify a backup (recommended monthly)
Restore the latest dump into a throwaway database and run the migration-version
check + a row-count sanity check. A backup is only valid once a restore has been
proven.

## Disaster recovery (DR) outline
1. Provision a fresh host / cluster (Docker Compose or K8s).
2. Restore Postgres from the latest off-host dump (above).
3. Re-create the Elasticsearch index from the catalogue sync (or ES snapshot,
   once snapshots are configured), then re-run a relevance smoke check.
4. Bring up api/gateway/worker; confirm `/readyz` and `/metrics`.
5. Run the billing renewal/dunning jobs once to reconcile any missed cycles.

## Observability during restore
- Watch `/metrics` (`vitrin_http_requests_total`, error rate) and `/readyz`.
- Prometheus alerts (`infra/alerts.yml`): `ApiDown`, `HighErrorRate`,
  `DependencyDegraded` should clear once the stack is healthy.
