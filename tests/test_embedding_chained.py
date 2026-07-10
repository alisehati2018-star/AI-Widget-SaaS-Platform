"""Unit tests for the embedding-task registry chain + ChainedEmbeddingClient
failover. Hermetic: monkeypatches the registry snapshot and the
`EmbeddingClient` class `chained.py` constructs internally — no network."""

from __future__ import annotations

import acip_embedding.chained as chained_mod
import httpx
from acip_embedding.chained import ChainedEmbeddingClient
from acip_gateway.registry import EmbeddingEndpoint, ProviderRegistry, RegistrySnapshot


async def test_embedding_endpoints_falls_back_to_env_when_unconfigured(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)

    async def fake_snapshot():
        return RegistrySnapshot(loaded_at=0.0)

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    endpoints = await reg.embedding_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].is_local and endpoints[0].wire == "tei"


async def test_embedding_endpoints_from_db_chain(monkeypatch):
    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(
        embedding_endpoints=[
            EmbeddingEndpoint(
                base_url="https://api.openai.com/v1", api_key="k", model="text-embedding-3-small",
                dims=1536, is_local=False, wire="openai",
            ),
        ],
        loaded_at=0.0,
    )

    async def fake_snapshot():
        return snap

    monkeypatch.setattr(reg, "snapshot", fake_snapshot)
    endpoints = await reg.embedding_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0].wire == "openai" and endpoints[0].model == "text-embedding-3-small"


class _FakeRegistry:
    def __init__(self, endpoints: list[EmbeddingEndpoint]) -> None:
        self._endpoints = endpoints

    async def embedding_endpoints(self):
        return self._endpoints


async def test_chained_client_fails_over_to_next_embedding_endpoint(monkeypatch):
    calls = {"acme": 0, "local": 0}

    class FakeEmbeddingClient:
        def __init__(self, **kwargs):
            self._model = kwargs["model"]

        async def embed(self, texts):
            if self._model == "acme-embed":
                calls["acme"] += 1
                raise httpx.TimeoutException("timed out")
            calls["local"] += 1
            return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(chained_mod, "EmbeddingClient", FakeEmbeddingClient)

    registry = _FakeRegistry([
        EmbeddingEndpoint(base_url="https://acme", api_key="k", model="acme-embed",
                          dims=768, is_local=False, wire="openai"),
        EmbeddingEndpoint(base_url="http://local:8080", api_key=None, model="local-embed",
                          dims=768, is_local=True, wire="tei"),
    ])
    client = ChainedEmbeddingClient(registry)
    vectors = await client.embed(["hello"])
    assert vectors == [[0.1, 0.2]]
    assert calls == {"acme": 1, "local": 1}


async def test_chained_client_embed_one_uses_primary_endpoint_cache_key(monkeypatch):
    class FakeRedis:
        def __init__(self):
            self.kv: dict[str, list[str]] = {}

        async def lrange(self, k, a, b):
            return self.kv.get(k, [])

        async def delete(self, k):
            self.kv.pop(k, None)

        async def rpush(self, k, *vals):
            self.kv.setdefault(k, []).extend(vals)

        async def expire(self, k, ttl):
            pass

    class FakeEmbeddingClient:
        def __init__(self, **kwargs):
            pass

        async def embed(self, texts):
            return [[9.0, 9.0] for _ in texts]

    monkeypatch.setattr(chained_mod, "EmbeddingClient", FakeEmbeddingClient)
    registry = _FakeRegistry([
        EmbeddingEndpoint(base_url="http://local:8080", api_key=None, model="local-embed",
                          dims=768, is_local=True, wire="tei"),
    ])
    redis = FakeRedis()
    client = ChainedEmbeddingClient(registry, redis=redis)
    vec1 = await client.embed_one("hello")
    assert vec1 == [9.0, 9.0]
    assert redis.kv  # cached under the primary endpoint's model/dims
    vec2 = await client.embed_one("hello")
    assert vec2 == [9.0, 9.0]
