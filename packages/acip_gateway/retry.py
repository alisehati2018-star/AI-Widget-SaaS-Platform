"""Retry-with-backoff for a single provider endpoint, before the gateway's
failover chain (`failover.py`/`registry.py`) moves on to the next endpoint.

Split out of both chain implementations because they duplicated the same
try/except loop — this is the shared "how many times, and on which errors,
do we retry the SAME endpoint before giving up on it" policy. Only errors
that a retry can plausibly fix (timeouts, connection resets, HTTP 429/5xx)
are retried; auth/validation errors (401/403/400/422 etc.) fail immediately
so the chain moves to the next endpoint right away — retrying a bad request
against the same broken key would just waste the whole backoff budget.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx
from acip_core.logging import get_logger

log = get_logger("gateway.retry")

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

T = TypeVar("T")


def is_retryable_error(exc: Exception) -> bool:
    """Transient network/rate-limit/server errors are retryable; anything
    that looks like a request/auth/billing problem is not (a different
    provider might have a valid key, but retrying the same one won't)."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _RETRYABLE_STATUS
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError)):
        return True
    return False


async def call_with_retry(
    fn: Callable[[], Awaitable[T]], *, max_retries: int = 0, backoff_ms: int = 250
) -> T:
    """Call `fn()`, retrying up to `max_retries` times (exponential backoff,
    capped at 5s) while `is_retryable_error` says the failure is transient.
    `max_retries=0` (the default for every endpoint until an admin opts in)
    means exactly one attempt — today's existing behavior, unchanged."""
    delay = backoff_ms / 1000.0
    attempt = 0
    while True:
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001 - reraise once retries are exhausted
            if attempt >= max_retries or not is_retryable_error(exc):
                raise
            attempt += 1
            log.warning("gateway.retry", attempt=attempt, max_retries=max_retries, error=str(exc))
            await asyncio.sleep(delay)
            delay = min(delay * 2, 5.0)
