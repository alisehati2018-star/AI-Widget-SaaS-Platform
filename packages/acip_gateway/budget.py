"""Budget-aware routing + kill switches (M6: REQ-M6-008/013).

Tracks per-tenant spend (Redis), enforces soft budgets and a hard cap, and
exposes per-tenant + global kill switches that force the local-only path. As a
tenant nears its ceiling the router biases to cheaper rungs; at the hard cap it
stops escalating to paid models entirely. Best-effort: a budget-store failure
must never break the request path (it fails open to local-only, the safe rung).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Rung(StrEnum):
    """Cost rungs of the escalation ladder, cheapest first (blueprint §8.1)."""

    CACHE = "cache"        # 0
    RULE = "rule"          # 0
    SEARCH = "search"      # very low (fixed)
    LOCAL = "local"        # low (owned GPU)
    FRONTIER = "frontier"  # high (metered)


# Relative cost multipliers used for metering/attribution (§8.1).
RUNG_COST: dict[Rung, float] = {
    Rung.CACHE: 0.0,
    Rung.RULE: 0.0,
    Rung.SEARCH: 0.01,
    Rung.LOCAL: 0.1,
    Rung.FRONTIER: 1.0,
}


@dataclass
class BudgetState:
    spent: float
    cap: float
    local_only: bool  # kill switch tripped OR hard cap reached

    @property
    def near_ceiling(self) -> bool:
        return self.cap > 0 and self.spent >= 0.8 * self.cap


class BudgetGuard:
    """Per-tenant budget accounting + kill switches, backed by Redis."""

    def __init__(self, redis, default_cap: float = 1000.0) -> None:
        self._redis = redis
        self._default_cap = default_cap

    def _spend_key(self, tenant_id: str) -> str:
        return f"budget:spent:{tenant_id}"

    def _cap_key(self, tenant_id: str) -> str:
        return f"budget:cap:{tenant_id}"

    def _kill_key(self, tenant_id: str) -> str:
        return f"killswitch:{tenant_id}"

    async def _global_kill(self) -> bool:
        if self._redis is None:
            return False
        try:
            return bool(await self._redis.get("killswitch:__global__"))
        except Exception:  # noqa: BLE001
            return False

    async def state(self, tenant_id: str) -> BudgetState:
        if self._redis is None:
            return BudgetState(spent=0.0, cap=self._default_cap, local_only=False)
        try:
            spent = float(await self._redis.get(self._spend_key(tenant_id)) or 0.0)
            cap = float(await self._redis.get(self._cap_key(tenant_id)) or self._default_cap)
            killed = bool(await self._redis.get(self._kill_key(tenant_id)))
            killed = killed or await self._global_kill()
        except Exception:  # noqa: BLE001 - fail safe to local-only
            return BudgetState(spent=0.0, cap=self._default_cap, local_only=True)
        hard_capped = cap > 0 and spent >= cap
        return BudgetState(spent=spent, cap=cap, local_only=killed or hard_capped)

    async def charge(self, tenant_id: str, cost: float) -> None:
        if self._redis is None or cost <= 0:
            return
        try:
            await self._redis.incrbyfloat(self._spend_key(tenant_id), cost)
        except Exception:  # noqa: BLE001
            pass

    async def set_kill_switch(self, tenant_id: str, on: bool) -> None:
        if self._redis is None:
            return
        key = self._kill_key(tenant_id)
        try:
            await self._redis.set(key, "1") if on else await self._redis.delete(key)
        except Exception:  # noqa: BLE001
            pass
