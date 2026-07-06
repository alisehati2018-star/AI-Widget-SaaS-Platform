"""Unit tests for WalletBudgetGuard (prepaid-wallet enforcement in the ladder)."""

from __future__ import annotations

from acip_billing.wallet import WalletBudgetGuard


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict = {}

    async def get(self, k):
        return self.kv.get(k)

    async def set(self, k, v, ex=None):
        self.kv[k] = v

    async def delete(self, k):
        self.kv.pop(k, None)

    async def incr(self, k):
        self.kv[k] = int(self.kv.get(k, 0)) + 1
        return self.kv[k]

    async def incrbyfloat(self, k, amt):
        self.kv[k] = float(self.kv.get(k, 0.0)) + amt
        return self.kv[k]


class FakeConn:
    def __init__(self, balance: float) -> None:
        self._balance = balance

    async def fetchval(self, *_a, **_k):
        return self._balance


class FakeAcquire:
    def __init__(self, conn: FakeConn) -> None:
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *exc):
        return False


class FakePool:
    def __init__(self, balance: float) -> None:
        self._balance = balance

    def acquire(self):
        return FakeAcquire(FakeConn(self._balance))


async def test_wallet_positive_balance_does_not_force_local():
    redis = FakeRedis()

    async def pool_getter():
        return FakePool(500.0)

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0)
    state = await guard.state("t1")
    assert state.local_only is False


async def test_wallet_zero_balance_forces_local_only():
    redis = FakeRedis()

    async def pool_getter():
        return FakePool(0.0)

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0)
    state = await guard.state("t1")
    assert state.local_only is True


async def test_wallet_negative_balance_forces_local_only():
    redis = FakeRedis()

    async def pool_getter():
        return FakePool(-5.0)

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0)
    assert (await guard.state("t1")).local_only is True


async def test_wallet_balance_is_cached_in_redis():
    redis = FakeRedis()
    calls = {"n": 0}

    async def pool_getter():
        calls["n"] += 1
        return FakePool(100.0)

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0, cache_ttl_s=60)
    await guard.state("t1")
    await guard.state("t1")
    assert calls["n"] == 1  # second call served from the Redis cache


async def test_wallet_invalidate_forces_reload():
    redis = FakeRedis()
    calls = {"n": 0}

    async def pool_getter():
        calls["n"] += 1
        return FakePool(100.0)

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0, cache_ttl_s=60)
    await guard.state("t1")
    await guard.invalidate_wallet("t1")
    await guard.state("t1")
    assert calls["n"] == 2


async def test_wallet_pg_failure_fails_open():
    redis = FakeRedis()

    async def pool_getter():
        raise RuntimeError("pg down")

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0)
    state = await guard.state("t1")
    assert state.local_only is False  # unknown balance never punishes the tenant


async def test_wallet_kill_switch_still_applies():
    redis = FakeRedis()

    async def pool_getter():
        return FakePool(500.0)  # healthy wallet, but kill switch wins

    guard = WalletBudgetGuard(redis, pool_getter, default_cap=1000.0)
    await guard.set_kill_switch("t1", True)
    assert (await guard.state("t1")).local_only is True
