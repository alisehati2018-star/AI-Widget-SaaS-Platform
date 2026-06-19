"""Versioned shopper/connector API surface (blueprint §12).

Phase 0 ships the *contract skeleton* only: routes exist and are documented,
but return 501 until their owning phase implements them:
  /v1/search, /v1/suggest  -> M5, Phase 1
  /v1/chat                 -> M7, Phase 2
  /v1/sync/*               -> M3, Phase 1
"""

from __future__ import annotations

from acip_core.errors import not_implemented
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["v1"])


@router.post("/search")
async def search():
    return not_implemented("Hybrid search (/v1/search, M5)")


@router.get("/suggest")
async def suggest():
    return not_implemented("Autocomplete (/v1/suggest, M5)")


@router.post("/chat")
async def chat():
    return not_implemented("Assistant chat (/v1/chat, M7)")


@router.post("/sync/webhook")
async def sync_webhook():
    return not_implemented("Store change webhook (/v1/sync/webhook, M3)")


@router.post("/sync/bulk")
async def sync_bulk():
    return not_implemented("Bulk import / backfill (/v1/sync/bulk, M3)")
