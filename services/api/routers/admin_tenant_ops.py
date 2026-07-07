"""Operator/admin API surface — per-tenant mutations: notes, API keys,
manual credit adjustment, plan changes, and suspend/reactivate.

Tenant creation, the platform overview, the tenant list, and the tenant
detail view live in `admin.py`.
"""

from __future__ import annotations

import secrets
from typing import Any

from acip_billing import usage_summary as _usage_summary
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from ..deps import hash_key
from .admin_common import (
    _ADMIN,
    _AUTHZ,
    _COOKIE,
    _admin_ok,
    _admin_write_rate_ok,
    _forbidden,
    _key_rows,
    _not_found,
    _valid_uuid,
)

_RATE_LIMITED = ("rate_limited", "Too many mutations for this tenant. Slow down and retry.")

router = APIRouter(prefix="/admin", tags=["admin"])


@router.patch("/tenants/{tenant_id}/notes")
async def set_tenant_notes(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Save the operator's free-text notes for a store (never shown to the tenant)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    notes = str(payload.get("notes", ""))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE tenants SET admin_notes = $1, updated_at = now() WHERE id = $2 RETURNING id",
            notes or None,
            tenant_id,
        )
    if updated is None:
        return _not_found()
    await audit(pool, actor="operator", action="tenant.notes", tenant_id=tenant_id, detail={})
    return {"tenant_id": tenant_id, "status": "saved"}


@router.get("/tenants/{tenant_id}/keys")
async def tenant_keys(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """List a store's API keys (hashes only exist server-side; nothing secret here)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM tenants WHERE id = $1", tenant_id):
            return _not_found()
        keys = await _key_rows(conn, tenant_id)
    return {"tenant_id": tenant_id, "keys": keys}


@router.post("/tenants/{tenant_id}/keys")
async def create_tenant_key(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Issue a new scoped key for a store. The raw key is returned exactly once."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    scope = str(payload.get("scope", "widget"))
    if scope not in ("widget", "sync"):
        return error_response(422, "invalid_request", "scope must be widget or sync.")
    label = str(payload.get("label", "")).strip() or "issued by operator"
    raw_key = "acip_" + secrets.token_urlsafe(24)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM tenants WHERE id = $1", tenant_id):
            return _not_found()
        key_id = await conn.fetchval(
            "INSERT INTO api_keys (tenant_id, key_hash, scope, label) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            tenant_id,
            hash_key(raw_key),
            scope,
            label,
        )
    await audit(
        pool,
        actor="operator",
        action="tenant.key_issue",
        tenant_id=tenant_id,
        detail={"scope": scope, "label": label},
    )
    return {"id": str(key_id), "api_key": raw_key, "scope": scope, "label": label}


@router.post("/tenants/{tenant_id}/keys/{key_id}/revoke")
async def revoke_tenant_key(
    tenant_id: str,
    key_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not (_valid_uuid(tenant_id) and _valid_uuid(key_id)):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE api_keys SET revoked = TRUE WHERE id = $1 AND tenant_id = $2 RETURNING id",
            key_id,
            tenant_id,
        )
    if updated is None:
        return error_response(404, "not_found", "No such key for this tenant.")
    await audit(
        pool,
        actor="operator",
        action="tenant.key_revoke",
        tenant_id=tenant_id,
        detail={"key_id": key_id},
    )
    return {"id": key_id, "status": "revoked"}


@router.post("/tenants/{tenant_id}/credits")
async def adjust_tenant_credits(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Manual credit adjustment: positive delta grants, negative deducts.
    Writes an append-only ledger entry + audit; returns the fresh summary."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    if not await _admin_write_rate_ok(tenant_id):
        return error_response(429, *_RATE_LIMITED)
    try:
        delta = float(payload.get("delta", 0))
    except (TypeError, ValueError):
        delta = 0.0
    if delta == 0:
        return error_response(422, "invalid_request", "Field 'delta' must be non-zero.")
    reason = str(payload.get("reason", "")).strip() or "manual adjustment"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if not await conn.fetchval("SELECT 1 FROM tenants WHERE id = $1", tenant_id):
            return _not_found()
        await conn.execute(
            "INSERT INTO credit_ledger (tenant_id, delta, rung, reason) VALUES ($1, $2, $3, $4)",
            tenant_id,
            delta,
            "manual",
            reason,
        )
    await audit(
        pool,
        actor="operator",
        action="tenant.credit_adjust",
        tenant_id=tenant_id,
        detail={"delta": delta, "reason": reason},
    )
    usage = await _usage_summary(pool, tenant_id)
    return {"tenant_id": tenant_id, "status": "adjusted", "credits": usage}


@router.patch("/tenants/{tenant_id}/plan")
async def change_tenant_plan(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Manually move a store onto a plan: updates the tenant's plan pointer and
    upserts its subscription (status + a fresh period window)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    if not await _admin_write_rate_ok(tenant_id):
        return error_response(429, *_RATE_LIMITED)
    plan_code = str(payload.get("plan_code", "")).strip()
    if not plan_code:
        return error_response(422, "invalid_request", "Field 'plan_code' is required.")
    sub_status = str(payload.get("status", "active"))
    if sub_status not in ("trialing", "active", "past_due", "canceled"):
        return error_response(
            422, "invalid_request", "status must be trialing, active, past_due, or canceled."
        )
    try:
        period_days = int(payload.get("period_days", 30))
    except (TypeError, ValueError):
        period_days = 30
    period_days = max(1, min(period_days, 366))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        plan_id = await conn.fetchval("SELECT id FROM plans WHERE code = $1", plan_code)
        if plan_id is None:
            return error_response(404, "not_found", "No such plan.")
        if not await conn.fetchval("SELECT 1 FROM tenants WHERE id = $1", tenant_id):
            return _not_found()
        async with conn.transaction():
            await conn.execute(
                "UPDATE tenants SET plan_id = $1, updated_at = now() WHERE id = $2",
                plan_id,
                tenant_id,
            )
            await conn.execute(
                "INSERT INTO subscriptions (tenant_id, plan_id, status, current_period_end) "
                "VALUES ($1, $2, $3, now() + make_interval(days => $4)) "
                "ON CONFLICT (tenant_id) DO UPDATE SET plan_id = EXCLUDED.plan_id, "
                "status = EXCLUDED.status, current_period_end = EXCLUDED.current_period_end, "
                "cancel_at_period_end = FALSE, updated_at = now()",
                tenant_id,
                plan_id,
                sub_status,
                period_days,
            )
    await audit(
        pool,
        actor="operator",
        action="tenant.plan_change",
        tenant_id=tenant_id,
        detail={"plan_code": plan_code, "status": sub_status, "period_days": period_days},
    )
    return {
        "tenant_id": tenant_id,
        "plan_code": plan_code,
        "status": sub_status,
        "period_days": period_days,
    }


@router.post("/tenants/{tenant_id}/status")
async def set_tenant_status(
    tenant_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Suspend or re-activate a tenant."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not await _admin_write_rate_ok(tenant_id):
        return error_response(429, *_RATE_LIMITED)
    status = str(payload.get("status", ""))
    if status not in ("active", "suspended"):
        return error_response(422, "invalid_request", "status must be active or suspended.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE tenants SET status = $1, updated_at = now() WHERE id = $2 RETURNING id",
            status,
            tenant_id,
        )
    if updated is None:
        return error_response(404, "not_found", "No such tenant.")
    await audit(
        pool,
        actor="operator",
        action="tenant.status",
        tenant_id=tenant_id,
        detail={"status": status},
    )
    return {"tenant_id": tenant_id, "status": status}
