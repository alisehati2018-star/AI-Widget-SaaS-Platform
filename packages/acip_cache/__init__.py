"""AI gateway cost-control foundation (M6, Phase-1 subset).

Phase 1 lands the load-bearing primitives: the L1 exact cache, the L2 semantic
cache scaffold, per-tenant data-version invalidation, and the usage/metering
record. The full routing/compression/failover ceiling is Phase 2.
"""

from .data_version import bump_data_version, current_data_version
from .l1 import L1ExactCache
from .l2 import L2SemanticCache
from .metering import record_usage

__all__ = [
    "L1ExactCache",
    "L2SemanticCache",
    "record_usage",
    "bump_data_version",
    "current_data_version",
]
