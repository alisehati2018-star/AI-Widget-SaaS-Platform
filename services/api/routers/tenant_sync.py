"""Store-owner dashboard — catalogue sync status + manual "sync now" trigger."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth
from .tenant_search import _tenant_docs

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/sync-status")
async def sync_status(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    """Per-source sync watermarks + the live indexed-document count from ES
    (degraded-safe: docs is null when the cluster is unreachable)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT source, high_watermark, last_run_at, last_status FROM sync_state "
            "WHERE tenant_id = $1 ORDER BY source",
            p.tenant_id,
        )
    docs, degraded = await _tenant_docs(p.tenant_id)
    return {
        "sources": [
            {
                "source": r["source"],
                "high_watermark": r["high_watermark"].isoformat() if r["high_watermark"] else None,
                "last_run_at": r["last_run_at"].isoformat() if r["last_run_at"] else None,
                "last_status": r["last_status"],
            }
            for r in rows
        ],
        "docs_indexed": docs,
        "degraded": degraded,
    }


@router.post("/sync/trigger")
async def sync_trigger(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Queue an immediate reconciliation run ("sync now"). The request is
    recorded in sync_state right away so the dashboard reflects it even before
    a worker picks the task up."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    source = str(payload.get("source", "") or "rest").strip().lower()
    if source not in ("opencart", "woocommerce", "rest"):
        return error_response(422, "invalid_request", "source must be opencart/woocommerce/rest.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO sync_state (tenant_id, source, last_run_at, last_status) "
            "VALUES ($1, $2, now(), 'queued') "
            "ON CONFLICT (tenant_id, source) "
            "DO UPDATE SET last_run_at = now(), last_status = 'queued'",
            p.tenant_id,
            source,
        )
    queued = True
    try:
        from worker.tasks import reconcile_tenant

        reconcile_tenant.delay(p.tenant_id, source)
    except Exception:  # noqa: BLE001 - broker down: the request stays recorded
        queued = False
    await audit(
        pool,
        actor=p.email,
        action="sync.trigger",
        tenant_id=p.tenant_id,
        detail={"source": source, "queued": queued},
    )
    return {"status": "queued" if queued else "recorded", "source": source}
