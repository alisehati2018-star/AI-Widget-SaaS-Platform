"""Operator/admin API surface — tenant provisioning + platform overview.

The admin plane is **auth-separated** from tenant APIs (§9.2): every endpoint
requires the operator token (`x-admin-token`) or an admin-plane session,
distinct from tenant API keys, via `_admin_ok` (shared in `admin_common`).

This module owns tenant creation, the platform KPI overview, the tenant list,
and the tenant detail view. Per-tenant mutations (notes, keys, credits, plan,
status) live in `admin_tenant_ops.py`. Every other admin domain (users, audit,
billing ops, search/insight, governance, security, monitoring, Elasticsearch
console, agent test, plans, invoices, contact inbox, widget defaults) lives in
its own `admin_*` router — all mounted under the same `/admin` prefix in
`main.py`, so the split is invisible to clients.
"""

from __future__ import annotations

import secrets
from typing import Any

from acip_billing import plan_status as _plan_status
from acip_billing import usage_summary as _usage_summary
from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from ..deps import hash_key
from .admin_common import (
    _ADMIN,
    _AUTHZ,
    _COOKIE,
    _admin_ok,
    _forbidden,
    _iso,
    _key_rows,
    _not_found,
    _valid_uuid,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/tenants")
async def create_tenant(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    slug = str(payload.get("slug", "")).strip()
    name = str(payload.get("name", slug)).strip()
    scope = str(payload.get("scope", "widget"))
    if not slug:
        return error_response(422, "invalid_request", "Field 'slug' is required.")
    raw_key = "acip_" + secrets.token_urlsafe(24)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            tenant_id = await conn.fetchval(
                "INSERT INTO tenants (slug, name) VALUES ($1, $2) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                slug,
                name,
            )
            await conn.execute(
                "INSERT INTO api_keys (tenant_id, key_hash, scope, label) VALUES ($1, $2, $3, $4)",
                tenant_id,
                hash_key(raw_key),
                scope,
                "provisioned",
            )
    await audit(
        pool,
        actor="operator",
        action="tenant.create",
        tenant_id=str(tenant_id),
        detail={"slug": slug, "scope": scope},
    )
    # The raw key is returned exactly once; only its hash is stored.
    return {"tenant_id": str(tenant_id), "slug": slug, "api_key": raw_key, "scope": scope}


def _daily_series(rows, days: int, *fields: str) -> list[dict[str, Any]]:
    """Fill grouped-by-day query rows into a dense series of the last N days
    (oldest → newest), zeroing days with no data so charts render evenly."""
    from datetime import UTC, date, timedelta
    from datetime import datetime as _dt

    by_day: dict[date, Any] = {r["d"]: r for r in rows}
    today = _dt.now(UTC).date()
    series: list[dict[str, Any]] = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        row = by_day.get(day)
        point: dict[str, Any] = {"date": day.isoformat()}
        for f in fields:
            point[f] = float(row[f]) if row is not None and row[f] is not None else 0.0
        series.append(point)
    return series


@router.get("/overview")
async def overview(
    days: int = 30,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Platform-wide KPIs + daily trends for the admin dashboard.

    Trends cover the last ``days`` (7–90) days: tenant signups, usage events,
    paid revenue, and failed payments. MRR is a point-in-time figure (no
    historical snapshots exist), so its trend proxy is daily paid revenue."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    days = max(7, min(int(days), 90))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        tenants = await conn.fetchval("SELECT count(*) FROM tenants")
        users = await conn.fetchval("SELECT count(*) FROM users")
        active_subs = await conn.fetchval(
            "SELECT count(*) FROM subscriptions WHERE status IN ('active', 'trialing')"
        )
        past_due = await conn.fetchval(
            "SELECT count(*) FROM subscriptions WHERE status = 'past_due'"
        )
        mrr = await conn.fetchval(
            "SELECT COALESCE(sum(p.price_monthly), 0) FROM subscriptions s "
            "JOIN plans p ON p.id = s.plan_id WHERE s.status = 'active'"
        )
        signup_rows = await conn.fetch(
            "SELECT (created_at AT TIME ZONE 'UTC')::date AS d, count(*)::float AS signups "
            "FROM tenants "
            "WHERE created_at >= now() - make_interval(days => $1) GROUP BY 1",
            days,
        )
        usage_rows = await conn.fetch(
            "SELECT (occurred_at AT TIME ZONE 'UTC')::date AS d, count(*)::float AS calls, "
            "COALESCE(sum(cost), 0)::float AS credits FROM usage_events "
            "WHERE occurred_at >= now() - make_interval(days => $1) GROUP BY 1",
            days,
        )
        revenue_rows = await conn.fetch(
            "SELECT (COALESCE(paid_at, created_at) AT TIME ZONE 'UTC')::date AS d, "
            "COALESCE(sum(amount), 0)::float AS revenue FROM orders "
            "WHERE status = 'paid' "
            "AND COALESCE(paid_at, created_at) >= now() - make_interval(days => $1) GROUP BY 1",
            days,
        )
        failed_rows = await conn.fetch(
            "SELECT (created_at AT TIME ZONE 'UTC')::date AS d, count(*)::float AS failed "
            "FROM orders WHERE status = 'failed' "
            "AND created_at >= now() - make_interval(days => $1) GROUP BY 1",
            days,
        )
    signups = _daily_series(signup_rows, days, "signups")
    usage = _daily_series(usage_rows, days, "calls", "credits")
    revenue = _daily_series(revenue_rows, days, "revenue")
    failed = _daily_series(failed_rows, days, "failed")
    return {
        "tenants": int(tenants or 0),
        "users": int(users or 0),
        "active_subscriptions": int(active_subs or 0),
        "past_due_subscriptions": int(past_due or 0),
        "mrr": float(mrr or 0),
        "days": days,
        "trends": {
            "signups": signups,
            "usage": usage,
            "revenue": revenue,
            "failed_payments": failed,
        },
        "totals": {
            "signups": sum(p["signups"] for p in signups),
            "calls": sum(p["calls"] for p in usage),
            "revenue": sum(p["revenue"] for p in revenue),
            "failed_payments": sum(p["failed"] for p in failed),
        },
    }


@router.get("/tenants")
async def list_tenants(
    q: str = "",
    status: str = "",
    plan: str = "",
    limit: int = 50,
    offset: int = 0,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """List tenants with plan + subscription status, filterable and paginated.

    ``q`` matches slug or name (case-insensitive substring); ``status`` filters
    the tenant lifecycle state; ``plan`` filters by plan code."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    where: list[str] = []
    args: list[Any] = []
    if q.strip():
        args.append(f"%{q.strip().lower()}%")
        where.append(f"(lower(t.slug) LIKE ${len(args)} OR lower(t.name) LIKE ${len(args)})")
    if status.strip():
        args.append(status.strip())
        where.append(f"t.status = ${len(args)}")
    if plan.strip():
        args.append(plan.strip())
        where.append(f"p.code = ${len(args)}")
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    base = (
        "FROM tenants t "
        "LEFT JOIN subscriptions s ON s.tenant_id = t.id "
        "LEFT JOIN plans p ON p.id = s.plan_id "
        f"{where_sql}"
    )
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(f"SELECT count(*) {base}", *args)
        rows = await conn.fetch(
            "SELECT t.id, t.slug, t.name, t.status, t.created_at, "
            "COALESCE(p.name, '—') AS plan, COALESCE(p.code, '') AS plan_code, "
            f"COALESCE(s.status, 'none') AS sub_status {base} "
            f"ORDER BY t.created_at DESC LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}",
            *args,
            limit,
            offset,
        )
    return {
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "tenants": [
            {
                "id": str(r["id"]),
                "slug": r["slug"],
                "name": r["name"],
                "status": r["status"],
                "plan": r["plan"],
                "plan_code": r["plan_code"],
                "sub_status": r["sub_status"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.get("/tenants/{tenant_id}")
async def tenant_detail(
    tenant_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """The complete operator view of one store: profile, subscription, credits,
    masked API keys, sync state, and team size — one call for the detail page."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(tenant_id):
        return _not_found()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        t = await conn.fetchrow(
            "SELECT t.id, t.slug, t.name, t.status, t.tracking_enabled, t.settings, "
            "t.admin_notes, t.created_at, t.updated_at, "
            "s.status AS sub_status, s.current_period_end, s.cancel_at_period_end, "
            "p.code AS plan_code, p.name AS plan_name, p.price_monthly, p.currency "
            "FROM tenants t "
            "LEFT JOIN subscriptions s ON s.tenant_id = t.id "
            "LEFT JOIN plans p ON p.id = s.plan_id WHERE t.id = $1",
            tenant_id,
        )
        if t is None:
            return _not_found()
        keys = await _key_rows(conn, tenant_id)
        sync_rows = await conn.fetch(
            "SELECT source, high_watermark, last_run_at, last_status "
            "FROM sync_state WHERE tenant_id = $1 ORDER BY source",
            tenant_id,
        )
        team = await conn.fetchval("SELECT count(*) FROM users WHERE tenant_id = $1", tenant_id)
    usage = await _usage_summary(pool, tenant_id)
    status = await _plan_status(pool, tenant_id)
    return {
        "id": str(t["id"]),
        "slug": t["slug"],
        "name": t["name"],
        "status": t["status"],
        "tracking_enabled": t["tracking_enabled"],
        "settings": t["settings"],
        "admin_notes": t["admin_notes"],
        "created_at": _iso(t["created_at"]),
        "updated_at": _iso(t["updated_at"]),
        "team_size": int(team or 0),
        "subscription": {
            "plan_code": t["plan_code"],
            "plan_name": t["plan_name"],
            "price_monthly": float(t["price_monthly"]) if t["price_monthly"] is not None else None,
            "currency": t["currency"],
            "status": t["sub_status"] or "none",
            "current_period_end": _iso(t["current_period_end"]),
            "cancel_at_period_end": bool(t["cancel_at_period_end"] or False),
        },
        "credits": {
            "used": usage["used"],
            "granted": usage["granted"],
            "balance": status.get("balance", 0.0),
            "cap": status.get("cap"),
            "within_plan": status.get("within_plan", True),
        },
        "api_keys": keys,
        "sync_state": [
            {
                "source": r["source"],
                "high_watermark": _iso(r["high_watermark"]),
                "last_run_at": _iso(r["last_run_at"]),
                "last_status": r["last_status"],
            }
            for r in sync_rows
        ],
    }
