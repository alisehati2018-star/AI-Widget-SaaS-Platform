"""Hermetic tests for provider quick-add templates + model discovery
normalization. Uses httpx.MockTransport — no network."""

from __future__ import annotations

import httpx
from acip_gateway.provider_templates import (
    PROVIDER_TEMPLATES,
    discover_models,
    get_template,
)


def test_templates_cover_expected_vendors():
    keys = {t["key"] for t in PROVIDER_TEMPLATES}
    assert keys == {
        "openrouter", "openai", "google", "deepseek", "groq",
        "bynara", "avalai", "conduit",
    }
    assert get_template("openai")["discover_kind"] == "openai_compatible"
    assert get_template("nonexistent") is None


async def test_discover_models_openai_compatible_shape():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(200, json={"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    models = await discover_models(
        base_url="https://api.openai.com/v1",
        api_key="sk-test",
        discover_kind="openai_compatible",
        client=client,
    )
    assert [m["model"] for m in models] == ["gpt-4o-mini", "gpt-4o"]


async def test_discover_models_openrouter_pricing_normalized_per_1m():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{
                "id": "acme/model-1",
                "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                "context_length": 8192,
            }]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    models = await discover_models(
        base_url="https://openrouter.ai/api/v1",
        api_key="k",
        discover_kind="openrouter",
        client=client,
    )
    assert models[0]["input_usd_per_1m"] == 1.0
    assert models[0]["output_usd_per_1m"] == 2.0
    assert models[0]["context_length"] == 8192


async def test_discover_models_google_strips_models_prefix():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"id": "models/gemini-2.5-flash"}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    models = await discover_models(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        api_key="k",
        discover_kind="google",
        client=client,
    )
    assert models[0]["model"] == "gemini-2.5-flash"


async def test_discover_models_raises_on_http_error():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(401, json={"error": "bad key"}))
    )
    try:
        await discover_models(
            base_url="https://api.openai.com/v1",
            api_key="bad",
            discover_kind="openai_compatible",
            client=client,
        )
        raise AssertionError("expected HTTPStatusError")
    except httpx.HTTPStatusError:
        pass
