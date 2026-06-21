"""ACIP billing (M11: REQ-M11-009).

Credit-based billing: an append-only credit ledger that records per-rung charges
(credit→cost multipliers from `acip_gateway.budget.RUNG_COST`), a balance query,
and plan-cap enforcement. Decouples pricing from any single provider's token
price (blueprint §8.1).
"""

from .ledger import balance, plan_status, record_charge, usage_summary
from .subscription import activate_plan, create_order, mark_order_paid

__all__ = [
    "record_charge",
    "balance",
    "plan_status",
    "usage_summary",
    "create_order",
    "activate_plan",
    "mark_order_paid",
]
