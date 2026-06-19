"""Liveness/readiness primitives shared by all services (REQ-M12-003).

`/healthz` = liveness (process is up). `/readyz` = readiness (declared
dependencies are reachable). Dependency checks are registered per service;
Phase 0 ships the framework, not deep checks.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

CheckFn = Callable[[], Awaitable[bool]]


@dataclass
class DependencyCheck:
    name: str
    check: CheckFn


class ReadinessRegistry:
    """Collects async dependency checks for a service's /readyz probe."""

    def __init__(self) -> None:
        self._checks: list[DependencyCheck] = []

    def register(self, name: str, check: CheckFn) -> None:
        self._checks.append(DependencyCheck(name=name, check=check))

    async def evaluate(self) -> tuple[bool, dict[str, str]]:
        results: dict[str, str] = {}
        ok = True
        for dep in self._checks:
            try:
                healthy = await dep.check()
            except Exception:  # noqa: BLE001 - readiness must never raise
                healthy = False
            results[dep.name] = "ok" if healthy else "unavailable"
            ok = ok and healthy
        return ok, results
