"""Token-based pricing engine (FinOps: cost → margin → credits).

Turns a model call's real token usage into two numbers that are recorded side
by side on every usage event:

* ``provider_cost`` — what the call actually cost the platform (USD), from the
  model's per-1M-token price sheet (``ai_models``), and
* ``credits`` — what the tenant is charged: provider cost, marked up by the
  configured platform margin, converted at the configured credit value.

Rungs that never touch a paid model keep deterministic prices: cache/rule are
free, search is a flat configured credit price, and any rung whose model has
no price sheet falls back to the legacy ``RUNG_COST`` multiplier — so an
unconfigured deployment behaves exactly as before this engine existed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Provider cost of one model, USD per 1M tokens (industry-standard unit)."""

    provider: str
    model: str
    input_usd_per_1m: float = 0.0
    output_usd_per_1m: float = 0.0


@dataclass(frozen=True)
class PricingConfig:
    """Platform-wide pricing knobs (single `pricing_settings` row)."""

    usd_per_credit: float = 0.0001    # 1 credit = $0.0001 → 10 000 credits = $1
    margin_percent: float = 30.0      # platform markup over provider cost
    search_credits: float = 0.01      # flat price of a search call
    local_input_usd_per_1m: float = 0.0   # honest cost attribution for owned GPU
    local_output_usd_per_1m: float = 0.0


# Legacy flat multipliers — the fallback when a model has no price sheet.
FALLBACK_RUNG_CREDITS: dict[str, float] = {
    "cache": 0.0,
    "rule": 0.0,
    "search": 0.01,
    "local": 0.1,
    "frontier": 1.0,
}


def provider_cost_usd(price: ModelPrice, tokens_in: int, tokens_out: int) -> float:
    """Actual COGS of one call from the provider's per-1M-token prices."""
    return (
        max(tokens_in, 0) * price.input_usd_per_1m
        + max(tokens_out, 0) * price.output_usd_per_1m
    ) / 1_000_000


def credits_from_cost(cost_usd: float, cfg: PricingConfig) -> float:
    """Convert a USD cost into tenant credits, marked up by the margin."""
    if cost_usd <= 0 or cfg.usd_per_credit <= 0:
        return 0.0
    return cost_usd * (1 + cfg.margin_percent / 100.0) / cfg.usd_per_credit


def charge_for_turn(
    rung: str,
    *,
    cfg: PricingConfig,
    price: ModelPrice | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> tuple[float, float]:
    """(credits_charged, provider_cost_usd) for one turn.

    cache/rule → free. search → flat configured credits, zero COGS.
    local → tokens priced at the local attribution rates (falls back to the
    legacy flat multiplier when attribution is unset, so local turns are never
    silently free). frontier → tokens priced from the model's sheet; without a
    sheet the legacy flat multiplier applies.
    """
    if rung in ("cache", "rule"):
        return 0.0, 0.0
    if rung == "search":
        return float(cfg.search_credits), 0.0

    if rung == "local":
        local_price = ModelPrice(
            provider="local",
            model="",
            input_usd_per_1m=cfg.local_input_usd_per_1m,
            output_usd_per_1m=cfg.local_output_usd_per_1m,
        )
        cost = provider_cost_usd(local_price, tokens_in, tokens_out)
        if cost <= 0:
            return FALLBACK_RUNG_CREDITS["local"], 0.0
        return credits_from_cost(cost, cfg), cost

    # frontier (or any future paid rung)
    if price is not None and (price.input_usd_per_1m > 0 or price.output_usd_per_1m > 0):
        cost = provider_cost_usd(price, tokens_in, tokens_out)
        return credits_from_cost(cost, cfg), cost
    return FALLBACK_RUNG_CREDITS.get(rung, FALLBACK_RUNG_CREDITS["frontier"]), 0.0


def parse_pricing_row(row) -> PricingConfig:
    """Build a PricingConfig from the `pricing_settings` row (None → defaults)."""
    if row is None:
        return PricingConfig()
    return PricingConfig(
        usd_per_credit=float(row["usd_per_credit"]),
        margin_percent=float(row["margin_percent"]),
        search_credits=float(row["search_credits"]),
        local_input_usd_per_1m=float(row["local_input_usd_per_1m"]),
        local_output_usd_per_1m=float(row["local_output_usd_per_1m"]),
    )
