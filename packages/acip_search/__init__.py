"""ACIP Persian hybrid search engine (M2 + M5).

- `analyzer` / `mapping`: the Persian analysis chain and catalogue mapping
  (blueprint Appendix A).
- `index_admin`: index template, creation, and zero-downtime alias-swap reindex.
- `query`: the single, central, tenant-scoped query-builder (the isolation
  invariant in code — REQ-M11-001).
- `retrieval` / `suggest` / `reranker` / `zero_result`: the search services.
"""

from .analyzer import ANALYSIS_SETTINGS
from .mapping import catalogue_mapping
from .query import build_hybrid_query

__all__ = ["ANALYSIS_SETTINGS", "catalogue_mapping", "build_hybrid_query"]
