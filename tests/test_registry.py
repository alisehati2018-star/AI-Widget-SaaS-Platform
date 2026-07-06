"""Unit tests for the DB-backed provider registry (multi-provider FinOps)."""

from __future__ import annotations

from acip_billing.pricing import ModelPrice, PricingConfig
from acip_gateway.failover import Endpoint
from acip_gateway.llm_client import LLMClient, LLMResponse
from acip_gateway.registry import DynamicProviderChain, ProviderRegistry, RegistrySnapshot


def _local_endpoint() -> Endpoint:
    return Endpoint(client=LLMClient("http://local:8000", provider="local"),
                     model="local-model", is_local=True)


def _frontier_endpoint() -> Endpoint:
    return Endpoint(client=LLMClient("https://api.example", provider="acme"),
                     model="acme-1", is_local=False)


async def test_registry_falls_back_to_env_chain_when_task_empty(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)

    async def fake_snapshot():
        return RegistrySnapshot(endpoints_by_task={}, loaded_at=0.0)

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    chain = await reg.endpoints("chat")
    assert chain  # env fallback always yields at least the local endpoint
    assert chain[-1].is_local


async def test_registry_appends_local_when_db_chain_has_none(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(
        endpoints_by_task={"chat": [_frontier_endpoint()]}, loaded_at=0.0
    )

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    chain = await reg.endpoints("chat")
    assert chain[0].client.provider_name == "acme"
    assert chain[-1].is_local  # env local terminal appended for the invariant


async def test_registry_db_chain_with_local_terminal_used_as_is(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(
        endpoints_by_task={"chat": [_frontier_endpoint(), _local_endpoint()]}, loaded_at=0.0
    )

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    chain = await reg.endpoints("chat")
    assert len(chain) == 2  # no extra env endpoint appended


async def test_registry_price_lookup(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)
    price = ModelPrice(provider="acme", model="acme-1", input_usd_per_1m=1.0, output_usd_per_1m=2.0)
    snap = RegistrySnapshot(prices={("acme", "acme-1"): price}, loaded_at=0.0)

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    assert await reg.price_for("acme", "acme-1") == price
    assert await reg.price_for("acme", "unknown-model") is None


async def test_registry_pricing_defaults(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)

    async def fake_snapshot():
        return RegistrySnapshot(loaded_at=0.0)

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    cfg = await reg.pricing()
    assert cfg == PricingConfig()


async def test_registry_invalidate_clears_cache():
    reg = ProviderRegistry(pool_getter=None)
    reg._snap = RegistrySnapshot(loaded_at=1e18)  # far future, would never expire
    reg.invalidate()
    assert reg._snap is None


async def test_dynamic_chain_fails_over_within_task(monkeypatch):
    class Boom:
        provider_name = "acme"

        async def chat(self, *a, **k):
            raise RuntimeError("down")

    class Ok:
        provider_name = "local"

        async def chat(self, *a, **k):
            return LLMResponse(text="ok", model="local-model", provider="local")

    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(
        endpoints_by_task={
            "chat": [
                Endpoint(client=Boom(), model="acme-1", is_local=False),
                Endpoint(client=Ok(), model="local-model", is_local=True),
            ]
        },
        loaded_at=0.0,
    )

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    chain = DynamicProviderChain(reg, task="chat")
    resp = await chain.generate([{"role": "user", "content": "x"}])
    assert resp.text == "ok" and resp.provider == "local"


async def test_dynamic_chain_prefer_local_filters_chain(monkeypatch):
    class Frontier:
        provider_name = "acme"

        async def chat(self, *a, **k):
            return LLMResponse(text="frontier-answer", model="acme-1", provider="acme")

    class Local:
        provider_name = "local"

        async def chat(self, *a, **k):
            return LLMResponse(text="local-answer", model="local-model", provider="local")

    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(
        endpoints_by_task={
            "chat": [
                Endpoint(client=Frontier(), model="acme-1", is_local=False),
                Endpoint(client=Local(), model="local-model", is_local=True),
            ]
        },
        loaded_at=0.0,
    )

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    chain = DynamicProviderChain(reg, task="chat")
    resp = await chain.generate([{"role": "user", "content": "x"}], prefer_local=True)
    assert resp.text == "local-answer"
