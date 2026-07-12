"""Consistent error envelope (blueprint §12.1: code, message, request-id).

EVERY error leaving the API — handler-raised, validation, framework
HTTPException, or unhandled crash — must use this envelope so clients can
switch on ``error.code`` (the web app maps codes to localized messages).
"""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .logging import trace_id_var

# Stable codes for envelope-less framework statuses.
_STATUS_CODES = {
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
}


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "request_id": trace_id_var.get()}},
    )


def not_implemented(feature: str) -> JSONResponse:
    """Phase-0 placeholder for endpoints whose logic lands in later phases."""
    return error_response(
        501,
        "not_implemented",
        f"{feature} is not implemented in Phase 0 (foundation only).",
    )


async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    return error_response(500, "internal_error", "An unexpected error occurred.")


async def validation_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Pydantic/FastAPI request validation → the standard envelope (not the
    default ``{"detail": [...]}`` shape clients don't understand)."""
    detail = "Invalid request."
    if isinstance(exc, RequestValidationError) and exc.errors():
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first.get("loc", []) if p not in ("body", "query"))
        msg = first.get("msg", "invalid value")
        detail = f"{loc}: {msg}" if loc else msg
    return error_response(422, "validation_error", detail)


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Framework-raised HTTPException (404 route miss, 405, dependencies…) →
    the standard envelope with a stable, mappable code."""
    status = exc.status_code if isinstance(exc, StarletteHTTPException) else 500
    detail = str(getattr(exc, "detail", "")) or "Request failed."
    return error_response(status, _STATUS_CODES.get(status, "http_error"), detail)
