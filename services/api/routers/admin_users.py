"""Admin surface — store (customer-plane) user accounts.

Distinct from `/admin/operators` (platform admins, `admin_users` table): these
endpoints manage the `users` table — the people who sign in to a store's own
dashboard.
"""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Store users (customer plane) with email search + role/status filters."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    where: list[str] = []
    params: list[Any] = []
    if q:
        params.append(f"%{q.strip()}%")
        where.append(
            f"(u.email ILIKE ${len(params)} OR u.full_name ILIKE ${len(params)} "
            f"OR t.slug ILIKE ${len(params)} OR t.name ILIKE ${len(params)})"
        )
    if role:
        params.append(role)
        where.append(f"u.role = ${len(params)}")
    if status:
        params.append(status)
        where.append(f"u.status = ${len(params)}")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    base = f"FROM users u LEFT JOIN tenants t ON t.id = u.tenant_id {clause}"
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) {base}", *params)
        rows = await conn.fetch(
            f"SELECT u.email, u.full_name, u.role, u.status, u.last_login_at, u.tenant_id, "
            f"COALESCE(t.name, '—') AS tenant {base} "
            f"ORDER BY u.created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
            *params, limit, offset,
        )
    return {
        "users": [
            {
                "email": r["email"],
                "full_name": r["full_name"],
                "role": r["role"],
                "status": r["status"],
                "tenant": r["tenant"],
                "has_tenant": r["tenant_id"] is not None,
                "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
            }
            for r in rows
        ],
        "total": int(total),
        "limit": limit,
        "offset": offset,
    }


@router.post("/users/{email}/status")
async def set_user_status(
    email: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Suspend or re-activate a user; suspending also clears any lockout."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    status = str(payload.get("status", ""))
    if status not in ("active", "suspended"):
        return error_response(422, "invalid_request", "status must be active or suspended.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE users SET status = $1, failed_logins = 0, locked_until = NULL "
            "WHERE lower(email) = $2 RETURNING id",
            status,
            email.lower(),
        )
    if updated is None:
        return error_response(404, "not_found", "No such user.")
    await audit(
        pool, actor="operator", action="user.status", detail={"email": email, "status": status}
    )
    return {"email": email, "status": status}


@router.post("/users/{email}/role")
async def set_user_role(
    email: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Change a store user's role within their tenant. Platform admins are a
    separate identity plane (``admin_users``) managed on /admin/operators —
    store users can never be promoted into it from here."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    role = str(payload.get("role", ""))
    if role not in ("store_owner", "store_staff"):
        return error_response(
            422, "invalid_request", "role must be store_owner or store_staff."
        )
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, tenant_id FROM users WHERE lower(email) = $1", email.lower()
        )
        if row is None:
            return error_response(404, "not_found", "No such user.")
        await conn.execute("UPDATE users SET role = $1 WHERE id = $2", role, row["id"])
    await audit(pool, actor="operator", action="user.role", detail={"email": email, "role": role})
    return {"email": email, "role": role}
