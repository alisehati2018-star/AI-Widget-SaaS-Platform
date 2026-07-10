"""Best-effort external credit/balance check for a configured provider.

Not every vendor exposes a balance API — OpenRouter does (`/auth/key`); most
others (OpenAI, Google, generic OpenAI-compatible gateways) don't expose a
prepaid-balance endpoint at all, so for those this degrades to a "key health"
check (models endpoint responds => key is valid) plus a note pointing the
admin at platform usage stats / the vendor's own dashboard instead of a
number that doesn't exist. Mirrors the shape of a reference project's
provider-credit check, reimplemented from scratch against this codebase's
httpx/async conventions.
"""

from __future__ import annotations

from typing import Any

import httpx


async def _get_json(url: str, headers: dict[str, str], timeout: float = 15.0) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _check_openrouter(base_url: str, api_key: str) -> dict[str, Any]:
    data = await _get_json(
        "https://openrouter.ai/api/v1/auth/key",
        {"Authorization": f"Bearer {api_key}"},
    )
    d = data.get("data") or data
    usage = float(d.get("usage") or 0)
    limit = d.get("limit")
    limit_f = float(limit) if limit is not None else None
    return {
        "source": "external_api",
        "usage": usage,
        "limit": limit_f,
        "remaining": max(0.0, limit_f - usage) if limit_f is not None else None,
        "currency": "USD",
    }


async def _check_key_health(
    base_url: str, api_key: str, note: str, dashboard_url: str
) -> dict[str, Any]:
    data = await _get_json(
        f"{base_url.rstrip('/')}/models", {"Authorization": f"Bearer {api_key}"}
    )
    count = len(data.get("data") or data.get("models") or [])
    return {
        "source": "api_key_check",
        "key_valid": True,
        "models_available": count,
        "note": note,
        "dashboard_url": dashboard_url,
    }


_NOTES: dict[str, tuple[str, str]] = {
    "openai": (
        "OpenAI does not expose prepaid balance via standard API keys. "
        "Use platform usage below or the OpenAI dashboard.",
        "https://platform.openai.com/usage",
    ),
    "google": (
        "Google AI Studio does not expose account balance via API. "
        "Use platform usage below or Google AI Studio / Cloud billing.",
        "https://aistudio.google.com/",
    ),
    "bynara": (
        "This gateway does not expose account balance via API. "
        "Use platform usage below or the vendor's own dashboard.",
        "https://router.bynara.id/keys",
    ),
    "conduit": (
        "This gateway does not expose account balance via API. "
        "Use platform usage below or the vendor's own dashboard.",
        "https://conduit.ozdoev.net",
    ),
}


async def check_provider_credit(
    *, base_url: str, api_key: str, discover_kind: str
) -> dict[str, Any]:
    """Raises `httpx.HTTPError` on failure — caller turns that into a
    user-facing error."""
    if discover_kind == "openrouter":
        return await _check_openrouter(base_url, api_key)
    note, dashboard_url = _NOTES.get(
        discover_kind,
        ("External balance not available for this provider. See platform usage stats.", ""),
    )
    return await _check_key_health(base_url, api_key, note, dashboard_url)
