"""Autocomplete / as-you-type suggestions (M5: REQ-M5-007).

Served from the lightweight `title.suggest` (`search_as_you_type`) field with a
tight latency budget (< 50 ms). Always tenant-scoped via the mandatory filter.
"""

from __future__ import annotations

from acip_core.config import get_settings


def build_suggest_query(tenant_id: str, prefix: str, size: int = 8) -> dict:
    if not tenant_id:
        raise ValueError("tenant_id is required (isolation invariant)")
    return {
        "size": size,
        "_source": ["product_id", "title"],
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": prefix,
                            "type": "bool_prefix",
                            "fields": [
                                "title.suggest",
                                "title.suggest._2gram",
                                "title.suggest._3gram",
                            ],
                        }
                    }
                ],
                "filter": [{"term": {"tenant_id": tenant_id}}],
            }
        },
    }


async def suggest(es, tenant_id: str, prefix: str, size: int = 8) -> list[dict]:
    alias = get_settings().catalogue_alias
    body = build_suggest_query(tenant_id, prefix, size)
    resp = await es.search(index=alias, body=body)
    return [
        {"product_id": h["_source"].get("product_id"), "title": h["_source"].get("title")}
        for h in resp["hits"]["hits"]
    ]
