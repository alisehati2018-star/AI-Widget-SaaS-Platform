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
    """

    async def dispatch(self, request: Request, call_next):
        if request.method not in _SAFE_METHODS:
            has_bearer = "authorization" in request.headers
            access_cookie = request.cookies.get(ACCESS_COOKIE)
            if access_cookie and not has_bearer:
                header = request.headers.get(CSRF_HEADER, "")
                cookie = request.cookies.get(CSRF_COOKIE, "")
                if not header or not cookie or not hmac.compare_digest(header, cookie):
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
