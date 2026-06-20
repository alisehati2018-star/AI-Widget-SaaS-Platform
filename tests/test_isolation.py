"""Tenant-isolation suite — the release blocker (M11: REQ-M11-005, §9.3).

Asserts that no code path can observe another tenant's data: the central query
builder refuses to build without a tenant filter and always stamps it on every
leg; analytics queries are tenant-scoped; long-term memory recall rejects
cross-tenant docs; and least-privilege key scopes are enforced. Any failure here
must fail the build (CI release gate).
"""

from __future__ import annotations

import pytest
from acip_analytics.aggregations import funnel_query, most_wanted_query, zero_result_query
from acip_assistant.memory import LongTermMemory
from acip_core.security import ApiKeyPrincipal
from acip_search.query import MissingTenantError, build_hybrid_query, query_has_tenant_filter

from services.api.deps import KeyScope, principal_allowed


def test_query_builder_requires_tenant():
    with pytest.raises(MissingTenantError):
        build_hybrid_query("", text="گوشی")


def test_query_builder_filters_every_leg():
    body = build_hybrid_query("t1", text="گوشی", query_vector=[0.1] * 8)
    assert query_has_tenant_filter(body, "t1")
    # A different tenant's filter must NOT satisfy the check.
    assert not query_has_tenant_filter(body, "t2")


def test_lexical_only_path_still_tenant_filtered():
    body = build_hybrid_query("t1", text="گوشی", query_vector=None)  # embeddings down
    assert query_has_tenant_filter(body, "t1")


def test_all_analytics_queries_tenant_scoped():
    for q in (most_wanted_query("t1"), zero_result_query("t1"), funnel_query("t1")):
        assert {"term": {"tenant_id": "t1"}} in q["query"]["bool"]["filter"]


class _FakeES:
    def __init__(self, stored_tenant: str) -> None:
        self._stored_tenant = stored_tenant

    async def get(self, index, id):  # noqa: A002 - mirrors ES client kwarg
        return {"_source": {"tenant_id": self._stored_tenant, "summary": "secret prefs"}}


async def test_longterm_memory_rejects_cross_tenant():
    mem = LongTermMemory(_FakeES(stored_tenant="t2"))
    # Asking as t1 must never return t2's stored memory.
    assert await mem.recall("t1", "shopper-1") is None
    # Same tenant is fine.
    mem_ok = LongTermMemory(_FakeES(stored_tenant="t1"))
    assert await mem_ok.recall("t1", "shopper-1") == "secret prefs"


def test_key_scope_least_privilege():
    widget = ApiKeyPrincipal(tenant_id="t1", scope=KeyScope.WIDGET, raw_key="k", verified=True)
    sync = ApiKeyPrincipal(tenant_id="t1", scope=KeyScope.SYNC, raw_key="k", verified=True)
    no_tenant = ApiKeyPrincipal(tenant_id=None, scope=None, raw_key=None, verified=False)
    assert principal_allowed(widget, KeyScope.WIDGET) is True
    assert principal_allowed(widget, KeyScope.SYNC) is False        # widget can't sync
    assert principal_allowed(sync, KeyScope.SYNC) is True
    assert principal_allowed(no_tenant, KeyScope.WIDGET) is False   # no tenant -> denied
