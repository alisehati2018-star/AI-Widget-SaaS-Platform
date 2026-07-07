"""Admin surface — public contact-form inbox, triaged by the operator
(new → read → resolved) with an internal follow-up note."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden, _iso

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/contact")
async def list_contact_messages(
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    where: list[str] = []
    params: list[Any] = []
    if status in ("new", "read", "resolved"):
        params.append(status)
        where.append(f"status = ${len(params)}")
    if q:
        params.append(f"%{q.strip()}%")
        where.append(f"(email ILIKE ${len(params)} OR name ILIKE ${len(params)})")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        counts = await conn.fetchrow(
            "SELECT count(*) AS all_count, "
            "count(*) FILTER (WHERE status = 'new') AS new_count, "
            "count(*) FILTER (WHERE status = 'read') AS read_count, "
            "count(*) FILTER (WHERE status = 'resolved') AS resolved_count "
            "FROM contact_messages"
        )
        total = await conn.fetchval(
            f"SELECT count(*) FROM contact_messages {clause}", *params
        )
        rows = await conn.fetch(
            f"SELECT id, name, email, message, status, admin_note, created_at, updated_at "
            f"FROM contact_messages {clause} "
            f"ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}",
            *params, limit, offset,
        )
    return {
        "messages": [
            {
                "id": int(r["id"]),
                "name": r["name"],
                "email": r["email"],
                "message": r["message"],
                "status": r["status"],
                "admin_note": r["admin_note"],
                "created_at": _iso(r["created_at"]),
                "updated_at": _iso(r["updated_at"]),
            }
            for r in rows
        ],
        "total": int(total),
        "counts": {
            "all": int(counts["all_count"]),
            "new": int(counts["new_count"]),
            "read": int(counts["read_count"]),
            "resolved": int(counts["resolved_count"]),
        },
        "limit": limit,
        "offset": offset,
    }


@router.patch("/contact/{message_id}")
async def update_contact_message(
    message_id: int,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    sets: list[str] = []
    values: list[Any] = []
    if "status" in payload:
        status = str(payload["status"])
        if status not in ("new", "read", "resolved"):
            return error_response(
                422, "invalid_request", "Status must be new, read or resolved."
            )
        values.append(status)
        sets.append(f"status = ${len(values)}")
    if "admin_note" in payload:
        note = str(payload.get("admin_note") or "").strip()[:4000] or None
        values.append(note)
        sets.append(f"admin_note = ${len(values)}")
    if not sets:
        return error_response(422, "invalid_request", "No editable fields supplied.")
    values.append(message_id)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            f"UPDATE contact_messages SET {', '.join(sets)}, updated_at = now() "
            f"WHERE id = ${len(values)} RETURNING id",
            *values,
        )
    if updated is None:
        return error_response(404, "not_found", "No such message.")
    await audit(await get_pg_pool(), actor="operator", action="contact.update",
                detail={"message_id": message_id, "fields": list(payload.keys())})
    return {"id": message_id, "status": "updated"}
