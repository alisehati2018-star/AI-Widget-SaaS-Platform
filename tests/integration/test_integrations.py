"""Phase 7 (completion roadmap) — store integrations: the delta-pull pilot loop.

Runs the REAL worker reconciliation (`_reconcile_one` / `_reconcile_all`)
against the pilot store simulator (`scripts/pilot_store.py`) on a live
Postgres: tenant settings → watermarked pull (Woo REST and the OpenCart module
export contract) → normalize/upsert (stub ES) → sync_state bookkeeping →
second run pulls only what changed. Skipped when PG is down.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
import uuid

import pytest

# One loop for the whole module: `get_pg_pool()` caches a pool bound to the
# first running loop, so a fresh loop per test would break every later test
# (same rule as the worker's persistent loop).
_LOOP = asyncio.new_event_loop()


def _run(coro):
    return _LOOP.run_until_complete(coro)


@pytest.fixture(scope="module")
def pilot_store():
    """The pilot shop simulator as a real subprocess (like a real local store)."""
    import httpx

    port = int(os.environ.get("PILOT_PORT", "9099"))
    proc = subprocess.Popen(
        [sys.executable, "scripts/pilot_store.py", "--port", str(port)],
        env={**os.environ, "PYTHONPATH": "packages:services"},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(40):
            if proc.poll() is not None:
                pytest.skip("pilot store failed to start")
            try:
                if httpx.get(f"{base}/healthz", timeout=1).status_code == 200:
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.25)
        else:
            pytest.skip("pilot store did not become ready")
        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            proc.kill()


class _StubES:
    """Records upserts; enough for the pull loop (ES-side is covered ES-gated)."""

    def __init__(self):
        self.docs: list[dict] = []

    async def index(self, **kwargs):
        self.docs.append(kwargs)


async def _mk_tenant(settings: dict) -> str:
    import json

    import asyncpg
    from acip_core.config import get_settings

    conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=5)
    try:
        tid = await conn.fetchval(
            "INSERT INTO tenants (slug, name, settings) VALUES ($1, $2, $3::jsonb) RETURNING id",
            f"p7-{uuid.uuid4().hex[:10]}",
            "P7 pilot",
            json.dumps(settings),
        )
    finally:
        await conn.close()
    return str(tid)


async def _sync_row(tid: str, source: str):
    import asyncpg
    from acip_core.config import get_settings

    conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=5)
    try:
        return await conn.fetchrow(
            "SELECT last_status, high_watermark FROM sync_state "
            "WHERE tenant_id = $1::uuid AND source = $2",
            uuid.UUID(tid),
            source,
        )
    finally:
        await conn.close()


def _pg_up() -> bool:
    async def _probe() -> bool:
        try:
            import asyncpg
            from acip_core.config import get_settings

            conn = await asyncpg.connect(dsn=get_settings().pg_dsn, timeout=3)
            await conn.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    return _run(_probe())


@pytest.fixture(autouse=True)
def _require_pg():
    if not _pg_up():
        pytest.skip("Postgres not reachable; skipping integrations tests.")


@pytest.fixture()
def stub_es(monkeypatch):
    import worker.tasks as wt

    es = _StubES()
    monkeypatch.setattr(wt, "get_es_client", lambda: es)
    return es


def test_woo_pull_loop_with_watermark(pilot_store, stub_es):
    from worker.tasks import _reconcile_one

    tid = _run(
        _mk_tenant(
            {
                "platform": "woocommerce",
                "store_url": pilot_store,
                "woo_consumer_key": "ck_pilot",
                "woo_consumer_secret": "cs_pilot",
            }
        )
    )
    # First run: full backfill of the 8 pilot products.
    assert _run(_reconcile_one(tid, "woocommerce")) == "ok:8"
    assert len(stub_es.docs) == 8
    titles = [d["document"]["title"] for d in stub_es.docs]
    assert "گوشی موبایل سامسونگ گلکسی A55" in titles
    row = _run(_sync_row(tid, "woocommerce"))
    assert row["last_status"] == "ok" and row["high_watermark"] is not None

    # Second run without changes: watermark filters everything out.
    stub_es.docs.clear()
    assert _run(_reconcile_one(tid, "woocommerce")) == "ok:0"
    assert stub_es.docs == []

    # "Edit" one product in the store → only that one is pulled.
    import httpx

    assert httpx.post(f"{pilot_store}/touch/4", timeout=5).status_code == 200
    assert _run(_reconcile_one(tid, "woocommerce")) == "ok:1"
    assert [d["document"]["product_id"] for d in stub_es.docs] == ["4"]


def test_opencart_pull_uses_module_export_contract(pilot_store, stub_es):
    from worker.tasks import _reconcile_one

    tid = _run(
        _mk_tenant(
            {
                "platform": "opencart",
                "store_url": pilot_store,
                "oc_export_token": "pilot-token",
            }
        )
    )
    assert _run(_reconcile_one(tid, "opencart")) == "ok:8"
    doc = stub_es.docs[0]["document"]
    assert doc["tenant_id"] == tid and doc["brand"]  # manufacturer mapped to brand

    # Wrong token → recorded as error, never raised.
    tid2 = _run(
        _mk_tenant(
            {"platform": "opencart", "store_url": pilot_store, "oc_export_token": "WRONG"}
        )
    )
    assert _run(_reconcile_one(tid2, "opencart")) == "error"
    row = _run(_sync_row(tid2, "opencart"))
    assert row["last_status"] == "error"


def test_reconcile_all_sweeps_connected_tenants(pilot_store, stub_es):
    from worker.tasks import _reconcile_all

    tid = _run(
        _mk_tenant(
            {
                "platform": "woocommerce",
                "store_url": pilot_store,
                "woo_consumer_key": "ck_pilot",
                "woo_consumer_secret": "cs_pilot",
            }
        )
    )
    out = _run(_reconcile_all())
    assert out.startswith("swept:")
    assert _run(_sync_row(tid, "woocommerce"))["last_status"] == "ok"


def test_unconfigured_tenant_records_ok_heartbeat(stub_es):
    from worker.tasks import _reconcile_one

    tid = _run(_mk_tenant({"platform": "custom"}))
    assert _run(_reconcile_one(tid, "rest")) == "ok"
    assert stub_es.docs == []
    assert _run(_sync_row(tid, "rest"))["last_status"] == "ok"
