"""Fixtures for ES-gated integration tests.

These run only when an Elasticsearch cluster is reachable (CI service container
or local `docker compose`). They are skipped otherwise so the unit suite stays
hermetic.
"""

from __future__ import annotations

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
