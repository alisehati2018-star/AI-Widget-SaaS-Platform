"""Agent-action tool interface + audit log (M7: REQ-M7-008, blueprint §7.5).

The capability is architected now (the tool interface and audit log exist), but
money-moving tools stay DISABLED until after GA (Phase 4), behind strict input
validation, per-tenant permissions, idempotency, and explicit confirmation.
Phase 2 ships the registry, the read-only/no-op tools, and the audit trail.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

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
    """Holds the declared tools and an in-process audit trail."""

    tools: dict[str, ToolSpec] = field(default_factory=dict)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def register(self, spec: ToolSpec) -> None:
        # Money-moving tools are force-disabled until Phase 4 enablement.
        if spec.money_moving:
            spec.enabled = False
            spec.requires_confirmation = True
        self.tools[spec.name] = spec

    async def invoke(self, name: str, tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
        spec = self.tools.get(name)
        if spec is None:
            return {"error": "unknown_tool"}
        self.audit.append({"tool": name, "tenant_id": tenant_id, "args": args})
        log.info("tool.invoked", tool=name, tenant_id=tenant_id)
        if not spec.enabled:
            return {"error": "tool_disabled", "reason": "money-moving tools are disabled until GA+"}
        return await spec.handler(tenant_id, args)


async def _check_stock(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:
    """Read-only stock check (safe, enabled). Wired to live data in Phase 4."""
    return {"product_id": args.get("product_id"), "in_stock": None, "note": "wired in Phase 4"}


def default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ToolSpec("check_stock", "Check whether a product is in stock", _check_stock))
    # Money-moving tools: declared now, disabled until Phase 4.
    reg.register(
        ToolSpec("create_payment_link", "Create a payment link", _disabled, money_moving=True)
    )
    reg.register(
        ToolSpec("apply_discount", "Apply a permitted discount", _disabled, money_moving=True)
    )
    return reg


async def _disabled(tenant_id: str, args: dict[str, Any]) -> dict[str, Any]:  # pragma: no cover
    return {"error": "tool_disabled"}
