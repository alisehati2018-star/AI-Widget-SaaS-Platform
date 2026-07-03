#!/usr/bin/env bash
# Vitrin restore (Phase 9). Restores a pg_dump made by infra/backup.sh into the
# control-plane database. The dump was taken with --clean --if-exists, so
# restoring over an existing database replaces its objects.
#
# Usage:
#   PG_HOST=localhost PG_USER=acip PG_PASSWORD=... PG_DB=acip \
#     ./infra/restore.sh backups/pg-acip-20260703-120000.sql.gz
#
# Elasticsearch is NOT restored here: the catalogue is rebuilt from the source
# stores (bulk import / reconciliation) or restored from an ES snapshot —
# see docs/DEPLOYMENT-SERVER.md §Backups.
set -euo pipefail

DUMP="${1:?usage: restore.sh <pg-dump.sql.gz>}"
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-acip}"
PG_DB="${PG_DB:-acip}"
export PGPASSWORD="${PG_PASSWORD:-acip}"

[ -f "$DUMP" ] || { echo "[restore] dump not found: $DUMP" >&2; exit 1; }

echo "[restore] restoring ${DUMP} into ${PG_DB} on ${PG_HOST}:${PG_PORT}"
gunzip -c "$DUMP" | psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -v ON_ERROR_STOP=1 -q
echo "[restore] verifying…"
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" -tAc \
  "SELECT 'tables: ' || count(*) FROM information_schema.tables WHERE table_schema='public';
   SELECT 'migrations: ' || count(*) FROM schema_migrations;
   SELECT 'tenants: ' || count(*) FROM tenants;"
echo "[restore] done."
