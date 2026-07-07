"""Store-owner dashboard — knowledge base (assistant grounding content)."""

from __future__ import annotations

from typing import Any

from acip_core.audit import audit
from acip_core.clients import get_pg_pool
from acip_core.errors import error_response
from fastapi import APIRouter

from .tenant_common import _AUTHZ, _COOKIE, _require_tenant, _unauth

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/kb")
async def kb_list(authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, title, body, published, updated_at FROM kb_articles "
            "WHERE tenant_id = $1 ORDER BY updated_at DESC",
            p.tenant_id,
        )
    return {
        "articles": [
            {
                "id": str(r["id"]),
                "title": r["title"],
                "body": r["body"],
                "published": r["published"],
                "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ]
    }


@router.post("/kb")
async def kb_create(
    payload: dict[str, Any], authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    title = str(payload.get("title", "")).strip()
    body = str(payload.get("body", "")).strip()
    if not title or not body:
        return error_response(422, "invalid_request", "title and body are required.")
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        new_id = await conn.fetchval(
            "INSERT INTO kb_articles (tenant_id, title, body) VALUES ($1, $2, $3) RETURNING id",
            p.tenant_id,
            title,
            body,
        )
    await audit(
        pool, actor=p.email, action="kb.create", tenant_id=p.tenant_id, detail={"title": title}
    )
    return {"id": str(new_id), "status": "created"}


@router.patch("/kb/{article_id}")
async def kb_update(
    article_id: str,
    payload: dict[str, Any],
    authorization: str | None = _AUTHZ,
    vitrin_access: str | None = _COOKIE,
):
    """Edit an article's title, body, or published state (tenant-scoped)."""
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    sets: list[str] = []
    values: list[Any] = []
    if "title" in payload:
        title = str(payload["title"]).strip()
        if not title:
            return error_response(422, "invalid_request", "title cannot be empty.")
        values.append(title)
        sets.append(f"title = ${len(values)}")
    if "body" in payload:
        body = str(payload["body"]).strip()
        if not body:
            return error_response(422, "invalid_request", "body cannot be empty.")
        values.append(body)
        sets.append(f"body = ${len(values)}")
    if "published" in payload:
        values.append(bool(payload["published"]))
        sets.append(f"published = ${len(values)}")
    if not sets:
        return error_response(422, "invalid_request", "No editable fields supplied.")
    values.extend([article_id, p.tenant_id])
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        updated = await conn.fetchval(
            f"UPDATE kb_articles SET {', '.join(sets)}, updated_at = now() "
            f"WHERE id = ${len(values) - 1} AND tenant_id = ${len(values)} RETURNING id",
            *values,
        )
    if updated is None:
        return error_response(404, "not_found", "No such article.")
    await audit(
        pool, actor=p.email, action="kb.update", tenant_id=p.tenant_id,
        detail={"id": article_id, "fields": list(payload.keys())},
    )
    return {"id": article_id, "status": "updated"}


@router.delete("/kb/{article_id}")
async def kb_delete(
    article_id: str, authorization: str | None = _AUTHZ, vitrin_access: str | None = _COOKIE
):
    p = await _require_tenant(authorization, vitrin_access)
    if p is None:
        return _unauth()
    assert p.tenant_id is not None
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM kb_articles WHERE id = $1 AND tenant_id = $2", article_id, p.tenant_id
        )
    await audit(
        pool, actor=p.email, action="kb.delete", tenant_id=p.tenant_id, detail={"id": article_id}
    )
    return {"status": "deleted"}
