"""Fixtures for ES-gated integration tests.

These run only when an Elasticsearch cluster is reachable (CI service container
or local `docker compose`). They are skipped otherwise so the unit suite stays
hermetic.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from acip_core.config import get_settings


@pytest.fixture(scope="session")
def es_client():
    es = pytest.importorskip("elasticsearch")
    s = get_settings()
    client = es.Elasticsearch(
        hosts=[s.es_host],
        basic_auth=(s.es_username, s.es_password) if s.es_password else None,
        verify_certs=s.es_verify_certs,
        request_timeout=5,
    )
    try:
        if not client.ping():
            pytest.skip("Elasticsearch not reachable; skipping integration tests.")
    except Exception:  # noqa: BLE001
        pytest.skip("Elasticsearch not reachable; skipping integration tests.")
    return client


ADMIN_TOKEN = "integration-operator-token"


@pytest.fixture(scope="session")
def live_client():
    """An httpx client against a **real uvicorn subprocess** on a live Postgres.

    Runs over HTTP (own process/loop) — exactly like production — rather than the
    in-process TestClient, which mixes the test loop with asyncpg's pool. Skips
    unless PG is reachable. Elasticsearch is not required. Turns the manual curl
    validations (auth, tenant isolation, billing lifecycle) into automated tests.
    """
    import subprocess
    import time

    import httpx

    env = {
        **os.environ,
        "AUTH_SECRET": os.environ.get("AUTH_SECRET", "integration-secret-0123456789abcdef"),
        "ADMIN_TOKEN": ADMIN_TOKEN,
        "BILLING_WEBHOOK_SECRET": os.environ.get("BILLING_WEBHOOK_SECRET", "integration-whsec"),
        "AUTH_IP_RATE_PER_MIN": "100000",
        "EMAIL_PROVIDER": "console",
        # Pin the security-relevant flags so the suite is deterministic and does
        # not depend on a developer's local .env (which may relax these).
        "EMAIL_VERIFICATION_REQUIRED": "true",
        "SIGNUP_ENABLED": "true",
        "CSRF_ENABLED": "true",
        "BILLING_PROVIDER": "manual",
        "PYTHONPATH": "packages:services",
    }
    get_settings.cache_clear()
    s = get_settings()

    async def _reachable() -> bool:
        try:
            import asyncpg

            conn = await asyncpg.connect(dsn=s.pg_dsn, timeout=3)
            await conn.close()
            return True
        except Exception:  # noqa: BLE001
            return False

    if not asyncio.new_event_loop().run_until_complete(_reachable()):
        pytest.skip("Postgres not reachable; skipping PG integration tests.")

    port = int(os.environ.get("ITEST_PORT", "8099"))
    proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        ready = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            try:
                if httpx.get(f"{base}/healthz", timeout=1).status_code == 200:
                    ready = True
                    break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        if not ready:
            proc.terminate()
            pytest.skip("API server did not start; skipping PG integration tests.")
        with httpx.Client(base_url=base, timeout=10) as client:
            yield client
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            proc.kill()
