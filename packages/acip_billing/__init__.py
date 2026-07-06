"""ACIP billing (M11: REQ-M11-009).

Credit-based billing: an append-only credit ledger that records per-rung charges
(credit→cost multipliers from `acip_gateway.budget.RUNG_COST`), a balance query,
and plan-cap enforcement. Decouples pricing from any single provider's token
price (blueprint §8.1).
"""

from .ledger import balance, plan_status, record_charge, usage_summary
from .pricing import (
    FALLBACK_RUNG_CREDITS,
    ModelPrice,
    PricingConfig,
    charge_for_turn,
    credits_from_cost,
    parse_pricing_row,
    provider_cost_usd,
)
from .subscription import (
    activate_plan,
    create_order,
    create_topup_order,
    list_past_due,
    mark_order_paid,
    process_renewals,
    proration_preview,
    set_cancel,
)

__all__ = [
    "ModelPrice",
    "PricingConfig",
    "FALLBACK_RUNG_CREDITS",
    "charge_for_turn",
    "credits_from_cost",
    "provider_cost_usd",
    "parse_pricing_row",
    "record_charge",
    "balance",
    "plan_status",
    "usage_summary",
    "create_order",
    "create_topup_order",
    "activate_plan",
    "mark_order_paid",
    "proration_preview",
    "set_cancel",
    "process_renewals",
    "list_past_due",
]
