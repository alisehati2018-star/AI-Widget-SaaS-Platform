"""Order index mapping (M3 order-sync extension, blueprint Appendix A.2 sibling).

Orders are indexed alongside products so a tenant's storefront orders are
searchable/aggregatable in Elasticsearch (e.g. admin sales lookups, order-status
analytics) with the same tenant-isolation guarantee as the catalogue: every
query MUST filter on `tenant_id`. No dense vector here — orders are a
structured/BM25-lite surface, not a semantic-search target.
"""

from __future__ import annotations


def order_mapping() -> dict:
    return {
        "dynamic": "strict",
        "properties": {
            "tenant_id": {"type": "keyword"},          # isolation filter
            "order_id": {"type": "keyword"},
            "status": {"type": "keyword"},
            "customer_email": {"type": "keyword"},
            "customer_name": {
                "type": "text",
                "analyzer": "fa_text",
                "search_analyzer": "fa_search",
                "fields": {"kw": {"type": "keyword"}},
            },
            "items": {
                "type": "nested",
                "properties": {
                    "product_id": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "fa_text"},
                    "quantity": {"type": "integer"},
                    "price": {"type": "scaled_float", "scaling_factor": 100},
                },
            },
            "total": {"type": "scaled_float", "scaling_factor": 100},
            "currency": {"type": "keyword"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"},
        },
    }
