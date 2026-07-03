"""Typed request models for the public + money-moving surfaces (audit W11).

Validation runs INSIDE the handlers (``parse``) instead of as FastAPI body
models, so the platform's stable error envelope
(``{"error": {"code", "message", "request_id"}}``) is preserved — widgets and
store plugins already depend on it. The models also add size guardrails the
manual checks never had (query/message length, bulk batch cap).
"""

from __future__ import annotations

from typing import Any, TypeVar

from acip_core.errors import error_response
from pydantic import BaseModel, Field, ValidationError

M = TypeVar("M", bound=BaseModel)


def parse(model: type[M], payload: Any) -> tuple[M | None, Any]:
    """(instance, None) on success; (None, 422 error_response) on failure."""
    try:
        return model.model_validate(payload or {}), None
    except ValidationError as exc:
        errors = exc.errors()
        loc = ".".join(str(x) for x in errors[0]["loc"]) if errors else "body"
        msg = errors[0]["msg"] if errors else "invalid"
        return None, error_response(
            422, "invalid_request", f"Invalid field '{loc or 'body'}': {msg}."
        )


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    filters: dict[str, Any] | None = None
    size: int | None = Field(default=None, ge=1, le=50)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = Field(default=None, max_length=64)


class BulkSyncRequest(BaseModel):
    source: str = Field(default="rest", max_length=32)
    products: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=32)


class TopupRequest(BaseModel):
    credits: float = Field(gt=0, le=10_000_000)
