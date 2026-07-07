"""Store-owner dashboard — API keys (list / create / revoke), tenant-scoped."""

from __future__ import annotations

import secrets
from typing import Any

from acip_auth.models import Role
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from ..deps import hash_key
from .tenant_common import _AUTHZ, _COOKIE, _owner_only, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/keys")
async def list_keys(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, scope, label, revoked, created_at, last_used_at FROM api_keys "
            "WHERE tenant_id = $1 ORDER BY created_at DESC",
            p.tenant_id,
        )
    return {
        "keys": [
            {
                "id": str(r["id"]),
                "scope": r["scope"],
                "label": r["label"],
                "revoked": r["revoked"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/keys")
async def create_key(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    scope = str(payload.get("scope", "widget"))
    if scope not in ("widget", "sync"):
        return error_response(422, "invalid_request", "scope must be 'widget' or 'sync'.")
    label = str(payload.get("label", "")).strip() or scope
    raw_key = "acip_" + secrets.token_urlsafe(24)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO api_keys (tenant_id, key_hash, scope, label) VALUES ($1, $2, $3, $4)",
            p.tenant_id,
            hash_key(raw_key),
            scope,
            label,
        )
    await audit(
        pool,
        actor=p.email,
        action="key.create",
        tenant_id=p.tenant_id,
        detail={"scope": scope, "label": label},
    )
    return {"api_key": raw_key, "scope": scope, "label": label}


@router.post("/keys/{key_id}/revoke")
async def revoke_key(
    key_id: str, authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET revoked = TRUE WHERE id = $1 AND tenant_id = $2",
            key_id,
            p.tenant_id,
        )
    await audit(
        pool, actor=p.email, action="key.revoke", tenant_id=p.tenant_id, detail={"key_id": key_id}
    )
    return {"status": "revoked"}
