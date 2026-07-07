"""Human authentication — password reset, email verification, and authenticated
password/email changes (no account enumeration on the public endpoints)."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any

from acip_auth import hash_password, validate_password_strength, verify_password
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from acip_notify import reset_email, send_email, verification_email
from fastapi import APIRouter, Request

from .auth_common import (
    _ACCESS_COOKIE,
    _AUTHZ,
    _EMAIL_RE,
    _LOCALE_COOKIE,
    _RATE_LIMITED,
    _create_verification,
    _hash_token,
    _ip_rate_ok,
    _now,
    current_principal,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# --------------------------------------------------------------------------- #
# Password reset (request + confirm) — no account enumeration                #
# --------------------------------------------------------------------------- #
@router.post("/password/reset-request")
async def reset_request(
    payload: dict[str, Any], request: Request, next_locale: str | None = _LOCALE_COOKIE
):
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)
    email = str(payload.get("email", "")).strip().lower()
    accepted = {"status": "accepted"}  # always generic
    if not _EMAIL_RE.match(email):
        return accepted
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT id, email FROM users WHERE lower(email) = $1", email)
        if user is not None:
            token = secrets.token_urlsafe(32)
            await conn.execute(
                "INSERT INTO password_resets (user_id, token_hash, expires_at) VALUES ($1, $2, $3)",
                user["id"],
                _hash_token(token),
                _now() + timedelta(hours=1),
            )
            subject, text, html = reset_email(
                f"{s.app_base_url}/reset-password?token={token}", next_locale
            )
            await send_email(email, subject, text, html)
            if s.env != "production":  # dev convenience for testing
                accepted["reset_token"] = token
    return accepted


@router.post("/verify-request")
async def verify_request(
    payload: dict[str, Any], request: Request, next_locale: str | None = _LOCALE_COOKIE
):
    """(Re)send an email-verification link. Generic response (no enumeration)."""
    if not await _ip_rate_ok(request):
        return error_response(429, *_RATE_LIMITED)
    email = str(payload.get("email", "")).strip().lower()
    accepted: dict[str, Any] = {"status": "accepted"}
    if not _EMAIL_RE.match(email):
        return accepted
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, email_verified FROM users WHERE lower(email) = $1", email
        )
        if user is not None and not user["email_verified"]:
            token = await _create_verification(conn, user["id"])
            subject, text, html = verification_email(
                f"{s.app_base_url}/verify-email?token={token}", next_locale
            )
            await send_email(email, subject, text, html)
            if s.env != "production":
                accepted["verify_token"] = token
    return accepted


@router.post("/verify-confirm")
async def verify_confirm(payload: dict[str, Any]):
    """Confirm an email-verification token → mark the user verified (single-use)."""
    token = str(payload.get("token", ""))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id FROM email_verifications WHERE token_hash = $1 "
            "AND used_at IS NULL AND expires_at > now()",
            _hash_token(token),
        )
        if row is None:
            return error_response(400, "invalid_token", "Invalid or expired verification token.")
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET email_verified = TRUE WHERE id = $1", row["user_id"]
            )
            await conn.execute(
                "UPDATE email_verifications SET used_at = now() WHERE id = $1", row["id"]
            )
    return {"status": "verified"}


@router.post("/password/reset-confirm")
async def reset_confirm(payload: dict[str, Any]):
    token = str(payload.get("token", ""))
    new_password = str(payload.get("password", ""))
    pw_problems = validate_password_strength(new_password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, user_id FROM password_resets WHERE token_hash = $1 "
            "AND used_at IS NULL AND expires_at > now()",
            _hash_token(token),
        )
        if row is None:
            return error_response(400, "invalid_token", "Invalid or expired reset token.")
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET password_hash = $1, failed_logins = 0, locked_until = NULL "
                "WHERE id = $2",
                hash_password(new_password),
                row["user_id"],
            )
            await conn.execute(
                "UPDATE password_resets SET used_at = now() WHERE id = $1", row["id"]
            )
            # Force re-login everywhere after a password change.
            await conn.execute(
                "UPDATE auth_sessions SET revoked = TRUE WHERE user_id = $1", row["user_id"]
            )
    return {"status": "password_updated"}


# --------------------------------------------------------------------------- #
# Change password (authenticated; verifies the current password)             #
# --------------------------------------------------------------------------- #
@router.post("/change-password")
async def change_password(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _ACCESS_COOKIE,
):
    principal = await current_principal(authorization, vitrin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    new_password = str(payload.get("new_password", ""))
    pw_problems = validate_password_strength(new_password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT password_hash FROM users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2::uuid",
            hash_password(new_password),
            principal.user_id,
        )
    return {"status": "password_updated"}


@router.post("/change-email")
async def change_email(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _ACCESS_COOKIE,
    next_locale: str | None = _LOCALE_COOKIE,
):
    """Change the signed-in user's email. Re-auth with the current password,
    then set the new address as unverified and send a verification email."""
    principal = await current_principal(authorization, vitrin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    new_email = str(payload.get("new_email", "")).strip().lower()
    if not _EMAIL_RE.match(new_email):
        return error_response(422, "invalid_email", "A valid email is required.")
    s = get_settings()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, password_hash FROM users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        if new_email == row["email"]:
            return error_response(422, "invalid_email", "This is already your email address.")
        if await conn.fetchval(
            "SELECT 1 FROM users WHERE lower(email) = $1 AND id <> $2::uuid",
            new_email,
            principal.user_id,
        ):
            return error_response(409, "email_taken", "An account with this email already exists.")
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET email = $1, email_verified = FALSE WHERE id = $2::uuid",
                new_email,
                principal.user_id,
            )
            verify_token = await _create_verification(conn, principal.user_id)
        await audit(
            pool, actor=row["email"], action="auth.change_email", detail={"new_email": new_email}
        )
    subject, text, html = verification_email(
        f"{s.app_base_url}/verify-email?token={verify_token}", next_locale
    )
    await send_email(new_email, subject, text, html)
    resp = {"status": "email_changed", "email": new_email}
    if s.env != "production":
        resp["verify_token"] = verify_token
    return resp
