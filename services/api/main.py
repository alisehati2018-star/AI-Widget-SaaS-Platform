"""ACIP public API — FastAPI bootstrap (Phase 0 foundation).

Wires: structured logging, trace-id middleware, consistent error envelope,
health probes, and the versioned/admin route skeletons. No feature logic.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from acip_core.config import get_settings
from acip_core.errors import unhandled_exception_handler
from acip_core.logging import configure_logging, get_logger
from acip_core.middleware import (
    CsrfMiddleware,
    SecurityHeadersMiddleware,
    TraceIdMiddleware,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import admin, auth, billing, health, public, tenant, v1


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
        title="Vitrin API",
        version="0.1.0",
        description="Vitrin — AI Commerce Intelligence Platform (public + auth + admin API).",
        lifespan=lifespan,
    )
    # Middleware (added inner→outer; CORS added last = outermost so it also
    # decorates error/preflight responses).
    app.add_middleware(TraceIdMiddleware)
    if settings.csrf_enabled:
        app.add_middleware(CsrfMiddleware)
    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware, hsts=settings.hsts_enabled)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health.router)
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(tenant.router)
    app.include_router(billing.router)
    app.include_router(v1.router)
    app.include_router(admin.router)

    return app


app = create_app()
