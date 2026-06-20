"""ACIP public API — FastAPI bootstrap (Phase 0 foundation).

Wires: structured logging, trace-id middleware, consistent error envelope,
health probes, and the versioned/admin route skeletons. No feature logic.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from acip_core.config import get_settings
from acip_core.errors import unhandled_exception_handler
from acip_core.logging import configure_logging, get_logger
from acip_core.middleware import TraceIdMiddleware
from fastapi import FastAPI

from .routers import admin, auth, health, v1


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name)
    log = get_logger("api")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        log.info("api.startup", env=settings.env)
        yield
        log.info("api.shutdown")

    app = FastAPI(
        title="ACIP API",
        version="0.0.0",
        description="AI Commerce Intelligence Platform — public API (Phase 0 foundation).",
        lifespan=lifespan,
    )
    app.add_middleware(TraceIdMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(v1.router)
    app.include_router(admin.router)

    return app


app = create_app()
