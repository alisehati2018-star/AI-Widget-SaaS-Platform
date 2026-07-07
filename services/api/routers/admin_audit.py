"""Admin surface — the append-only audit-log browser (+ CSV export)."""

from __future__ import annotations

from typing import Any

from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden, _iso

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit")
async def audit_log(
    actor: str | None = None,
    action: str | None = None,
    tenant: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    cursor: int | None = None,
    limit: int = 50,
    fmt: str | None = None,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Audit-log browser: actor/action-prefix/tenant/date filters + keyset
    cursor (pass the previous page's `next_cursor` to continue).
    `fmt=csv` streams the filtered entries as a CSV download."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    limit = max(1, min(int(limit), 200))
    where: list[str] = []
    params: list[Any] = []
    if actor:
        params.append(f"%{actor.strip()}%")
        where.append(f"a.actor ILIKE ${len(params)}")
    if action:
        params.append(f"{action.strip()}%")
        where.append(f"a.action LIKE ${len(params)}")
    if tenant:
        params.append(f"%{tenant.strip()}%")
        where.append(
            f"a.tenant_id IN (SELECT id FROM tenants "
            f"WHERE slug ILIKE ${len(params)} OR name ILIKE ${len(params)})"
        )
    for field, op, value in (("date_from", ">=", date_from), ("date_to", "<", date_to)):
        if value:
            try:
                from datetime import date, timedelta

                day = date.fromisoformat(value)
            except ValueError:
                return error_response(422, "invalid_request", f"Invalid '{field}' (YYYY-MM-DD).")
            if field == "date_to":
                day = day + timedelta(days=1)  # inclusive end date
            params.append(day)
            where.append(f"a.created_at {op} ${len(params)}::date")
    if cursor is not None:
        params.append(int(cursor))
        where.append(f"a.id < ${len(params)}")
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    pool = await get_pg_pool()

    if fmt == "csv":
        import csv
        import io
        import json

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT a.id, a.actor, a.action, a.detail, a.created_at, "
                f"t.slug AS tenant_slug "
                f"FROM audit_log a LEFT JOIN tenants t ON t.id = a.tenant_id {clause} "
                f"ORDER BY a.id DESC LIMIT 10000",
                *params,
            )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "created_at", "actor", "action", "tenant", "detail"])
        for r in rows:
            writer.writerow([
                int(r["id"]), _iso(r["created_at"]), r["actor"], r["action"],
                r["tenant_slug"] or "", json.dumps(r["detail"], ensure_ascii=False),
            ])
        from fastapi.responses import Response

        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"content-disposition": 'attachment; filename="audit-export.csv"'},
        )

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT a.id, a.actor, a.action, a.detail, a.created_at, t.slug AS tenant_slug "
            f"FROM audit_log a LEFT JOIN tenants t ON t.id = a.tenant_id {clause} "
            f"ORDER BY a.id DESC LIMIT ${len(params) + 1}",
            *params, limit + 1,
        )
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "entries": [
            {
                "id": int(r["id"]),
                "actor": r["actor"],
                "action": r["action"],
                "tenant": r["tenant_slug"],
                "detail": r["detail"],
                "created_at": _iso(r["created_at"]),
            }
            for r in rows
        ],
        "next_cursor": int(rows[-1]["id"]) if has_more and rows else None,
    }
