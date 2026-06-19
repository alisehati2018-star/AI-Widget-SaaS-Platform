"""Catalogue index mapping (M2: REQ-M2-007/008/011, blueprint Appendix A.2).

Explicit mapping (no dynamic-mapping surprises). `tenant_id` drives isolation +
ACORN filtering; `embedding` uses DiskBBQ (`bbq_disk`) so vectors live on disk
at ~95% less RAM. `dims` matches the chosen embedding model / MRL dimension.
"""

from __future__ import annotations


def catalogue_mapping(dims: int = 1024) -> dict:
    return {
        "dynamic": "strict",
        "properties": {
            "tenant_id": {"type": "keyword"},          # isolation + ACORN filter
            "product_id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "fa_text",
                "search_analyzer": "fa_search",
                "fields": {
                    "kw": {"type": "keyword"},
                    "suggest": {"type": "search_as_you_type", "analyzer": "fa_text"},
                },
            },
            "description": {
                "type": "text",
                "analyzer": "fa_text",
                "search_analyzer": "fa_search",
            },
            "brand": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "attributes": {"type": "flattened"},        # flexible facets
            "price": {"type": "scaled_float", "scaling_factor": 100},
            "in_stock": {"type": "boolean"},
            "popularity": {"type": "rank_feature"},      # boosts ranking
            "updated_at": {"type": "date"},
            "embedding": {
                "type": "dense_vector",
                "dims": dims,
                "index": True,
                "similarity": "cosine",
                "index_options": {"type": "bbq_disk"},   # DiskBBQ
            },
        },
    }
