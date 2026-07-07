"""Admin surface — Elasticsearch control panel (M2/M9): operator-plane index
management. Non-destructive reads + guarded create/reindex/alias/delete
operations so an operator can fully control the cluster from the dashboard."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_es_client, get_pg_pool
from acip_core.config import get_settings
from acip_core.errors import error_response
from fastapi import APIRouter

from .admin_common import _ADMIN, _AUTHZ, _COOKIE, _admin_ok, _forbidden

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/es/health")
async def es_health(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import acip_search.index_admin as ia

    es = get_es_client()
    try:
        health = await ia.cluster_health(es)
    except Exception as exc:  # noqa: BLE001 - surface a clean "unreachable" state
        return {"reachable": False, "error": str(exc)}
    return {"reachable": True, **health}


@router.get("/es/indices")
async def es_indices(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import acip_search.index_admin as ia

    es = get_es_client()
    s = get_settings()
    return {
        "alias": s.catalogue_alias,
        "indices": await ia.list_indices(es),
        "aliases": await ia.list_aliases(es),
    }


@router.get("/es/mapping")
async def es_mapping(
    index: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import acip_search.index_admin as ia

    try:
        return {"index": index, **await ia.get_mapping_and_settings(get_es_client(), index)}
    except Exception as exc:  # noqa: BLE001
        return error_response(404, "not_found", f"Index not found: {exc}")


@router.get("/es/tenant-count")
async def es_tenant_count(
    tenant: str,
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """How many catalogue docs a given store has indexed (sync verification)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import acip_search.index_admin as ia

    return {"tenant_id": tenant, "docs": await ia.tenant_doc_count(get_es_client(), tenant)}


@router.post("/es/ensure-index")
async def es_ensure_index(
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Idempotently create the catalogue index behind the read alias."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    import acip_search.index_admin as ia

    try:
        result = await ia.ensure_catalogue_index(get_es_client())
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(await get_pg_pool(), actor="operator", action="es.ensure_index", detail=result)
    return result


@router.post("/es/reindex")
async def es_reindex(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Build a fresh index, reindex into it, then swap the read alias (zero
    downtime, instant rollback by re-pointing the alias)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    source = str(payload.get("source_index", "")).strip()
    if not source:
        return error_response(422, "invalid_request", "Field 'source_index' is required.")
    import acip_search.index_admin as ia

    try:
        new_index = await ia.reindex_and_swap(get_es_client(), source)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(
        await get_pg_pool(),
        actor="operator",
        action="es.reindex",
        detail={"source": source, "new_index": new_index},
    )
    return {"status": "reindexed", "source_index": source, "new_index": new_index}


@router.post("/es/alias")
async def es_alias(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Atomically point the read alias at a chosen index (manual rollback/swap)."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    to_index = str(payload.get("index", "")).strip()
    if not to_index:
        return error_response(422, "invalid_request", "Field 'index' is required.")
    alias = str(payload.get("alias") or get_settings().catalogue_alias)
    import acip_search.index_admin as ia

    try:
        await ia.point_alias(get_es_client(), alias, to_index)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(
        await get_pg_pool(),
        actor="operator",
        action="es.alias_swap",
        detail={"alias": alias, "index": to_index},
    )
    return {"status": "swapped", "alias": alias, "index": to_index}


@router.post("/es/delete-index")
async def es_delete_index(
    payload: dict[str, Any],
    x_admin_token: str | None = _ADMIN,
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Delete a concrete index (e.g. an old version after a successful swap).

    Refuses to delete an index that the read alias currently points at."""
    if not await _admin_ok(x_admin_token, authorization, vitrin_access):
        return _forbidden()
    index = str(payload.get("index", "")).strip()
    if not index:
        return error_response(422, "invalid_request", "Field 'index' is required.")
    import acip_search.index_admin as ia

    es = get_es_client()
    live = {a["index"] for a in await ia.list_aliases(es)}
    if index in live:
        return error_response(
            409, "alias_in_use", "This index is live behind an alias; swap the alias first."
        )
    try:
        await ia.delete_index(es, index)
    except Exception as exc:  # noqa: BLE001
        return error_response(500, "es_error", str(exc))
    await audit(await get_pg_pool(), actor="operator", action="es.delete_index",
                detail={"index": index})
    return {"status": "deleted", "index": index}
