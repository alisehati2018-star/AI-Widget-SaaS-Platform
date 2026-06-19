"""Lazily-constructed service singletons for the API process (Phase 1).

Wires the search service with its embedding client, Redis cache, and the
metering sink. Constructors do no I/O until first use.
"""

from __future__ import annotations

from functools import lru_cache

from acip_cache.metering import record_usage
from acip_core.clients import get_es_client, get_pg_pool, get_redis
from acip_embedding import get_embedding_client
from acip_search.retrieval import SearchService


async def _meter(tenant_id: str, **kwargs) -> None:
    await record_usage(await get_pg_pool(), tenant_id, **kwargs)


@lru_cache
def get_search_service() -> SearchService:
    redis = get_redis()
    return SearchService(
        es=get_es_client(),
        embedding_client=get_embedding_client(redis=redis),
        redis=redis,
        meter=_meter,
    )
