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
    MetricsMiddleware,
    SecurityHeadersMiddleware,
    TraceIdMiddleware,
)
from acip_core.obs import setup_telemetry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    admin,
    admin_ai_discovery,
    admin_ai_finance,
    admin_ai_models,
    admin_ai_providers,
    admin_ai_routing,
    admin_audit,
    admin_auth,
    admin_auth_account,
    admin_auth_totp,
    admin_billing_ops,
    admin_contact,
    admin_credit_policy,
    admin_es,
    admin_governance,
    admin_misc,
    admin_monitoring,
    admin_operators,
    admin_ops_status,
    admin_plans,
    admin_search_insight,
    admin_security,
    admin_tenant_ops,
    admin_users,
    auth,
    auth_password,
    billing,
    billing_invoices,
    billing_webhooks,
    health,
    public,
    tenant,
    tenant_credits,
    tenant_governance,
    tenant_kb,
    tenant_keys,
    tenant_leads,
    tenant_search,
    tenant_settings,
    tenant_sync,
    tenant_team,
    v1,
    widget,
)


async def _bootstrap_search_index(log) -> None:
    """Best-effort first-run bootstrap: ensure the catalogue index exists
    behind the read alias so a fresh deployment can serve /v1/search without a
    manual console step. Failures (ES down/not configured) are logged and
    ignored — startup must never block on the cluster."""
    try:
        import acip_search.index_admin as ia
        from acip_core.clients import get_es_client

        result = await ia.ensure_catalogue_index(get_es_client())
        log.info("es.bootstrap", status=result.get("status"), index=result.get("index"))
    except Exception as exc:  # noqa: BLE001 - degradation path, by design
        log.warning("es.bootstrap_skipped", error=str(exc))

    try:
        import acip_search.orders_index as oi
        from acip_core.clients import get_es_client

        result = await oi.ensure_orders_index(get_es_client())
        log.info("es.orders_bootstrap", status=result.get("status"), index=result.get("index"))
    except Exception as exc:  # noqa: BLE001 - degradation path, by design
        log.warning("es.orders_bootstrap_skipped", error=str(exc))


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name)
    log = get_logger("api")

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        log.info("api.startup", env=settings.env)
        bootstrap_task = None
        if settings.es_bootstrap_on_startup:
            import asyncio

            bootstrap_task = asyncio.create_task(_bootstrap_search_index(log))
        yield
        if bootstrap_task is not None and not bootstrap_task.done():
            bootstrap_task.cancel()
        log.info("api.shutdown")

    app = FastAPI(
        title="Vitrin API",
        version="0.1.0",
        description="Vitrin — AI Commerce Intelligence Platform (public + auth + admin API).",
        lifespan=lifespan,
    )
    # Middleware (added inner→outer; CORS added last = outermost so it also
    # decorates error/preflight responses).
    if settings.admin_ip_allowlist_list:
        # Operator plane (Phase 9): /admin/* only from the allowed networks.
        # Added BEFORE TraceId so TraceId wraps it and the 403 carries a
        # request id (later add_middleware = outermost).
        from acip_core.middleware import AdminIpAllowlistMiddleware

        app.add_middleware(
            AdminIpAllowlistMiddleware, allowlist=settings.admin_ip_allowlist_list
        )
    app.add_middleware(TraceIdMiddleware)
    if settings.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
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
    setup_telemetry(app, settings)

    app.include_router(health.router)
    app.include_router(public.router)
    app.include_router(auth.router)
    app.include_router(auth_password.router)
    app.include_router(tenant.router)
    app.include_router(tenant_search.router)
    app.include_router(tenant_sync.router)
    app.include_router(tenant_leads.router)
    app.include_router(tenant_keys.router)
    app.include_router(tenant_settings.router)
    app.include_router(tenant_team.router)
    app.include_router(tenant_governance.router)
    app.include_router(tenant_credits.router)
    app.include_router(tenant_kb.router)
    app.include_router(billing.router)
    app.include_router(billing_invoices.router)
    app.include_router(billing_webhooks.router)
    app.include_router(v1.router)
    app.include_router(widget.router)
    app.include_router(admin_auth.router)
    app.include_router(admin_auth_account.router)
    app.include_router(admin_auth_totp.router)
    app.include_router(admin.router)
    app.include_router(admin_tenant_ops.router)
    app.include_router(admin_users.router)
    app.include_router(admin_audit.router)
    app.include_router(admin_billing_ops.router)
    app.include_router(admin_search_insight.router)
    app.include_router(admin_governance.router)
    app.include_router(admin_security.router)
    app.include_router(admin_monitoring.router)
    app.include_router(admin_ops_status.router)
    app.include_router(admin_es.router)
    app.include_router(admin_plans.router)
    app.include_router(admin_contact.router)
    app.include_router(admin_misc.router)
    app.include_router(admin_ai_providers.router)
    app.include_router(admin_ai_models.router)
    app.include_router(admin_ai_routing.router)
    app.include_router(admin_ai_discovery.router)
    app.include_router(admin_ai_finance.router)
    app.include_router(admin_credit_policy.router)
    app.include_router(admin_operators.router)

    return app


app = create_app()
