"""ACIP AI Gateway — FastAPI bootstrap (Phase 0 foundation).

The gateway will own routing, caching (L1/L2/L3), cost metering, and provider
failover (M6, Phases 1-2). Phase 0 establishes only the service shell, health
probes, logging, and trace propagation — no routing/cache logic yet.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from acip_core.clients import redis_ready
from acip_core.config import get_settings
from acip_core.errors import not_implemented, unhandled_exception_handler
from acip_core.health import ReadinessRegistry
from acip_core.logging import configure_logging, get_logger
from acip_core.middleware import TraceIdMiddleware
from fastapi import APIRouter, FastAPI, Response

_registry = ReadinessRegistry()
_registry.register("redis", redis_ready)

router = APIRouter(tags=["gateway"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, object]:
    ok, deps = await _registry.evaluate()
    response.status_code = 200 if ok else 503
    return {"status": "ready" if ok else "degraded", "dependencies": deps}


@router.post("/route")
async def route():
    return not_implemented("Cost-aware routing ladder (M6)")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, "gateway")
    log = get_logger("gateway")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        log.info("gateway.startup", env=settings.env)
        yield
        log.info("gateway.shutdown")

    app = FastAPI(title="ACIP Gateway", version="0.0.0", lifespan=lifespan)
    app.add_middleware(TraceIdMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(router)

    return app


app = create_app()
