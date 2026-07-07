"""Store-owner dashboard — GDPR self-serve: data export, tracking opt-out,
and self-service erasure (owner-only, confirmation-gated)."""

from __future__ import annotations

from typing import Any

from acip_auth.models import Role
from acip_core.audit import audit
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _owner_only, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/export")
async def export_data(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT email, phone, has_intent, source, created_at FROM leads WHERE tenant_id = $1",
            p.tenant_id,
        )
    return {"tenant_id": p.tenant_id, "leads": [dict(r) for r in rows]}


@router.post("/tracking")
async def set_tracking(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    enabled = bool(payload.get("enabled", True))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET tracking_enabled = $1 WHERE id = $2", enabled, p.tenant_id
        )
    await audit(
        pool,
        actor=p.email,
        action="tenant.tracking",
        tenant_id=p.tenant_id,
        detail={"enabled": enabled},
    )
    return {"tracking_enabled": enabled}


@router.post("/erase")
async def self_erase(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Erase the tenant's shopper-facing data (leads, chat memory, events, index
    docs). Requires an explicit confirmation matching the store slug."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        slug = await conn.fetchval("SELECT slug FROM tenants WHERE id = $1", p.tenant_id)
    if str(payload.get("confirm", "")) != slug:
        return error_response(
            422,
            "confirmation_required",
            f"Type your store slug '{slug}' to confirm erasure.",
        )
    es = get_es_client()
    erased: dict[str, Any] = {}
    query = {"query": {"term": {"tenant_id": p.tenant_id}}}
    for index in (s.catalogue_alias, f"{s.es_index_prefix}-chatmem", f"{s.es_index_prefix}-events"):
        try:
            await es.delete_by_query(index=index, body=query, conflicts="proceed")
            erased[index] = "ok"
        except Exception:  # noqa: BLE001
            erased[index] = "skipped"
    redis = get_redis()
    if redis is not None:
        for pattern in (
            f"chatmem:{p.tenant_id}:*",
            f"l2:{p.tenant_id}",
            f"synonyms:{p.tenant_id}",
            f"data_version:{p.tenant_id}",
        ):
            try:
                async for key in redis.scan_iter(match=pattern):
                    await redis.delete(key)
            except Exception:  # noqa: BLE001
                pass
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM leads WHERE tenant_id = $1", p.tenant_id)
    await audit(
        pool, actor=p.email, action="tenant.self_erase", tenant_id=p.tenant_id, detail=erased
    )
    return {"status": "erased", "detail": erased}
