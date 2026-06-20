"""Store-owner dashboard API (Phase 8, M9 human layer).

Every endpoint authenticates a *person* via their access JWT and derives the
``tenant_id`` from the authenticated principal — **never** from client input —
so a store user can only ever touch their own tenant. This is the human-side
mirror of the data isolation invariant.
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from acip_analytics import aggregations as _agg
from acip_analytics import attribution as _attr
from acip_analytics import why_summary as _why
from acip_auth import hash_password
from acip_auth.models import AuthPrincipal, Role
from acip_billing.ledger import balance, plan_status
from acip_core.audit import audit
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Header

from ..deps import hash_key
from .auth import current_principal

router = APIRouter(prefix="/tenant", tags=["tenant"])

_AUTHZ = Header(default=None, alias="authorization")
_TENANT_ROLES = frozenset({Role.STORE_OWNER, Role.STORE_STAFF})


async def _require_tenant(authorization: str | None) -> AuthPrincipal | None:
    """Return a tenant-scoped principal, or None if not a logged-in store user."""
    principal = await current_principal(authorization)
    if principal is None or principal.tenant_id is None or principal.role not in _TENANT_ROLES:
        return None
    return principal


def _unauth():
    return error_response(401, "unauthenticated", "Sign in to your store account.")


def _owner_only():
    return error_response(403, "forbidden", "This action requires the store owner role.")


# --------------------------------------------------------------------------- #
# Profile / overview                                                          #
# --------------------------------------------------------------------------- #
@router.get("/profile")
async def profile(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        t = await conn.fetchrow(
            "SELECT t.slug, t.name, t.status, t.tracking_enabled, t.settings, "
            "COALESCE(pl.name, '—') AS plan, COALESCE(s.status, 'none') AS sub_status, "
            "s.current_period_end "
            "FROM tenants t "
            "LEFT JOIN subscriptions s ON s.tenant_id = t.id "
            "LEFT JOIN plans pl ON pl.id = s.plan_id WHERE t.id = $1",
            p.tenant_id,
        )
    status = await plan_status(pool, p.tenant_id)
    spent = await balance(pool, p.tenant_id)
    if t is None:
        return error_response(404, "not_found", "Tenant not found.")
    period_end = t["current_period_end"]
    return {
        "tenant_id": p.tenant_id,
        "slug": t["slug"], "name": t["name"], "status": t["status"],
        "plan": t["plan"], "sub_status": t["sub_status"],
        "current_period_end": period_end.isoformat() if period_end else None,
        "tracking_enabled": t["tracking_enabled"],
        "settings": t["settings"],
        "credits": {
            "spent": abs(spent), "cap": status.get("cap"),
            "within_plan": status.get("within_plan", True),
        },
        "role": p.role.value,
    }


# --------------------------------------------------------------------------- #
# Analytics (tenant-scoped)                                                   #
# --------------------------------------------------------------------------- #
@router.get("/analytics")
async def analytics(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    es = get_es_client()
    return {
        "four_dimensions": await _attr.four_dimension_summary(pool, get_redis(), p.tenant_id),
        "most_wanted": await _agg.most_wanted(es, p.tenant_id),
        "zero_results": await _agg.zero_result_terms(es, p.tenant_id),
        "funnel": await _agg.funnel(es, p.tenant_id),
    }


@router.get("/insight")
async def insight(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    return {"insight": await _why(get_es_client(), p.tenant_id)}


# --------------------------------------------------------------------------- #
# Search tuning: synonyms + zero-results                                      #
# --------------------------------------------------------------------------- #
def _syn_key(tenant: str) -> str:
    return f"synonyms:{tenant}"


@router.get("/synonyms")
async def get_synonyms(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    redis = get_redis()
    raw = await redis.get(_syn_key(p.tenant_id)) if redis is not None else None
    return {"synonyms": raw.splitlines() if raw else []}


@router.post("/synonyms")
async def set_synonyms(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    lines = payload.get("synonyms", [])
    if not isinstance(lines, list):
        return error_response(422, "invalid_request", "Field 'synonyms' must be a list.")
    redis = get_redis()
    if redis is not None:
        await redis.set(_syn_key(p.tenant_id), "\n".join(str(x) for x in lines))
    return {"count": len(lines), "status": "saved"}


@router.get("/zero-results")
async def zero_results(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    return {"terms": await _agg.zero_result_terms(get_es_client(), p.tenant_id)}


# --------------------------------------------------------------------------- #
# Leads                                                                       #
# --------------------------------------------------------------------------- #
@router.get("/leads")
async def leads(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT email, phone, has_intent, source, created_at FROM leads "
            "WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 500",
            p.tenant_id,
        )
    return {
        "leads": [
            {
                "email": r["email"], "phone": r["phone"], "has_intent": r["has_intent"],
                "source": r["source"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


# --------------------------------------------------------------------------- #
# API keys (list / create / revoke) — scoped to the tenant                    #
# --------------------------------------------------------------------------- #
@router.get("/keys")
async def list_keys(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
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
                "id": str(r["id"]), "scope": r["scope"], "label": r["label"],
                "revoked": r["revoked"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/keys")
async def create_key(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
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
            p.tenant_id, hash_key(raw_key), scope, label,
        )
    await audit(pool, actor=p.email, action="key.create", tenant_id=p.tenant_id,
                detail={"scope": scope, "label": label})
    return {"api_key": raw_key, "scope": scope, "label": label}


@router.post("/keys/{key_id}/revoke")
async def revoke_key(key_id: str, authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_keys SET revoked = TRUE WHERE id = $1 AND tenant_id = $2",
            key_id, p.tenant_id,
        )
    await audit(pool, actor=p.email, action="key.revoke", tenant_id=p.tenant_id,
                detail={"key_id": key_id})
    return {"status": "revoked"}


# --------------------------------------------------------------------------- #
# Store settings + white-label branding                                       #
# --------------------------------------------------------------------------- #
@router.patch("/settings")
async def update_settings(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    # Whitelist the keys a tenant may set (platform branding stays visible).
    allowed = {"logo_url", "primary_color", "store_url", "platform", "widget_greeting"}
    patch = {k: v for k, v in payload.items() if k in allowed}
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE tenants SET settings = settings || $1::jsonb, updated_at = now() "
            "WHERE id = $2",
            json.dumps(patch), p.tenant_id,
        )
    await audit(pool, actor=p.email, action="settings.update", tenant_id=p.tenant_id, detail=patch)
    return {"status": "saved", "settings": patch}


# --------------------------------------------------------------------------- #
# Team (list + invite staff)                                                  #
# --------------------------------------------------------------------------- #
@router.get("/team")
async def team(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT email, full_name, role, status, last_login_at FROM users "
            "WHERE tenant_id = $1 ORDER BY created_at ASC",
            p.tenant_id,
        )
    return {
        "members": [
            {
                "email": r["email"], "full_name": r["full_name"], "role": r["role"],
                "status": r["status"],
                "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/team/invite")
async def invite(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    email = str(payload.get("email", "")).strip().lower()
    full_name = str(payload.get("full_name", "")).strip() or None
    if "@" not in email:
        return error_response(422, "invalid_email", "A valid email is required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM users WHERE lower(email) = $1", email):
            return error_response(409, "email_taken", "A user with this email already exists.")
        setup_token = secrets.token_urlsafe(32)
        async with conn.transaction():
            user_id = await conn.fetchval(
                "INSERT INTO users (email, password_hash, full_name, role, tenant_id, status) "
                "VALUES ($1, $2, $3, 'store_staff', $4, 'pending') RETURNING id",
                email, hash_password(secrets.token_urlsafe(24)), full_name, p.tenant_id,
            )
            await conn.execute(
                "INSERT INTO invitations (tenant_id, email, role, invited_by) "
                "VALUES ($1, $2, 'store_staff', $3)",
                p.tenant_id, email, p.user_id,
            )
            await conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
                user_id, hash_key(setup_token), datetime.now(UTC) + timedelta(days=7),
            )
    await audit(pool, actor=p.email, action="team.invite", tenant_id=p.tenant_id,
                detail={"email": email})
    result = {"status": "invited", "email": email}
    # The invitee sets their password via /reset-password?token=... (email delivery
    # is wired in the notification phase; token surfaced in non-production only).
    if get_settings().env != "production":
        result["setup_token"] = setup_token
    return result


# --------------------------------------------------------------------------- #
# GDPR self-serve (export / tracking)                                         #
# --------------------------------------------------------------------------- #
@router.get("/export")
async def export_data(authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
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
async def set_tracking(payload: dict[str, Any], authorization: str | None = _AUTHZ):
    p = await _require_tenant(authorization)
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
    await audit(pool, actor=p.email, action="tenant.tracking", tenant_id=p.tenant_id,
                detail={"enabled": enabled})
    return {"tracking_enabled": enabled}
