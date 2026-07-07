"""Store-owner dashboard — team management: list, invite staff, resend the
setup email, change a member's role, or remove them (owner-only actions)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from acip_auth import hash_password
from acip_auth.models import Role
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import invite_email, send_email
from fastapi import APIRouter

from ..deps import hash_key
from .tenant_common import _AUTHZ, _COOKIE, _owner_only, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/team")
async def team(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
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
                "email": r["email"],
                "full_name": r["full_name"],
                "role": r["role"],
                "status": r["status"],
                "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/team/invite")
async def invite(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
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
                email,
                hash_password(secrets.token_urlsafe(24)),
                full_name,
                p.tenant_id,
            )
            await conn.execute(
                "INSERT INTO invitations (tenant_id, email, role, invited_by) "
                "VALUES ($1, $2, 'store_staff', $3)",
                p.tenant_id,
                email,
                p.user_id,
            )
            await conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
                user_id,
                hash_key(setup_token),
                datetime.now(UTC) + timedelta(days=7),
            )
        store_name = await conn.fetchval("SELECT name FROM tenants WHERE id = $1", p.tenant_id)
    await audit(
        pool, actor=p.email, action="team.invite", tenant_id=p.tenant_id, detail={"email": email}
    )
    s = get_settings()
    subject, text, html = invite_email(
        f"{s.app_base_url}/reset-password?token={setup_token}", store_name or "your store"
    )
    await send_email(email, subject, text, html)
    result = {"status": "invited", "email": email}
    if s.env != "production":  # dev convenience: surface the setup link token
        result["setup_token"] = setup_token
    return result


@router.post("/team/resend")
async def resend_invite(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    """Re-send the setup email for a PENDING teammate (fresh 7-day token)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    email = str(payload.get("email", "")).strip().lower()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval(
            "SELECT id FROM users WHERE lower(email) = $1 AND tenant_id = $2 "
            "AND status = 'pending'",
            email,
            p.tenant_id,
        )
        if user_id is None:
            return error_response(404, "not_found", "No pending invite for this email.")
        setup_token = secrets.token_urlsafe(32)
        async with conn.transaction():
            # Invalidate previous setup links before issuing the fresh one.
            await conn.execute(
                "UPDATE password_resets SET used_at = now() "
                "WHERE user_id = $1 AND used_at IS NULL",
                user_id,
            )
            await conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
                user_id,
                hash_key(setup_token),
                datetime.now(UTC) + timedelta(days=7),
            )
        store_name = await conn.fetchval("SELECT name FROM tenants WHERE id = $1", p.tenant_id)
    await audit(
        pool, actor=p.email, action="team.resend", tenant_id=p.tenant_id, detail={"email": email}
    )
    s = get_settings()
    subject, text, html = invite_email(
        f"{s.app_base_url}/reset-password?token={setup_token}", store_name or "your store"
    )
    await send_email(email, subject, text, html)
    result = {"status": "resent", "email": email}
    if s.env != "production":  # dev convenience: surface the setup link token
        result["setup_token"] = setup_token
    return result


@router.post("/team/role")
async def team_role(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    email = str(payload.get("email", "")).strip().lower()
    role = str(payload.get("role", ""))
    if role not in ("store_owner", "store_staff"):
        return error_response(422, "invalid_request", "role must be store_owner or store_staff.")
    if email == p.email:
        return error_response(422, "invalid_request", "You cannot change your own role.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE users SET role = $1 WHERE lower(email) = $2 AND tenant_id = $3 RETURNING id",
            role,
            email,
            p.tenant_id,
        )
    if updated is None:
        return error_response(404, "not_found", "No such team member.")
    await audit(
        pool,
        actor=p.email,
        action="team.role",
        tenant_id=p.tenant_id,
        detail={"email": email, "role": role},
    )
    return {"status": "updated", "email": email, "role": role}


@router.post("/team/remove")
async def team_remove(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    if p.role != Role.STORE_OWNER:
        return _owner_only()
    email = str(payload.get("email", "")).strip().lower()
    if email == p.email:
        return error_response(422, "invalid_request", "You cannot remove yourself.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        removed = await conn.fetchval(
            "DELETE FROM users WHERE lower(email) = $1 AND tenant_id = $2 "
            "AND role <> 'platform_admin' RETURNING id",
            email,
            p.tenant_id,
        )
    if removed is None:
        return error_response(404, "not_found", "No such team member.")
    await audit(
        pool, actor=p.email, action="team.remove", tenant_id=p.tenant_id, detail={"email": email}
    )
    return {"status": "removed", "email": email}
