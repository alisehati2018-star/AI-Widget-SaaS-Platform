"""Shared ASGI middleware: trace id, security headers, and CSRF (REQ-M12-004)."""

from __future__ import annotations

import hmac
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .logging import trace_id_var

TRACE_HEADER = "x-request-id"
ACCESS_COOKIE = "vitrin_access"
CSRF_COOKIE = "vitrin_csrf"
# The admin identity plane uses its own cookie pair (services/api/routers/
# admin_auth.py) — fully separate from the customer cookies above.
ADMIN_ACCESS_COOKIE = "vitrin_admin_access"
ADMIN_CSRF_COOKIE = "vitrin_admin_csrf"
CSRF_HEADER = "x-csrf-token"
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})


class TraceIdMiddleware(BaseHTTPMiddleware):
    """Ensure each request has a trace id and echo it back in the response.

    Every error envelope and log line carries this id so a request is
    traceable end to end (blueprint §12.1, §14.3).
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get(TRACE_HEADER) or uuid.uuid4().hex
        token = trace_id_var.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            trace_id_var.reset(token)
        response.headers[TRACE_HEADER] = trace_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record request count + latency per method/status into the metrics registry."""

    async def dispatch(self, request: Request, call_next):
        import time

        from .obs import metrics

        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            method = request.method
            metrics.inc("vitrin_http_requests_total", {"method": method, "status": str(status)})
            metrics.observe("vitrin_http_request_duration_seconds", elapsed, {"method": method})


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard hardening headers to every response (SE-2).

    CSP is intentionally strict for the API (no inline anything); the Next.js
    frontend is served separately and sets its own CSP.
    """

    def __init__(self, app, *, hsts: bool = False) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        h.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if self._hsts:
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class CsrfMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for **cookie-authenticated** unsafe requests.

    Bearer-token requests (Authorization header) are exempt — browsers don't
    attach those automatically, so they aren't CSRF-able. Only requests that
    authenticate via the access cookie must present a matching ``x-csrf-token``
    header (compared to the ``vitrin_csrf`` cookie). This keeps the existing
    bearer flow working unchanged during the dual-support window.

    Unauthenticated public endpoints (auth, the signed billing webhook, contact)
    are exempt: their action does not rely on the session cookie, so CSRF is not
    the threat model — and a stale cookie must not block sign-in / signup.
    """

    # Path prefixes whose action is authenticated by body/credentials/signature,
    # not by the session cookie. The cookie-protected surfaces are /tenant/*
    # and /admin/* (still enforced below). /admin/auth/ mirrors /auth/ — its
    # own login/refresh/logout/bootstrap run before any session cookie exists.
    _EXEMPT = ("/auth/", "/admin/auth/", "/billing/webhook", "/contact")

    def _blocked(self, request: Request, access_cookie_name: str, csrf_cookie_name: str) -> bool:
        cookie = request.cookies.get(access_cookie_name)
        if not cookie:
            return False
        header = request.headers.get(CSRF_HEADER, "")
        csrf_cookie = request.cookies.get(csrf_cookie_name, "")
        return not header or not csrf_cookie or not hmac.compare_digest(header, csrf_cookie)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method not in _SAFE_METHODS and not path.startswith(self._EXEMPT):
            has_bearer = "authorization" in request.headers
            # Scope the check to the plane the path actually belongs to (admin
            # vs customer) so an unrelated, stale cookie from the *other* plane
            # in the same browser can never block a valid request.
            access_name, csrf_name = (
                (ADMIN_ACCESS_COOKIE, ADMIN_CSRF_COOKIE)
                if path.startswith("/admin/")
                else (ACCESS_COOKIE, CSRF_COOKIE)
            )
            if not has_bearer and self._blocked(request, access_name, csrf_name):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "csrf_failed",
                            "message": "Missing or invalid CSRF token.",
                            "request_id": trace_id_var.get(),
                        }
                    },
                )
        return await call_next(request)
