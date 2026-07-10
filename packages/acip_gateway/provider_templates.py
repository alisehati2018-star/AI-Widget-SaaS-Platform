"""Quick-add provider templates + live model discovery.

Every vendor here is OpenAI-wire-compatible (`GET {base_url}/models`, Bearer
auth) — same assumption `llm_client.py::LLMClient` already makes for chat
completions, so no vendor SDKs are needed. `discover_kind` only changes how
the model-list *response* is normalized (id format, pricing fields), not the
transport. Concept mirrors a reference project's provider-template/discovery
pattern; reimplemented from scratch against this codebase's conventions.
"""

from __future__ import annotations

from typing import Any, TypedDict

import httpx


class ProviderTemplate(TypedDict):
    key: str
    display_name: str
    base_url: str
    discover_kind: str
    description: str
    dashboard_url: str


# Deliberately excludes a `freellmapi`-style local desktop proxy some
# reference implementations include — meaningless for a server deployment.
PROVIDER_TEMPLATES: list[ProviderTemplate] = [
    {
        "key": "openrouter",
        "display_name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "discover_kind": "openrouter",
        "description": "Aggregator gateway to many models with one key; its /models "
        "response includes live per-token pricing.",
        "dashboard_url": "https://openrouter.ai/keys",
    },
    {
        "key": "openai",
        "display_name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "discover_kind": "openai_compatible",
        "description": "Official OpenAI API.",
        "dashboard_url": "https://platform.openai.com/api-keys",
    },
    {
        "key": "google",
        "display_name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "discover_kind": "google",
        "description": "Gemini via its OpenAI-compatibility endpoint.",
        "dashboard_url": "https://aistudio.google.com/apikey",
    },
    {
        "key": "deepseek",
        "display_name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "discover_kind": "openai_compatible",
        "description": "DeepSeek's OpenAI-compatible API.",
        "dashboard_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "key": "groq",
        "display_name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "discover_kind": "openai_compatible",
        "description": "Groq's OpenAI-compatible low-latency inference API.",
        "dashboard_url": "https://console.groq.com/keys",
    },
    {
        "key": "bynara",
        "display_name": "Bynara (NaraRouter)",
        "base_url": "https://router.bynara.id/v1",
        "discover_kind": "bynara",
        "description": "Regional multi-model router gateway.",
        "dashboard_url": "https://bynara.id",
    },
    {
        "key": "avalai",
        "display_name": "AvalAI",
        "base_url": "https://api.avalai.ir/v1",
        "discover_kind": "openai_compatible",
        "description": "Regional OpenAI-compatible gateway.",
        "dashboard_url": "https://avalai.ir",
    },
    {
        "key": "conduit",
        "display_name": "Conduit",
        "base_url": "https://conduit.ozdoev.net/api/v1",
        "discover_kind": "conduit",
        "description": "OpenAI-compatible gateway to a broad model catalogue.",
        "dashboard_url": "https://conduit.ozdoev.net",
    },
]

_BY_KEY = {t["key"]: t for t in PROVIDER_TEMPLATES}


def get_template(key: str) -> ProviderTemplate | None:
    return _BY_KEY.get(key)


def _per_1m(price_per_token: Any) -> float:
    """Vendor `/models` pricing is USD-per-token (OpenRouter-style string);
    ai_models stores USD-per-1M-tokens."""
    try:
        return float(price_per_token) * 1_000_000
    except (TypeError, ValueError):
        return 0.0


class DiscoveredModel(TypedDict):
    model: str
    label: str
    input_usd_per_1m: float
    output_usd_per_1m: float
    context_length: int | None


def _normalize_openai_style(payload: dict[str, Any]) -> list[DiscoveredModel]:
    items = payload.get("data") or payload.get("models") or []
    out: list[DiscoveredModel] = []
    for it in items:
        model_id = str(it.get("id") or it.get("name") or "").strip()
        if not model_id:
            continue
        pricing = it.get("pricing") or {}
        out.append(
            {
                "model": model_id,
                "label": str(it.get("name") or model_id),
                "input_usd_per_1m": _per_1m(pricing.get("prompt")),
                "output_usd_per_1m": _per_1m(pricing.get("completion")),
                "context_length": it.get("context_length") or it.get("context_window"),
            }
        )
    return out


def _strip_google_prefix(models: list[DiscoveredModel]) -> list[DiscoveredModel]:
    for m in models:
        if m["model"].startswith("models/"):
            m["model"] = m["model"][len("models/"):]
    return models


async def discover_models(
    *,
    base_url: str,
    api_key: str,
    discover_kind: str,
    timeout: float = 15.0,
    client: httpx.AsyncClient | None = None,
) -> list[DiscoveredModel]:
    """Fetch and normalize the live model list for a configured provider.
    Raises `httpx.HTTPError` on failure — the caller turns that into a
    user-facing error, it is not swallowed here. `client` is injectable for
    hermetic tests (`httpx.MockTransport`); production callers omit it."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    url = f"{base_url.rstrip('/')}/models"

    async def _get(c: httpx.AsyncClient) -> dict[str, Any]:
        resp = await c.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    if client is not None:
        payload = await _get(client)
    else:
        async with httpx.AsyncClient(timeout=timeout) as owned_client:
            payload = await _get(owned_client)
    models = _normalize_openai_style(payload)
    if discover_kind == "google":
        models = _strip_google_prefix(models)
    return models
