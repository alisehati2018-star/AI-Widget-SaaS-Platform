"""ACIP Analytics & Insight Engine (M10, first cut).

Turns conversations, queries, and behaviour into decisions: most-wanted and
out-of-stock-but-wanted products, funnel drop-off, in-conversation lead capture
with intent detection, and AI attribution — all tenant-scoped and async/batch,
isolated from the shopper path (blueprint §11).
"""

from .aggregations import funnel, most_wanted, zero_result_terms
from .attribution import attribution_summary, four_dimension_summary
from .insight import why_summary
from .leads import LeadSignal, capture_lead, detect_lead
from .nl_analyst import analyze, route_metric

__all__ = [
    "most_wanted",
    "zero_result_terms",
    "funnel",
    "detect_lead",
    "capture_lead",
    "LeadSignal",
    "attribution_summary",
    "four_dimension_summary",
    "why_summary",
    "analyze",
    "route_metric",
]
