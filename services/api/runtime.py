"""Lazily-constructed service singletons for the API process (Phase 1-2).

Wires the search service (M5) and the RAG assistant (M7) with the gateway
(M6: cache → route → compress → failover → meter). Constructors do no I/O until
first use.
"""

from __future__ import annotations

from functools import lru_cache

from acip_assistant.memory import SessionMemory
from acip_assistant.rag import RagAssistant
from acip_billing.ledger import record_charge
from acip_cache.data_version import current_data_version
from acip_cache.l1 import L1ExactCache
from acip_cache.l2 import L2SemanticCache
from acip_cache.metering import record_usage
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_core.config import get_settings
from acip_core.ratelimit import RateLimiter
from acip_embedding import get_embedding_client
from acip_gateway.budget import BudgetGuard
from acip_gateway.failover import Endpoint, ProviderChain
from acip_gateway.llm_client import LLMClient
from acip_gateway.router import GatewayRouter
from acip_search.retrieval import SearchService


async def _meter(tenant_id: str, **kwargs) -> None:
    pool = await get_pg_pool()
    await record_usage(pool, tenant_id, **kwargs)
    # Persist the per-rung charge to the credit ledger (REQ-M11-009).
    cost = float(kwargs.get("cost", 0.0) or 0.0)
    if cost > 0:
        await record_charge(pool, tenant_id, rung=str(kwargs.get("rung", "")), cost=cost)


@lru_cache
def get_rate_limiter() -> RateLimiter:
    # Default per-minute ceiling; per-tenant plan limits are applied from the
    # `plans` table during validation/runtime tuning.
    return RateLimiter(get_redis(), default_per_min=120)


@lru_cache
def get_search_service() -> SearchService:
    redis = get_redis()
    return SearchService(
        es=get_es_client(),
        embedding_client=get_embedding_client(redis=redis),
        redis=redis,
        meter=_meter,
    )


@lru_cache
def get_provider_chain() -> ProviderChain:
    """Process-wide provider chain (frontier → local), reused by the analyst."""
    return _provider_chain()


def _provider_chain() -> ProviderChain:
    """Frontier (optional) → local. The chain MUST end at a local endpoint."""
    s = get_settings()
    endpoints: list[Endpoint] = []
    if s.frontier_enabled and s.frontier_url:
        endpoints.append(
            Endpoint(
                client=LLMClient(s.frontier_url, provider="frontier", api_key=s.frontier_api_key),
                model=s.frontier_model or s.llm_model,
                is_local=False,
            )
        )
    endpoints.append(
        Endpoint(client=LLMClient(s.llm_url, provider="local"), model=s.llm_model, is_local=True)
    )
    return ProviderChain(endpoints)


@lru_cache
def get_assistant() -> RagAssistant:
    s = get_settings()
    redis = get_redis()
    embed_client = get_embedding_client(redis=redis)
    search = get_search_service()

    async def retrieve(tenant_id: str, query: str) -> list[dict]:
        res = await search.search(tenant_id, query)
        return res.get("results", [])

    async def embed(text: str) -> list[float] | None:
        try:
            return await embed_client.embed_one(text)
        except Exception:  # noqa: BLE001 - degrade (skip L2 / vector leg)
            return None

    async def data_version(tenant_id: str) -> int:
        return await current_data_version(redis, tenant_id)

    router = GatewayRouter(
        l1=L1ExactCache(redis),
        l2=L2SemanticCache(redis),
        budget=BudgetGuard(redis, default_cap=s.budget_default_cap),
        providers=_provider_chain(),
        meter=_meter,
    )
    return RagAssistant(
        router,
        retrieve=retrieve,
        embed=embed,
        session_memory=SessionMemory(redis),
        data_version=data_version,
    )
