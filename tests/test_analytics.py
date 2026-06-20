"""Unit tests for the analytics/insight engine (M10) and admin auth (M9/M11)."""

from __future__ import annotations

from acip_analytics.aggregations import (
    funnel_query,
    most_wanted_query,
    zero_result_query,
)
from acip_analytics.leads import detect_lead

# --- tenant-scoping invariant on every analytics query (REQ-M10-006) ---

def _has_tenant_filter(body: dict, tenant: str) -> bool:
    filters = body["query"]["bool"]["filter"]
    return {"term": {"tenant_id": tenant}} in filters


def test_all_aggregation_queries_are_tenant_scoped():
    assert _has_tenant_filter(most_wanted_query("t1"), "t1")
    assert _has_tenant_filter(zero_result_query("t1"), "t1")
    assert _has_tenant_filter(funnel_query("t1"), "t1")


def test_zero_result_query_filters_empty_results():
    body = zero_result_query("t1")
    assert {"term": {"result_count": 0}} in body["query"]["bool"]["filter"]


# --- lead detection (REQ-M10-004) ---

def test_detect_lead_email_and_intent():
    s = detect_lead("می‌خوام بخرم، ایمیلم ali@example.com است")
    assert s.email == "ali@example.com"
    assert s.has_intent is True
    assert s.is_lead is True


def test_detect_lead_phone():
    s = detect_lead("شماره من 0912 345 6789 هست")
    assert s.phone is not None
    assert s.is_lead is True


def test_detect_no_lead():
    s = detect_lead("سلام، فقط یک سوال داشتم")
    assert s.is_lead is False


# --- admin operator auth is separated from tenant keys (REQ-M11-004) ---

def test_admin_authorized_requires_configured_token(monkeypatch):
    from acip_core.config import get_settings

    from services.api.routers import admin

    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_TOKEN", "secret-op-token")
    get_settings.cache_clear()
    assert admin._authorized("secret-op-token") is True
    assert admin._authorized("wrong") is False
    assert admin._authorized(None) is False
    get_settings.cache_clear()


# --- insight 'why' engine + NL analyst (M10-002/003) ---

def test_funnel_dropoff_finds_biggest():
    from acip_analytics.insight import _funnel_dropoff
    drops = _funnel_dropoff({"search": 100, "click": 40, "cart": 30, "purchase": 10})
    assert drops[0]["from"] == "search" and drops[0]["to"] == "click"
    assert drops[0]["drop_rate"] == 0.6


async def test_nl_analyst_routes_and_grounds():
    from acip_analytics.nl_analyst import analyze, route_metric

    class _ES:
        async def search(self, index, body):
            return {"aggregations": {"terms": {"buckets": [{"key": "گوشی", "doc_count": 5}]}}}

    routed = await route_metric("پرفروش‌ترین محصولات؟", _ES(), "t1")
    assert routed["kind"] == "most_wanted"
    # No providers -> deterministic, grounded template narration (never invents).
    out = await analyze("پرفروش‌ترین محصولات؟", _ES(), "t1")
    assert out["narrated_by"] == "template" and "گوشی" in out["answer"]
