"""Seed a demo Persian catalogue: tenant + API keys + 100 real products.

Creates (idempotently) a demo tenant in Postgres, issues a widget key and a
sync key (printed ONCE), ensures the catalogue index exists behind the read
alias, then ingests the 100-product Persian fixture through the REAL sync
pipeline (normalize → optional embedding → idempotent upsert → data-version
bump). After it finishes, `/v1/search` and `/v1/chat` answer with live data
for the printed widget key.

Usage (repo root; PG/ES settings via env or .env, same as the API):
    PYTHONPATH=packages:services python scripts/seed_catalog.py
    python scripts/seed_catalog.py --slug demo-fa --dry-run     # validate only
    python scripts/seed_catalog.py --no-embeddings              # lexical only

Windows PowerShell:
    $env:PYTHONPATH = "packages;services"
    python scripts/seed_catalog.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "catalog_fa.json"


def _load_fixture() -> list[dict]:
    products = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(products, list) and products, "fixture must be a non-empty list"
    return products


async def _ensure_tenant(slug: str, name: str) -> tuple[str, str, str]:
    """Create/find the demo tenant and issue fresh widget + sync keys."""
    from acip_core.clients import get_pg_pool
    from api.deps import hash_key  # same hashing as the API key resolver

    widget_key = "acip_" + secrets.token_urlsafe(24)
    sync_key = "acip_" + secrets.token_urlsafe(24)
    pool = await get_pg_pool()
    async with pool.acquire() as conn:
        tenant_id = await conn.fetchval(
            "INSERT INTO tenants (slug, name) VALUES ($1, $2) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
            slug,
            name,
        )
        # Re-running the seed must not leave a trail of still-valid old keys.
        await conn.execute(
            "UPDATE api_keys SET revoked = true "
            "WHERE tenant_id = $1 AND label IN ('seed widget', 'seed sync') AND NOT revoked",
            tenant_id,
        )
        for key, scope, label in (
            (widget_key, "widget", "seed widget"),
            (sync_key, "sync", "seed sync"),
        ):
            await conn.execute(
                "INSERT INTO api_keys (tenant_id, key_hash, scope, label) VALUES ($1, $2, $3, $4)",
                tenant_id,
                hash_key(key),
                scope,
                label,
            )
    return str(tenant_id), widget_key, sync_key


async def _seed(slug: str, name: str, use_embeddings: bool) -> int:
    from acip_cache.data_version import bump_data_version
    from acip_core.clients import get_es_client, get_redis
    from acip_embedding import get_embedding_client
    from acip_search import index_admin as ia
    from acip_sync.ingest import upsert_product
    from acip_sync.normalize import normalize_product

    products = _load_fixture()
    tenant_id, widget_key, sync_key = await _ensure_tenant(slug, name)

    es = get_es_client()
    bootstrap = await ia.ensure_catalogue_index(es)
    print(f"index: {bootstrap.get('status')} → {bootstrap.get('index')}")

    embedder = get_embedding_client(redis=get_redis()) if use_embeddings else None
    embedded = 0
    for raw in products:
        product = normalize_product(tenant_id, "rest", raw)
        vector = None
        if embedder is not None:
            try:
                vector = await embedder.embed_one(product.embedding_text())
                embedded += 1
            except Exception:  # noqa: BLE001 - embeddings optional: lexical still works
                embedder = None  # service down: stop retrying per-product
        await upsert_product(es, product, embedding=vector)
    await es.indices.refresh(index=None, ignore_unavailable=True)
    await bump_data_version(get_redis(), tenant_id)

    print(f"tenant:  {slug} ({tenant_id})")
    print(f"indexed: {len(products)} products ({embedded} with embeddings)")
    print("-- keys are shown ONCE; store them now --")
    print(f"widget key: {widget_key}")
    print(f"sync key:   {sync_key}")
    print("\nquick test:")
    print(
        f'  curl -s http://localhost:8000/v1/search -H "x-api-key: {widget_key}" '
        '-H "content-type: application/json" -d \'{"query": "گوشی سامسونگ"}\''
    )
    return len(products)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slug", default="demo-fa", help="demo tenant slug")
    parser.add_argument("--name", default="فروشگاه نمونهٔ ویترین", help="demo tenant name")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="validate the fixture + normalisation without touching PG/ES",
    )
    parser.add_argument(
        "--no-embeddings", action="store_true",
        help="skip dense vectors (lexical-only index; faster, no TEI needed)",
    )
    args = parser.parse_args()

    if args.dry_run:
        from acip_sync.normalize import normalize_product

        products = _load_fixture()
        seen: set[str] = set()
        for raw in products:
            p = normalize_product("dry-run-tenant", "rest", raw)
            assert p.product_id and p.product_id not in seen, f"duplicate id {p.product_id}"
            assert p.title and p.price is not None, f"incomplete product {p.product_id}"
            assert p.embedding_text(), f"empty embedding text {p.product_id}"
            seen.add(p.product_id)
        print(f"dry-run OK: {len(products)} products validated (ids p-001…p-{len(products):03d})")
        return

    count = asyncio.run(_seed(args.slug, args.name, use_embeddings=not args.no_embeddings))
    print(f"\ndone — {count} products live.")


if __name__ == "__main__":
    main()
