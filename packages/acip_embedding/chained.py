"""Multi-provider embedding client, routed through the admin-configured
`embedding` task chain (mirrors chat/analyst routing in `acip_gateway`).

Same `.embed()`/`.embed_one()` interface as `EmbeddingClient`, so callers
don't change; falls back to the single env-configured local model when no
admin routing is configured, matching `ProviderRegistry`'s usual
degrade-to-env behavior for chat/analyst.
"""

from __future__ import annotations

from acip_core.logging import get_logger
from acip_gateway.registry import ProviderRegistry
from acip_gateway.retry import call_with_retry

from .client import EmbeddingClient, EmbeddingUnavailable, cache_get, cache_key, cache_set

log = get_logger("embedding.chained")


class ChainedEmbeddingClient:
    def __init__(self, registry: ProviderRegistry, redis=None) -> None:
        self._registry = registry
        self._redis = redis

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        endpoints = await self._registry.embedding_endpoints()
        last_exc: Exception | None = None
        for ep in endpoints:
            client = EmbeddingClient(
                redis=self._redis, base_url=ep.base_url, model=ep.model,
                dims=ep.dims, api_key=ep.api_key, wire=ep.wire,
            )

            async def _call(client: EmbeddingClient = client) -> list[list[float]]:
                return await client.embed(texts)

            try:
                return await call_with_retry(
                    _call, max_retries=ep.max_retries, backoff_ms=ep.retry_backoff_ms
                )
            except Exception as exc:  # noqa: BLE001 - fail over to the next endpoint
                last_exc = exc
                log.warning("embedding.endpoint_failed", model=ep.model, is_local=ep.is_local)
                continue
        raise EmbeddingUnavailable(f"all embedding endpoints failed; last error: {last_exc}")

    async def embed_one(self, text: str) -> list[float]:
        """Same cache-then-embed shape as `EmbeddingClient.embed_one`, keyed
        off the primary (position-0) endpoint's model/dims — a mid-chain
        failover just misses the cache for that call rather than corrupting
        it, since the key always names the model that's supposed to serve."""
        endpoints = await self._registry.embedding_endpoints()
        primary = endpoints[0] if endpoints else None
        key = cache_key(primary.model, primary.dims or 0, text) if primary else None
        if key is not None:
            cached = await cache_get(self._redis, key)
            if cached is not None:
                return cached
        vec = (await self.embed([text]))[0]
        if key is not None:
            await cache_set(self._redis, key, vec)
        return vec


def get_embedding_client_for_task(registry: ProviderRegistry, redis=None) -> ChainedEmbeddingClient:
    return ChainedEmbeddingClient(registry, redis=redis)
