"""ES-backed results provider for the golden-set evaluation (M5 ↔ M12-009).

Replaces the Phase-0 `EmptyProvider`: runs the real tenant-scoped hybrid search
for each golden query and returns the ranked `product_id`s for scoring. Used by
`run_eval.py` when an Elasticsearch cluster is reachable.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from acip_core.clients import get_es_client, get_redis
from acip_embedding import get_embedding_client
from acip_search.retrieval import SearchService


class ESResultsProvider:
    """Synchronous `search(query)->[product_id]` adapter over the async service."""

    def __init__(self, tenant_id: str, size: int = 10) -> None:
        redis = get_redis()
        self._tenant_id = tenant_id
        self._size = size
        self._svc = SearchService(
            es=get_es_client(),
            embedding_client=get_embedding_client(redis=redis),
            redis=redis,
        )

    def search(self, query: str) -> Sequence[str]:
        result = asyncio.run(self._svc.search(self._tenant_id, query, size=self._size))
        return [r.get("product_id") for r in result["results"] if r.get("product_id")]
