"""Elasticsearch client factory + readiness probe (REQ-M1-001).

Phase 0 only establishes connectivity and a health check. Index templates,
the Persian analyzer, and mappings are Phase 1 (M2) and are NOT created here.
"""

from __future__ import annotations

from elasticsearch import AsyncElasticsearch

from ..config import get_settings

_client: AsyncElasticsearch | None = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        s = get_settings()
        _client = AsyncElasticsearch(
            hosts=[s.es_host],
            basic_auth=(s.es_username, s.es_password) if s.es_password else None,
            verify_certs=s.es_verify_certs,
            request_timeout=5,
        )
    return _client


async def es_ready() -> bool:
    try:
        return bool(await get_es_client().ping())
    except Exception:  # noqa: BLE001
        return False
