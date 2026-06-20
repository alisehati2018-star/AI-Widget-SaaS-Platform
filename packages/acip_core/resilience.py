"""Resilience patterns (M12: REQ-M12-002, blueprint §14.2).

Circuit breaker (trip a failing dependency open so it fails fast to the
fallback) and a bulkhead (bounded concurrency per dependency/tenant so one slow
provider or noisy tenant cannot starve the rest). Both are in-process, async,
and dependency-free.
"""

from __future__ import annotations

import asyncio
import time
from enum import StrEnum


class CircuitState(StrEnum):
    CLOSED = "closed"      # healthy, calls pass
    OPEN = "open"          # tripped, calls fail fast
    HALF_OPEN = "half_open"  # probing recovery


class CircuitBreaker:
    """Trips open after `threshold` consecutive failures; recovers after `reset`."""

    def __init__(self, *, threshold: int = 5, reset_seconds: float = 30.0) -> None:
        self._threshold = threshold
        self._reset = reset_seconds
        self._failures = 0
        self._opened_at = 0.0
        self.state = CircuitState.CLOSED

    def allow(self) -> bool:
        if self.state is CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self._reset:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        self._failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self.state = CircuitState.OPEN
            self._opened_at = time.monotonic()


class Bulkhead:
    """Bounds concurrent in-flight calls so one dependency cannot exhaust all."""

    def __init__(self, limit: int = 16) -> None:
        self._sem = asyncio.Semaphore(limit)

    async def __aenter__(self):
        await self._sem.acquire()
        return self

    async def __aexit__(self, *exc) -> None:
        self._sem.release()
