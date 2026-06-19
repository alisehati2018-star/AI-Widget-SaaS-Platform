"""Liveness/readiness probes for the public API (REQ-M12-003)."""

from __future__ import annotations

from acip_core.clients import es_ready, pg_ready, redis_ready
from acip_core.health import ReadinessRegistry
from fastapi import APIRouter, Response

router = APIRouter(tags=["health"])

_registry = ReadinessRegistry()
_registry.register("elasticsearch", es_ready)
_registry.register("postgres", pg_ready)
_registry.register("redis", redis_ready)


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness — the process is up."""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    """Readiness — declared dependencies are reachable."""
    ok, deps = await _registry.evaluate()
    response.status_code = 200 if ok else 503
    return {"status": "ready" if ok else "degraded", "dependencies": deps}
