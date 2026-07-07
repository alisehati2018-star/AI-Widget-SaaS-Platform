"""Unit tests for the token-based pricing engine (FinOps completion)."""

from __future__ import annotations

from acip_billing.pricing import (
    FALLBACK_RUNG_CREDITS,
    ModelPrice,
    PricingConfig,
    charge_for_turn,
    credits_from_cost,
    parse_pricing_row,
    provider_cost_usd,
)


def test_provider_cost_usd_scales_by_1m_tokens():
    price = ModelPrice(
        provider="openai", model="gpt-x", input_usd_per_1m=2.0, output_usd_per_1m=8.0
    )
    # 500k input + 250k output tokens.
    cost = provider_cost_usd(price, 500_000, 250_000)
    assert cost == 500_000 * 2.0 / 1_000_000 + 250_000 * 8.0 / 1_000_000


def test_credits_from_cost_applies_margin_and_credit_value():
    cfg = PricingConfig(usd_per_credit=0.0001, margin_percent=30.0)
    # $0.01 cost, 30% margin -> $0.013, at $0.0001/credit -> 130 credits.
    assert round(credits_from_cost(0.01, cfg), 6) == 130.0


def test_credits_from_cost_zero_when_free():
    cfg = PricingConfig()
    assert credits_from_cost(0.0, cfg) == 0.0
    assert credits_from_cost(-1.0, cfg) == 0.0


def test_charge_for_turn_cache_and_rule_are_free():
    cfg = PricingConfig()
    assert charge_for_turn("cache", cfg=cfg) == (0.0, 0.0)
    assert charge_for_turn("rule", cfg=cfg) == (0.0, 0.0)


def test_charge_for_turn_search_is_flat_and_costless():
    cfg = PricingConfig(search_credits=0.02)
    credits, cost = charge_for_turn("search", cfg=cfg)
    assert credits == 0.02 and cost == 0.0


def test_charge_for_turn_frontier_with_price_sheet():
    cfg = PricingConfig(usd_per_credit=0.0001, margin_percent=0.0)
    price = ModelPrice(
        provider="openai", model="gpt-x", input_usd_per_1m=1.0, output_usd_per_1m=1.0
    )
    credits, cost = charge_for_turn(
        "frontier", cfg=cfg, price=price, tokens_in=1_000_000, tokens_out=0
    )
    assert cost == 1.0
    assert round(credits, 2) == 10000.0  # $1 / $0.0001 per credit, no margin


def test_charge_for_turn_frontier_without_price_sheet_falls_back():
    cfg = PricingConfig()
    credits, cost = charge_for_turn("frontier", cfg=cfg, price=None, tokens_in=100, tokens_out=100)
    assert credits == FALLBACK_RUNG_CREDITS["frontier"]
    assert cost == 0.0


def test_charge_for_turn_local_uses_attribution_when_set():
    cfg = PricingConfig(
        usd_per_credit=0.0001, margin_percent=0.0,
        local_input_usd_per_1m=0.1, local_output_usd_per_1m=0.1,
    )
    credits, cost = charge_for_turn("local", cfg=cfg, tokens_in=1_000_000, tokens_out=0)
    assert cost == 0.1
    assert round(credits, 2) == 1000.0


def test_charge_for_turn_local_falls_back_without_attribution():
    cfg = PricingConfig()  # local attribution left at 0
    credits, cost = charge_for_turn("local", cfg=cfg, tokens_in=1000, tokens_out=1000)
    assert credits == FALLBACK_RUNG_CREDITS["local"]
    assert cost == 0.0


def test_parse_pricing_row_defaults_when_none():
    cfg = parse_pricing_row(None)
    assert cfg == PricingConfig()


def test_parse_pricing_row_reads_mapping():
    row = {
        "usd_per_credit": "0.0005",
        "margin_percent": "25",
        "search_credits": "0.02",
        "local_input_usd_per_1m": "0.05",
        "local_output_usd_per_1m": "0.1",
    }
    cfg = parse_pricing_row(row)
    assert cfg.usd_per_credit == 0.0005
    assert cfg.margin_percent == 25.0
    assert cfg.search_credits == 0.02
