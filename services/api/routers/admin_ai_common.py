"""Shared helpers for the AI provider/pricing/finance admin routers."""

from __future__ import annotations

import re
from typing import Any

from acip_core.errors import error_response
from fastapi import Cookie, Header

_ADMIN = Header(default=None, alias="x-admin-token")
_AUTHZ = Header(default=None, alias="authorization")
_COOKIE = Cookie(default=None, alias="vitrin_admin_access")

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)
_TASKS = ("chat", "analyst")


async def _ok(token, authorization, cookie) -> bool:
    from .admin_common import _admin_ok

    return await _admin_ok(token, authorization, cookie)


def _forbidden():
    return error_response(401, "unauthorized", "A valid x-admin-token is required.")


def _not_found():
    return error_response(404, "not_found", "No such resource.")


def _invalid(msg: str):
    return error_response(422, "invalid_request", msg)


def _mask(key: str | None) -> str:
    if not key:
        return ""
    return f"…{key[-4:]}" if len(key) > 4 else "…"


def _invalidate_registry() -> None:
    """Make routing/pricing changes visible to the gateway immediately."""
    from ..runtime import get_provider_registry

    get_provider_registry().invalidate()


def _provider_row(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "name": r["name"],
        "kind": r["kind"],
        "base_url": r["base_url"],
        "api_key_masked": _mask(r["api_key"]),
        "has_api_key": bool(r["api_key"]),
        "is_local": r["is_local"],
        "enabled": r["enabled"],
        "timeout_s": float(r["timeout_s"]),
        "notes": r["notes"],
    }


def _model_row(r) -> dict[str, Any]:
    return {
        "id": str(r["id"]),
        "provider_id": str(r["provider_id"]),
        "model": r["model"],
        "label": r["label"],
        "input_usd_per_1m": float(r["input_usd_per_1m"]),
        "output_usd_per_1m": float(r["output_usd_per_1m"]),
        "enabled": r["enabled"],
    }
