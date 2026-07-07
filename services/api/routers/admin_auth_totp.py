"""Platform-admin TOTP two-factor auth (Phase 9 hardening) — enroll, confirm,
disable, and status."""

from __future__ import annotations

from typing import Any

from acip_auth import verify_password
from acip_auth.totp import generate_totp_secret, otpauth_uri, verify_totp, verify_totp_step
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_auth_common import _ACCESS_COOKIE, _AUTHZ, admin_current_principal

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.get("/totp")
async def totp_status(
    authorization: str | None = _AUTHZ, vitrin_admin_access: str | None = _ACCESS_COOKIE
):
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        enabled = await conn.fetchval(
            "SELECT totp_enabled FROM admin_users WHERE id = $1::uuid", principal.user_id
        )
    return {"totp_enabled": bool(enabled)}


@router.post("/totp/enroll")
async def totp_enroll(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    """Start enrollment: store a fresh secret (NOT yet enforced) and return it
    with the otpauth:// URI. Enforcement begins only after /totp/confirm."""
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, password_hash, totp_enabled FROM admin_users WHERE id = $1::uuid",
            principal.user_id,
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        if row["totp_enabled"]:
            return error_response(409, "totp_already_enabled", "Two-factor auth is already on.")
        secret = generate_totp_secret()
        await conn.execute(
            "UPDATE admin_users SET totp_secret = $1 WHERE id = $2::uuid",
            secret,
            principal.user_id,
        )
    return {
        "secret": secret,
        "otpauth_uri": otpauth_uri(secret, str(row["email"])),
        "status": "pending_confirmation",
    }


@router.post("/totp/confirm")
async def totp_confirm(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    """Turn enforcement on after the admin proves the authenticator works."""
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    code = str(payload.get("totp_code", "")).strip()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, totp_secret, totp_enabled FROM admin_users WHERE id = $1::uuid",
            principal.user_id,
        )
        if row is None or not row["totp_secret"]:
            return error_response(409, "totp_not_enrolled", "Start enrollment first.")
        if row["totp_enabled"]:
            return error_response(409, "totp_already_enabled", "Two-factor auth is already on.")
        step = verify_totp_step(str(row["totp_secret"]), code)
        if step is None:
            return error_response(401, "invalid_totp", "The 6-digit code is not valid.")
        # Record the confirmation step too, so this exact code can't be
        # replayed as the first login code.
        await conn.execute(
            "UPDATE admin_users SET totp_enabled = TRUE, totp_last_step = $1 WHERE id = $2::uuid",
            step,
            principal.user_id,
        )
    await audit(pool, actor=str(row["email"]), action="admin_auth.totp_enabled", detail={})
    return {"status": "totp_enabled"}


@router.post("/totp/disable")
async def totp_disable(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    """Turn 2FA off — requires the password AND a live code (a stolen session
    alone can't weaken the account)."""
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    code = str(payload.get("totp_code", "")).strip()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, password_hash, totp_secret, totp_enabled "
            "FROM admin_users WHERE id = $1::uuid",
            principal.user_id,
        )
        if row is None or not row["totp_enabled"]:
            return error_response(409, "totp_not_enabled", "Two-factor auth is not on.")
        if not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        if not verify_totp(str(row["totp_secret"]), code):
            return error_response(401, "invalid_totp", "The 6-digit code is not valid.")
        await conn.execute(
            "UPDATE admin_users SET totp_enabled = FALSE, totp_secret = NULL "
            "WHERE id = $1::uuid",
            principal.user_id,
        )
    await audit(pool, actor=str(row["email"]), action="admin_auth.totp_disabled", detail={})
    return {"status": "totp_disabled"}
