"""Versioned shopper/connector API surface (blueprint §12).

Phase 1 implements search, suggest, and sync; `/v1/chat` stays 501 (M7, Phase 2).
Every endpoint is tenant-scoped via the API key (REQ-M11-001). The mandatory
`tenant_id` filter is enforced centrally in `acip_search.query`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from acip_core.errors import error_response
from acip_search.suggest import suggest as run_suggest
from acip_sync.connectors import get_connector
from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from ..deps import API_KEY_HEADER, resolve_principal
from ..runtime import get_assistant, get_search_service

router = APIRouter(prefix="/v1", tags=["v1"])

# Shared API-key header dependency default (keeps signatures readable).
_KEY = Header(default=None, alias=API_KEY_HEADER)


def _unauthorized():
    return error_response(401, "unauthorized", "A valid x-api-key is required.")


@router.post("/search")
async def search(payload: dict[str, Any], x_api_key: str | None = _KEY):
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    query = str(payload.get("query", "")).strip()
    if not query:
        return error_response(422, "invalid_request", "Field 'query' is required.")
    svc = get_search_service()
    result = await svc.search(
        principal.tenant_id,
        query,
        filters=payload.get("filters"),
        size=payload.get("size"),
    )
    return result


@router.get("/suggest")
async def suggest(q: str = "", x_api_key: str | None = _KEY):
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    if not q.strip():
        return {"suggestions": []}
    from acip_core.clients import get_es_client

    items = await run_suggest(get_es_client(), principal.tenant_id, q.strip())
    return {"suggestions": items}


@router.post("/sync/webhook")
async def sync_webhook(
    request: Request,
    source: str = "rest",
    x_api_key: str | None = _KEY,
):
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    payload = await request.json()
    connector = get_connector(source)
    event = connector.parse(payload)
    # Enqueue for the worker (event-driven fast path). Import is lazy so the API
    # does not hard-depend on the broker at import time.
    from worker.tasks import process_webhook_event

    process_webhook_event.delay(
        principal.tenant_id, source, event.type.value, event.product_id, event.raw
    )
    return {"status": "accepted", "product_id": event.product_id, "type": event.type.value}


@router.post("/sync/bulk")
async def sync_bulk(payload: dict[str, Any], x_api_key: str | None = _KEY):
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    source = str(payload.get("source", "rest"))
    products = payload.get("products", [])
    if not isinstance(products, list):
        return error_response(422, "invalid_request", "Field 'products' must be a list.")
    from worker.tasks import bulk_import

    bulk_import.delay(principal.tenant_id, source, products)
    return {"status": "accepted", "count": len(products)}


@router.post("/chat")
async def chat(payload: dict[str, Any], x_api_key: str | None = _KEY):
    """Grounded RAG assistant turn (M7). Tenant-scoped; answers strictly from
    the store's own data via the gateway cache→route→compress→generate ladder."""
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    message = str(payload.get("message", "")).strip()
    if not message:
        return error_response(422, "invalid_request", "Field 'message' is required.")
    session_id = str(payload.get("session_id") or uuid.uuid4().hex)
    assistant = get_assistant()
    result = await assistant.answer(principal.tenant_id, session_id, message)

    # Best-effort in-conversation lead capture (M10-004); never breaks the turn.
    from acip_analytics import capture_lead, detect_lead
    from acip_core.clients import get_pg_pool

    signal = detect_lead(message)
    if signal.is_lead:
        await capture_lead(await get_pg_pool(), principal.tenant_id, signal)

    return {"session_id": session_id, **result}


@router.post("/chat/stream")
async def chat_stream(payload: dict[str, Any], x_api_key: str | None = _KEY):
    """Server-Sent-Events streaming chat (M7: REQ-M7-007).

    Streams the grounded answer so the widget renders progressively (first-token
    target < 1.5 s — measured in the Validation phase). The full turn still goes
    through the gateway ladder + guardrails; this endpoint chunks the result as
    SSE `data:` frames. True per-token model streaming is wired to vLLM at
    validation time via `acip_gateway.llm_client.LLMClient.stream`.
    """
    principal = await resolve_principal(x_api_key)
    if not principal.tenant_id:
        return _unauthorized()
    message = str(payload.get("message", "")).strip()
    if not message:
        return error_response(422, "invalid_request", "Field 'message' is required.")
    session_id = str(payload.get("session_id") or uuid.uuid4().hex)
    result = await get_assistant().answer(principal.tenant_id, session_id, message)

    async def _events():
        yield f"event: meta\ndata: {json.dumps({'session_id': session_id})}\n\n"
        for token in str(result.get("answer", "")).split():
            yield f"data: {json.dumps({'token': token + ' '})}\n\n"
        yield f"event: done\ndata: {json.dumps({'citations': result.get('citations', [])})}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream")
