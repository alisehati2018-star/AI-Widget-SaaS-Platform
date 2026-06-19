"""Consistent error envelope (blueprint §12.1: code, message, request-id)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from .logging import trace_id_var


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
