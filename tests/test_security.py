"""Phase 3 security/resilience primitives: rate limit, circuit breaker, bulkhead,
billing ledger guards (M11/M12)."""

from __future__ import annotations

import asyncio

from acip_billing.ledger import balance, plan_status, record_charge
from acip_core.ratelimit import RateLimiter
from acip_core.resilience import Bulkhead, CircuitBreaker, CircuitState


class FakeRedis:
    def __init__(self) -> None:
        self.kv: dict = {}

    async def incr(self, k):
        self.kv[k] = int(self.kv.get(k, 0)) + 1
        return self.kv[k]

    async def expire(self, k, ttl):
        return True


# --- rate limiting (REQ-M11-003) ---

async def test_rate_limiter_blocks_over_limit():
    rl = RateLimiter(FakeRedis(), default_per_min=3)
    results = [await rl.allow("t1") for _ in range(5)]
    assert results == [True, True, True, False, False]


async def test_rate_limiter_fails_open_without_redis():
    rl = RateLimiter(None)
    assert await rl.allow("t1") is True


async def test_rate_limiter_is_per_tenant():
    rl = RateLimiter(FakeRedis(), default_per_min=1)
    assert await rl.allow("t1") is True
    assert await rl.allow("t2") is True   # separate bucket
    assert await rl.allow("t1") is False


# --- circuit breaker (REQ-M12-002) ---

def test_circuit_breaker_trips_and_recovers():
    cb = CircuitBreaker(threshold=2, reset_seconds=0.0)
    assert cb.allow() is True
    cb.record_failure()
    cb.record_failure()
    assert cb.state is CircuitState.OPEN
    # reset_seconds=0 -> immediately half-open on next allow
    assert cb.allow() is True
    assert cb.state is CircuitState.HALF_OPEN
    cb.record_success()
    assert cb.state is CircuitState.CLOSED


# --- bulkhead (REQ-M12-002) ---

async def test_bulkhead_bounds_concurrency():
    bh = Bulkhead(limit=2)
    async with bh:
        async with bh:
            # Two slots taken; a third acquire would block — verify it times out.
            with_timeout = asyncio.wait_for(bh.__aenter__(), timeout=0.05)
            try:
                await with_timeout
                raised = False
            except TimeoutError:
                raised = True
    assert raised is True


# --- billing ledger guards (REQ-M11-009) ---

async def test_ledger_noop_without_pool():
    await record_charge(None, "t1", rung="local", cost=1.0)  # no raise
    assert await balance(None, "t1") == 0.0
    assert (await plan_status(None, "t1"))["within_plan"] is True
