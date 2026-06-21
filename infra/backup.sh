#!/usr/bin/env bash
# Vitrin backup (Phase F). Dumps the control-plane Postgres DB (and triggers a
# Redis snapshot). Elasticsearch snapshots use the ES snapshot API and are wired
# when the cluster is connected (deferred).
#
# Usage:
#   PG_HOST=localhost PG_USER=acip PG_PASSWORD=acip PG_DB=acip ./infra/backup.sh [outdir]
set -euo pipefail

OUTDIR="${1:-./backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUTDIR"

PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-acip}"
PG_DB="${PG_DB:-acip}"
export PGPASSWORD="${PG_PASSWORD:-acip}"

PG_OUT="$OUTDIR/pg-${PG_DB}-${STAMP}.sql.gz"
echo "[backup] pg_dump ${PG_DB} -> ${PG_OUT}"
pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" --no-owner --clean --if-exists \
  | gzip > "$PG_OUT"
echo "[backup] postgres OK ($(du -h "$PG_OUT" | cut -f1))"

# Redis is a cache/queue (rebuildable), but snapshot it for completeness.
if command -v redis-cli >/dev/null 2>&1; then
  redis-cli -p "${REDIS_PORT:-6379}" SAVE >/dev/null 2>&1 && echo "[backup] redis SAVE OK" || \
    echo "[backup] redis snapshot skipped (not reachable)"
fi

echo "[backup] Elasticsearch snapshot: deferred (run via ES snapshot API once connected)."
echo "[backup] done -> ${PG_OUT}"
