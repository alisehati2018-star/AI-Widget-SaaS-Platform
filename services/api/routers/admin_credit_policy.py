"""Admin surface — signup credit policy (M11 follow-up).

A dedicated, single-row settings surface for "how many credits does a
brand-new self-serve signup get" — deliberately separate from
`pricing_settings` (what a credit is worth) and from a plan's
`credits_per_month` (its advertised *monthly* allowance, granted only on
paid-plan activation/renewal). Read by `auth.py::_grant_signup_credit` at
signup time; granting free credit to one specific existing customer is a
different, already-existing flow (`POST /admin/tenants/{id}/credits`).
"""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


def _policy_row(r) -> dict[str, Any]:
    return {
        "auto_grant_enabled": r["auto_grant_enabled"],
        "signup_credits": float(r["signup_credits"]),
    }


@router.get("/credit-policy")
async def get_credit_policy(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT auto_grant_enabled, signup_credits FROM signup_credit_policy WHERE id"
        )
    return _policy_row(row)


@router.put("/credit-policy")
async def put_credit_policy(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    fields: dict[str, Any] = {}
    if "auto_grant_enabled" in payload:
        fields["auto_grant_enabled"] = bool(payload["auto_grant_enabled"])
    if "signup_credits" in payload:
        try:
            amount = float(payload["signup_credits"])
        except (TypeError, ValueError):
            return error_response(422, "invalid_request", "'signup_credits' must be a number.")
        if not (0 <= amount <= 1_000_000):
            return error_response(
                422, "invalid_request", "'signup_credits' must be between 0 and 1,000,000."
            )
        fields["signup_credits"] = amount
    if not fields:
        return error_response(422, "invalid_request", "No editable fields provided.")
    sets = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(fields))
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE signup_credit_policy SET {sets}, updated_at = now() "  # noqa: S608
            "WHERE id RETURNING auto_grant_enabled, signup_credits",
            *fields.values(),
        )
    await audit(pool, actor="operator", action="credit_policy.update", detail=fields)
    return _policy_row(row)
