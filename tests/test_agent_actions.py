"""Phase 4 — agent-action enablement framework (M7: REQ-M7-008, §7.5).

Money-moving tools are disabled by default; when enabled they require per-tenant
permission, explicit confirmation, and are idempotent. Read-only tools are
always safe.
"""

from __future__ import annotations

import pytest
from acip_assistant.tools import default_registry
from acip_core.config import get_settings


@pytest.fixture
def enabled_registry(monkeypatch):
    monkeypatch.setenv("AGENT_ACTIONS_ENABLED", "true")
    get_settings.cache_clear()
    reg = default_registry()
    yield reg
    get_settings.cache_clear()


async def test_money_tool_disabled_by_default():
    get_settings.cache_clear()
    reg = default_registry()
    out = await reg.invoke("create_payment_link", "t1", {"amount": 100})
    assert out["error"] == "tool_disabled"


async def test_money_tool_requires_confirmation(enabled_registry):
    out = await enabled_registry.invoke("create_payment_link", "t1", {"amount": 100})
    assert out["status"] == "confirmation_required"


async def test_money_tool_requires_permission(enabled_registry):
    out = await enabled_registry.invoke(
        "create_payment_link", "t1", {"amount": 100}, confirmed=True, permitted=False
    )
    assert out["error"] == "forbidden"


async def test_money_tool_executes_when_confirmed_and_permitted(enabled_registry):
    out = await enabled_registry.invoke(
        "create_payment_link", "t1", {"amount": 100}, confirmed=True, permitted=True
    )
    assert "error" not in out and "amount" in out


async def test_money_tool_is_idempotent(enabled_registry):
    a = await enabled_registry.invoke(
        "apply_discount", "t1", {"code": "X"}, confirmed=True, idempotency_key="k1"
    )
    b = await enabled_registry.invoke(
        "apply_discount", "t1", {"code": "X"}, confirmed=True, idempotency_key="k1"
    )
    assert a is b  # same result object; the action did not re-run


async def test_readonly_tool_always_enabled():
    get_settings.cache_clear()
    reg = default_registry()
    out = await reg.invoke("check_stock", "t1", {"product_id": "1"})
    assert "error" not in out
