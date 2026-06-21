"""Liveness/readiness probes for the public API (REQ-M12-003)."""

from __future__ import annotations

from acip_core.clients import es_ready, pg_ready, redis_ready
from acip_core.config import get_settings
from acip_core.health import ReadinessRegistry
from acip_core.obs import metrics
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

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
    metrics.gauge("vitrin_readyz_ok", 1.0 if ok else 0.0)
    for name, state in deps.items():
        metrics.gauge("vitrin_dependency_up", 1.0 if state == "ok" else 0.0, {"dep": name})
    response.status_code = 200 if ok else 503
    return {"status": "ready" if ok else "degraded", "dependencies": deps}


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Prometheus scrape endpoint (text exposition format)."""
    if not get_settings().metrics_enabled:
        return PlainTextResponse("metrics disabled\n", status_code=404)
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")
