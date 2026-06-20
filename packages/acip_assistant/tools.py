"""Agent-action tool interface + audit log (M7: REQ-M7-008; enabled in Phase 4).

The capability is architected from Phase 2 (interface + audit). Phase 4 adds the
**enablement framework** for money-moving tools — they remain DISABLED by
default and, when turned on (`AGENT_ACTIONS_ENABLED`), are gated by: per-tenant
permission, an explicit confirmation step, and an idempotency key (blueprint
§7.5). Read-only tools (e.g. stock check) are always safe and enabled.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("assistant.tools")

ToolFn = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


@dataclass
class ToolSpec:
    name: str
    description: str
    handler: ToolFn
    money_moving: bool = False
    enabled: bool = True
    requires_confirmation: bool = False


@dataclass
class ToolRegistry:
    """Declared tools, an audit trail, and an idempotency cache."""

    tools: dict[str, ToolSpec] = field(default_factory=dict)
    audit: list[dict[str, Any]] = field(default_factory=list)
    _seen: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        if spec.money_moving:
            # Money tools require confirmation, and are only enabled when the
            # operator has globally turned agent actions on (Phase 4 gate).
            spec.requires_confirmation = True
            spec.enabled = get_settings().agent_actions_enabled
        self.tools[spec.name] = spec

    async def invoke(
        self,
        name: str,
        tenant_id: str,
        args: dict[str, Any],
        *,
        confirmed: bool = False,
        permitted: bool = True,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        spec = self.tools.get(name)
        if spec is None:
            return {"error": "unknown_tool"}
        self.audit.append({"tool": name, "tenant_id": tenant_id, "args": args,
                           "confirmed": confirmed})
        log.info("tool.invoked", tool=name, tenant_id=tenant_id, confirmed=confirmed)
        if not spec.enabled:
            return {"error": "tool_disabled", "reason": "agent actions are off (enable in Phase 4)"}
        if not permitted:
            return {"error": "forbidden", "reason": "tenant lacks permission for this tool"}
        if spec.requires_confirmation and not confirmed:
            return {"status": "confirmation_required", "tool": name,
                    "message": "explicit confirmation is required before executing this action"}
        # Idempotency: a repeated key returns the original result, never re-runs.
        if idempotency_key and idempotency_key in self._seen:
            return self._seen[idempotency_key]
        result = await spec.handler(tenant_id, args)
        if idempotency_key:
            self._seen[idempotency_key] = result
        return result


async def _check_stock(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Read-only stock check (safe, always enabled). Live data wired in Phase 4."""
    return {"product_id": args.get("product_id"), "in_stock": None, "note": "wired to live data"}


async def _order_lookup(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Read-only order lookup (safe). Live data wired in Phase 4."""
    return {"order_id": args.get("order_id"), "status": None, "note": "wired to live data"}


async def _payment_link(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Money-moving: create a payment link (confirmation + permission gated)."""
    return {"payment_link": None, "amount": args.get("amount"), "note": "executed via PSP"}


async def _apply_discount(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Money-moving: apply a permitted discount (confirmation + permission gated)."""
    return {"applied": True, "code": args.get("code"), "note": "executed in Phase 4"}


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("check_stock", "Check whether a product is in stock", _check_stock))
    reg.register(ToolSpec("order_lookup", "Look up an order status", _order_lookup))
    reg.register(ToolSpec("create_payment_link", "Create a payment link", _payment_link,
                          money_moving=True))
    reg.register(ToolSpec("apply_discount", "Apply a permitted discount", _apply_discount,
                          money_moving=True))
    return reg
