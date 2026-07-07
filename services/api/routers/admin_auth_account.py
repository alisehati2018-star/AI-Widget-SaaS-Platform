"""Platform-admin account changes — password and email (authenticated,
re-verifies the current password; no self-serve email verification since
admins are provisioned/managed by other admins)."""

from __future__ import annotations

from typing import Any

from acip_auth import hash_password, validate_password_strength, verify_password
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_auth_common import _ACCESS_COOKIE, _AUTHZ, _EMAIL_RE, admin_current_principal

router = APIRouter(prefix="/admin/auth", tags=["admin-auth"])


@router.post("/change-password")
async def change_password(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    principal = await admin_current_principal(authorization, vitrin_admin_access)
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
            "SELECT password_hash FROM admin_users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        await conn.execute(
            "UPDATE admin_users SET password_hash = $1 WHERE id = $2::uuid",
            hash_password(new_password),
            principal.user_id,
        )
    return {"status": "password_updated"}


@router.post("/change-email")
async def change_email(
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_admin_access: str | None = _ACCESS_COOKIE,
):
    """Change the signed-in admin's email. No verification email is sent —
    platform admins are provisioned/managed by other admins, not self-serve."""
    principal = await admin_current_principal(authorization, vitrin_admin_access)
    if principal is None:
        return error_response(401, "unauthenticated", "A valid access token is required.")
    current = str(payload.get("current_password", ""))
    new_email = str(payload.get("new_email", "")).strip().lower()
    if not _EMAIL_RE.match(new_email):
        return error_response(422, "invalid_email", "A valid email is required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT email, password_hash FROM admin_users WHERE id = $1::uuid", principal.user_id
        )
        if row is None or not verify_password(current, row["password_hash"]):
            return error_response(403, "invalid_password", "Your current password is incorrect.")
        if new_email == row["email"]:
            return error_response(422, "invalid_email", "This is already your email address.")
        if await conn.fetchval(
            "SELECT 1 FROM admin_users WHERE lower(email) = $1 AND id <> $2::uuid",
            new_email,
            principal.user_id,
        ):
            return error_response(409, "email_taken", "An account with this email already exists.")
        await conn.execute(
            "UPDATE admin_users SET email = $1 WHERE id = $2::uuid", new_email, principal.user_id
        )
        await audit(
            pool,
            actor=row["email"],
            action="admin_auth.change_email",
            detail={"new_email": new_email},
        )
    return {"status": "email_changed", "email": new_email}
