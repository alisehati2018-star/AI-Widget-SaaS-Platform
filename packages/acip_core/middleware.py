"""Shared ASGI middleware: assign/propagate a trace id on every request (REQ-M12-004)."""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .logging import trace_id_var

TRACE_HEADER = "x-request-id"


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
