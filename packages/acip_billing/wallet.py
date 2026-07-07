"""Wallet-aware budget guard (credit enforcement in the request path).

Before this existed the credit ledger was display-only: a tenant whose wallet
hit zero kept consuming paid frontier turns. `WalletBudgetGuard` extends the
Redis budget guard so the gateway's escalation ladder ALSO respects the
prepaid wallet: when the ledger balance (grants − spend) is exhausted, the
tenant is forced to the free/local rungs (cache → rule → search → local) —
shoppers still get grounded answers, the platform stops buying frontier
tokens for a customer who has not paid for them.

The balance is read from PostgreSQL at most once per TTL per tenant (cached in
Redis so all API workers share it), and everything fails open: an outage in
either store must never take the assistant down.
"""

from __future__ import annotations

from acip_core.logging import get_logger
from acip_gateway.budget import BudgetGuard, BudgetState

log = get_logger("billing.wallet")

_CACHE_KEY = "wallet:balance:{tenant_id}"


class WalletBudgetGuard(BudgetGuard):
    """BudgetGuard + prepaid-wallet enforcement from the credit ledger."""

    def __init__(self, redis, pool_getter, *, default_cap: float = 1000.0,
                 cache_ttl_s: int = 30) -> None:
        super().__init__(redis, default_cap=default_cap)
        self._pool_getter = pool_getter
        self._cache_ttl = cache_ttl_s

    async def _wallet_balance(self, tenant_id: str) -> float | None:
        """Ledger balance, Redis-cached. None = unknown (fail open)."""
        key = _CACHE_KEY.format(tenant_id=tenant_id)
        if self._redis is not None:
            try:
                cached = await self._redis.get(key)
                if cached is not None:
                    return float(cached)
            except Exception:  # noqa: BLE001
                pass
        try:
            pool = await self._pool_getter()
            async with pool.acquire() as conn:
                val = await conn.fetchval(
                    "SELECT coalesce(sum(delta), 0) FROM credit_ledger WHERE tenant_id = $1",
                    tenant_id,
                )
            balance = float(val or 0.0)
        except Exception as exc:  # noqa: BLE001 - PG down: don't punish the tenant
            log.warning("wallet.balance_failed", error=str(exc))
            return None
        if self._redis is not None:
            try:
                await self._redis.set(key, str(balance), ex=self._cache_ttl)
            except Exception:  # noqa: BLE001
                pass
        return balance

    async def state(self, tenant_id: str) -> BudgetState:
        base = await super().state(tenant_id)
        if base.local_only:
            return base
        balance = await self._wallet_balance(tenant_id)
        if balance is not None and balance <= 0:
            return BudgetState(spent=base.spent, cap=base.cap, local_only=True)
        return base

    async def invalidate_wallet(self, tenant_id: str) -> None:
        """Drop the cached balance (call after grants so credit applies fast)."""
        if self._redis is None:
            return
        try:
            await self._redis.delete(_CACHE_KEY.format(tenant_id=tenant_id))
        except Exception:  # noqa: BLE001
            pass
