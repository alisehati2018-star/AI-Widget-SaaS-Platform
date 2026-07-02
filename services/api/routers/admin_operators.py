"""Operator (platform admin) management — CRUD over the ``admin_users`` table.

Lives on the admin plane under ``/admin/operators``. Until now the only way to
add a second admin was the raw-token ``/admin/auth/bootstrap`` call; these
endpoints let a signed-in admin invite, rename, suspend, re-activate and remove
other admins from the UI, with two safety rails:

* an admin can never suspend or delete **themself**, and
* the **last active admin** can never be suspended or deleted (the platform
  must always keep at least one working operator account).

Nothing here touches the customer ``users`` table — the two identity planes
stay fully separate.
"""

from __future__ import annotations

import re
import secrets
from typing import Any

from acip_auth import hash_password, validate_password_strength
from acip_auth.models import AuthPrincipal
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter, Cookie, Header

router = APIRouter(prefix="/admin/operators", tags=["admin-operators"])

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_admin_access")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


async def _principal(
    token: str | None, authorization: str | None, cookie: str | None
) -> tuple[bool, AuthPrincipal | None]:
    """(authorized?, principal). The raw operator token authorizes with no
    principal (automation); a signed-in admin carries one, enabling the
    self-protection rails below."""
    from .admin_auth import admin_current_principal

    principal = await admin_current_principal(authorization, cookie)
    if principal is not None:
        return True, principal
    expected = get_settings().admin_token
    if expected and token and secrets.compare_digest(token, expected):
        return True, None
    return False, None


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


def _not_found():
    return error_response(404, "not_found", "No such operator.")


def _row(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "email": r["email"],
        "full_name": r["full_name"],
        "status": r["status"],
        "last_login_at": r["last_login_at"].isoformat() if r["last_login_at"] else None,
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "sessions": int(r["sessions"]),
    }


_SELECT = (
    "SELECT a.id, a.email, a.full_name, a.status, a.last_login_at, a.created_at, "
    "(SELECT count(*) FROM admin_sessions s WHERE s.admin_user_id = a.id "
    " AND NOT s.revoked AND s.expires_at > now()) AS sessions "
    "FROM admin_users a"
)


@router.get("")
async def list_operators(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    ok, principal = await _principal(x_admin_token, authorization, vitrin_access)
    if not ok:
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"{_SELECT} ORDER BY a.created_at ASC")
    return {
        "operators": [_row(r) for r in rows],
        "me": principal.user_id if principal else None,
    }


@router.post("")
async def create_operator(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Invite a new platform admin (email + initial password + optional name)."""
    ok, principal = await _principal(x_admin_token, authorization, vitrin_access)
    if not ok:
        return _forbidden()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))
    full_name = str(payload.get("full_name", "")).strip() or None
    if not _EMAIL_RE.match(email):
        return error_response(422, "invalid_email", "A valid email is required.")
    pw_problems = validate_password_strength(password)
    if pw_problems:
        return error_response(422, "weak_password", " ".join(pw_problems))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM admin_users WHERE lower(email) = $1", email):
            return error_response(409, "email_taken", "An account with this email already exists.")
        operator_id = await conn.fetchval(
            "INSERT INTO admin_users (email, password_hash, full_name) "
            "VALUES ($1, $2, $3) RETURNING id",
            email,
            hash_password(password),
            full_name,
        )
    await audit(
        pool,
        actor=principal.email if principal else "operator",
        action="operator.create",
        detail={"email": email},
    )
    return {"id": str(operator_id), "email": email, "status": "active"}


@router.patch("/{operator_id}")
async def update_operator(
    operator_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Edit an operator's display name (identity fields stay self-serve:
    email/password change only via /admin/auth by the account owner)."""
    ok, principal = await _principal(x_admin_token, authorization, vitrin_access)
    if not ok:
        return _forbidden()
    if not _UUID_RE.match(operator_id):
        return _not_found()
    if "full_name" not in payload:
        return error_response(422, "invalid_request", "No editable fields supplied.")
    full_name = str(payload.get("full_name", "")).strip() or None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            "UPDATE admin_users SET full_name = $1, updated_at = now() "
            "WHERE id = $2::uuid RETURNING id",
            full_name,
            operator_id,
        )
    if updated is None:
        return _not_found()
    await audit(
        pool,
        actor=principal.email if principal else "operator",
        action="operator.update",
        detail={"operator_id": operator_id},
    )
    return {"id": operator_id, "status": "updated"}


@router.post("/{operator_id}/status")
async def set_operator_status(
    operator_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Suspend or re-activate an operator; suspension also revokes their
    live sessions so access ends immediately."""
    ok, principal = await _principal(x_admin_token, authorization, vitrin_access)
    if not ok:
        return _forbidden()
    if not _UUID_RE.match(operator_id):
        return _not_found()
    status = str(payload.get("status", ""))
    if status not in ("active", "suspended"):
        return error_response(422, "invalid_request", "Status must be active or suspended.")
    if status == "suspended" and principal and principal.user_id == operator_id:
        return error_response(409, "self_action", "You cannot suspend your own account.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchval(
                "SELECT status FROM admin_users WHERE id = $1::uuid FOR UPDATE", operator_id
            )
            if current is None:
                return _not_found()
            if status == "suspended" and current == "active":
                others = await conn.fetchval(
                    "SELECT count(*) FROM admin_users "
                    "WHERE status = 'active' AND id <> $1::uuid",
                    operator_id,
                )
                if int(others) == 0:
                    return error_response(
                        409, "last_admin", "The last active admin cannot be suspended."
                    )
            await conn.execute(
                "UPDATE admin_users SET status = $1, updated_at = now() WHERE id = $2::uuid",
                status,
                operator_id,
            )
            if status == "suspended":
                await conn.execute(
                    "UPDATE admin_sessions SET revoked = TRUE WHERE admin_user_id = $1::uuid",
                    operator_id,
                )
    await audit(
        pool,
        actor=principal.email if principal else "operator",
        action="operator.status",
        detail={"operator_id": operator_id, "status": status},
    )
    return {"id": operator_id, "status": status}


@router.delete("/{operator_id}")
async def delete_operator(
    operator_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    ok, principal = await _principal(x_admin_token, authorization, vitrin_access)
    if not ok:
        return _forbidden()
    if not _UUID_RE.match(operator_id):
        return _not_found()
    if principal and principal.user_id == operator_id:
        return error_response(409, "self_action", "You cannot delete your own account.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT email, status FROM admin_users WHERE id = $1::uuid FOR UPDATE",
                operator_id,
            )
            if row is None:
                return _not_found()
            if row["status"] == "active":
                others = await conn.fetchval(
                    "SELECT count(*) FROM admin_users "
                    "WHERE status = 'active' AND id <> $1::uuid",
                    operator_id,
                )
                if int(others) == 0:
                    return error_response(
                        409, "last_admin", "The last active admin cannot be deleted."
                    )
            await conn.execute("DELETE FROM admin_users WHERE id = $1::uuid", operator_id)
    await audit(
        pool,
        actor=principal.email if principal else "operator",
        action="operator.delete",
        detail={"operator_id": operator_id, "email": row["email"]},
    )
    return {"id": operator_id, "status": "deleted"}
