"""Admin surface — GDPR-style data governance (M11: REQ-M11-006):
right-to-erasure, data export, and per-tenant tracking opt-out."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/tenants/{tenant_id}/erase")
async def erase_tenant_data(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Erase a tenant's data across index, memory, and logs (right to be forgotten)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    s = get_settings()
    es = get_es_client()
    erased: dict[str, Any] = {}
    query = {"query": {"term": {"tenant_id": tenant_id}}}
    for index in (s.catalogue_alias, f"{s.es_index_prefix}-chatmem", f"{s.es_index_prefix}-events"):
        try:
            await es.delete_by_query(index=index, body=query, conflicts="proceed")
            erased[index] = "ok"
        except Exception:  # noqa: BLE001 - index may not exist yet
            erased[index] = "skipped"
    redis = get_redis()
    if redis is not None:
        for pattern in (
            f"chatmem:{tenant_id}:*",
            f"l2:{tenant_id}",
            f"synonyms:{tenant_id}",
            f"data_version:{tenant_id}",
        ):
            try:
                async for key in redis.scan_iter(match=pattern):
                    await redis.delete(key)
            except Exception:  # noqa: BLE001
                pass
    pool = await get_pg_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM leads WHERE tenant_id = $1", tenant_id)
    except Exception:  # noqa: BLE001
        pass
    await audit(pool, actor="operator", action="tenant.erase", tenant_id=tenant_id, detail=erased)
    return {"tenant_id": tenant_id, "erased": erased, "status": "erased"}


@router.get("/tenants/{tenant_id}/export")
async def export_tenant_data(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Export a tenant's portable data (PII included for the data subject)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    leads: list[dict[str, Any]] = []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT email, phone, has_intent, source, created_at "
                "FROM leads WHERE tenant_id = $1",
                tenant_id,
            )
            leads = [dict(r) for r in rows]
    except Exception:  # noqa: BLE001
        leads = []
    return {"tenant_id": tenant_id, "leads": leads}


@router.post("/tenants/{tenant_id}/tracking")
async def set_tracking(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Enable/disable behavioural capture for a tenant (REQ-M11-006)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    enabled = bool(payload.get("enabled", True))
    pool = await get_pg_pool()
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE tenants SET tracking_enabled = $1 WHERE id = $2", enabled, tenant_id
            )
    except Exception:  # noqa: BLE001
        pass
    await audit(
        pool,
        actor="operator",
        action="tenant.tracking",
        tenant_id=tenant_id,
        detail={"enabled": enabled},
    )
    return {"tenant_id": tenant_id, "tracking_enabled": enabled}
