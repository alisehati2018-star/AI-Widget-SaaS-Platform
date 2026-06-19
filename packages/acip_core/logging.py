"""Structured JSON logging with a per-request trace id (REQ-M12-004)."""

from __future__ import annotations

import logging
from contextvars import ContextVar

import structlog

# Propagated by middleware so every log line in a request carries the same id.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def _inject_trace_id(_logger, _name, event_dict):
    event_dict["trace_id"] = trace_id_var.get()
    return event_dict


def configure_logging(level: str = "INFO", service_name: str = "acip") -> None:
    """Configure structlog to emit JSON lines. Idempotent."""
    logging.basicConfig(format="%(message)s", level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_trace_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.EventRenamer("msg"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
    structlog.get_logger().bind(service=service_name)


def get_logger(name: str | None = None):
    return structlog.get_logger(name)
