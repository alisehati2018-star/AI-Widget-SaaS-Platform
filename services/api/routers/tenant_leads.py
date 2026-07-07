"""Store-owner dashboard — captured leads: list + pipeline status/notes."""

from __future__ import annotations

from typing import Any

from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/leads")
async def leads(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None  # narrowed: _require_tenant guarantees a tenant
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, email, phone, has_intent, source, status, notes, created_at FROM leads "
            "WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 500",
            p.tenant_id,
        )
    return {
        "leads": [
            {
                "id": r["id"],
                "email": r["email"],
                "phone": r["phone"],
                "has_intent": r["has_intent"],
                "source": r["source"],
                "status": r["status"],
                "notes": r["notes"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    }


_LEAD_STATUSES = ("new", "contacted", "qualified", "won", "lost")


@router.post("/leads/{lead_id}")
async def update_lead(
    lead_id: int,
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Update a lead's pipeline status and/or notes (tenant-scoped)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    sets: list[str] = []
    values: list[Any] = []
    if "status" in payload:
        status = str(payload["status"])
        if status not in _LEAD_STATUSES:
            return error_response(
                422, "invalid_request", f"status must be one of {', '.join(_LEAD_STATUSES)}."
            )
        values.append(status)
        sets.append(f"status = ${len(values)}")
    if "notes" in payload:
        values.append(str(payload["notes"]))
        sets.append(f"notes = ${len(values)}")
    if not sets:
        return error_response(422, "invalid_request", "Supply 'status' and/or 'notes'.")
    values.extend([lead_id, p.tenant_id])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            f"UPDATE leads SET {', '.join(sets)}, updated_at = now() "
            f"WHERE id = ${len(values) - 1} AND tenant_id = ${len(values)} RETURNING id",
            *values,
        )
    if updated is None:
        return error_response(404, "not_found", "No such lead.")
    return {"id": lead_id, "status": "updated"}
