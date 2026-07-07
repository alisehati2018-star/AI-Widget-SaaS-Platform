"""Admin surface — plan management (M11): operators edit pricing, included
credits, caps, rate limits and visibility of subscription plans."""

from __future__ import annotations

import re
from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden, _valid_uuid

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/plans")
async def list_plans(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, code, name, description, price_monthly, currency, credits_per_month, "
            "monthly_credit_cap, rate_limit_per_min, is_public, sort_order, features, "
            "name_fa, description_fa, features_fa "
            "FROM plans ORDER BY sort_order ASC, price_monthly ASC"
        )
    return {
        "plans": [
            {
                "id": str(r["id"]),
                "code": r["code"],
                "name": r["name"],
                "description": r["description"],
                "price_monthly": float(r["price_monthly"]),
                "currency": r["currency"],
                "credits_per_month": float(r["credits_per_month"]),
                "monthly_credit_cap": float(r["monthly_credit_cap"]),
                "rate_limit_per_min": r["rate_limit_per_min"],
                "is_public": r["is_public"],
                "sort_order": r["sort_order"],
                "features": r["features"],
                "name_fa": r["name_fa"],
                "description_fa": r["description_fa"],
                "features_fa": r["features_fa"],
            }
            for r in rows
        ]
    }


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Edit a plan's pricing, included credits, caps, limits and visibility."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    columns = {
        "name": str,
        "name_fa": str,
        "description": str,
        "description_fa": str,
        "price_monthly": float,
        "currency": str,
        "credits_per_month": float,
        "monthly_credit_cap": float,
        "rate_limit_per_min": int,
        "is_public": bool,
        "sort_order": int,
    }
    sets: list[str] = []
    values: list[Any] = []
    for col, caster in columns.items():
        if col in payload:
            try:
                values.append(caster(payload[col]))
            except (TypeError, ValueError):
                return error_response(422, "invalid_request", f"Invalid value for '{col}'.")
            sets.append(f"{col} = ${len(values)}")
    if not sets:
        return error_response(422, "invalid_request", "No editable fields supplied.")
    values.append(plan_id)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            f"UPDATE plans SET {', '.join(sets)} WHERE id = ${len(values)}::uuid RETURNING id",
            *values,
        )
    if updated is None:
        return error_response(404, "not_found", "No such plan.")
    await audit(pool, actor="operator", action="plan.update",
                detail={"plan_id": plan_id, "fields": list(payload.keys())})
    return {"plan_id": plan_id, "status": "updated"}


_PLAN_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,30}$")


@router.post("/plans")
async def create_plan(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Create a new pricing plan. `code` is the stable identifier used by
    checkout and the public /plans page; it cannot be changed later."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    code = str(payload.get("code", "")).strip().lower()
    name = str(payload.get("name", "")).strip()
    if not _PLAN_CODE_RE.match(code):
        return error_response(
            422, "invalid_request",
            "Field 'code' must be 2-31 chars of a-z, 0-9, '-' or '_'.",
        )
    if not name:
        return error_response(422, "invalid_request", "Field 'name' is required.")
    optional = {
        "name_fa": (str, None),
        "description": (str, None),
        "description_fa": (str, None),
        "price_monthly": (float, 0.0),
        "currency": (str, "USD"),
        "credits_per_month": (float, 0.0),
        "monthly_credit_cap": (float, 100000.0),
        "rate_limit_per_min": (int, 120),
        "is_public": (bool, True),
        "sort_order": (int, 100),
    }
    values: dict[str, Any] = {}
    for col, (caster, default) in optional.items():
        if col in payload and payload[col] is not None:
            try:
                values[col] = caster(payload[col])
            except (TypeError, ValueError):
                return error_response(422, "invalid_request", f"Invalid value for '{col}'.")
        else:
            values[col] = default
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        if await conn.fetchval("SELECT 1 FROM plans WHERE code = $1", code):
            return error_response(409, "code_taken", "A plan with this code already exists.")
        plan_id = await conn.fetchval(
            "INSERT INTO plans (code, name, name_fa, description, description_fa, "
            "price_monthly, currency, credits_per_month, monthly_credit_cap, "
            "rate_limit_per_min, is_public, sort_order) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) RETURNING id",
            code, name, values["name_fa"], values["description"], values["description_fa"],
            values["price_monthly"], values["currency"],
            values["credits_per_month"], values["monthly_credit_cap"],
            values["rate_limit_per_min"], values["is_public"], values["sort_order"],
        )
    await audit(pool, actor="operator", action="plan.create",
                detail={"plan_id": str(plan_id), "code": code})
    return {"plan_id": str(plan_id), "code": code, "status": "created"}


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Delete a plan that is not referenced by any tenant, subscription or
    order. Plans in use must be hidden (`is_public = false`) instead."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    if not _valid_uuid(plan_id):
        return error_response(404, "not_found", "No such plan.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        refs = await conn.fetchrow(
            "SELECT (SELECT count(*) FROM tenants WHERE plan_id = $1::uuid) AS tenants, "
            "(SELECT count(*) FROM subscriptions WHERE plan_id = $1::uuid) AS subs, "
            "(SELECT count(*) FROM orders WHERE plan_id = $1::uuid) AS orders",
            plan_id,
        )
        in_use = int(refs["tenants"]) + int(refs["subs"]) + int(refs["orders"])
        if in_use:
            return error_response(
                409, "plan_in_use",
                f"Plan is referenced by {refs['tenants']} tenant(s), {refs['subs']} "
                f"subscription(s) and {refs['orders']} order(s); hide it instead.",
            )
        deleted = await conn.fetchval(
            "DELETE FROM plans WHERE id = $1::uuid RETURNING code", plan_id
        )
    if deleted is None:
        return error_response(404, "not_found", "No such plan.")
    await audit(pool, actor="operator", action="plan.delete",
                detail={"plan_id": plan_id, "code": deleted})
    return {"plan_id": plan_id, "status": "deleted"}
