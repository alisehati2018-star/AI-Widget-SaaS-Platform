"""Admin surface — account-security monitoring: locked accounts (both
identity planes), failed-login counts, recent auth events, and manual unlock."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/security")
async def security_monitoring(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Locked accounts (both identity planes), failed-login counts, and
    recent auth events."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        locked = await conn.fetch(
            "SELECT email, failed_logins, locked_until, 'customer' AS plane FROM users "
            "WHERE locked_until IS NOT NULL AND locked_until > now() "
            "UNION ALL "
            "SELECT email, failed_logins, locked_until, 'admin' AS plane FROM admin_users "
            "WHERE locked_until IS NOT NULL AND locked_until > now() "
            "ORDER BY locked_until DESC"
        )
        at_risk = await conn.fetchval(
            "SELECT (SELECT count(*) FROM users WHERE failed_logins > 0) "
            "+ (SELECT count(*) FROM admin_users WHERE failed_logins > 0)"
        )
        events = await conn.fetch(
            "SELECT actor, action, created_at FROM audit_log "
            "WHERE action LIKE 'auth.%' OR action LIKE 'admin_auth.%' "
            "ORDER BY created_at DESC LIMIT 50"
        )
    return {
        "locked_accounts": [
            {
                "email": r["email"],
                "plane": r["plane"],
                "failed_logins": r["failed_logins"],
                "locked_until": r["locked_until"].isoformat() if r["locked_until"] else None,
            }
            for r in locked
        ],
        "accounts_with_failures": int(at_risk or 0),
        "recent_auth_events": [
            {
                "actor": r["actor"],
                "action": r["action"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in events
        ],
    }


@router.post("/security/unlock")
async def unlock_account(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Manually clear a lockout (failed logins + locked_until) for a customer
    or admin account, so the user doesn't have to wait out the window."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    email = str(payload.get("email", "")).strip().lower()
    plane = str(payload.get("plane", "customer"))
    if not email:
        return error_response(422, "invalid_request", "Field 'email' is required.")
    if plane not in ("customer", "admin"):
        return error_response(422, "invalid_request", "plane must be customer or admin.")
    table = "users" if plane == "customer" else "admin_users"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        unlocked = await conn.fetchval(
            f"UPDATE {table} SET failed_logins = 0, locked_until = NULL "  # noqa: S608
            f"WHERE lower(email) = $1 RETURNING id",
            email,
        )
    if unlocked is None:
        return error_response(404, "not_found", "No such account.")
    await audit(pool, actor="operator", action="security.unlock",
                detail={"email": email, "plane": plane})
    return {"email": email, "plane": plane, "status": "unlocked"}
