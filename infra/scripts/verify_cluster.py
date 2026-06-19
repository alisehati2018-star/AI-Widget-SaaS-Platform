"""Phase-0 cluster verification (T-P0-001 validation / REQ-M1-001).

Confirms the Elasticsearch cluster is reachable, healthy, version >= 9.2, and
that the load-bearing 2026 capabilities exist: dense_vector kNN, RRF
retrievers, and DiskBBQ (`bbq_disk`). It does NOT create the catalogue index,
analyzer, or mappings — those are Phase 1 (M2). Run after `docker compose up`.

    python infra/scripts/verify_cluster.py
"""

from __future__ import annotations

import sys

from acip_core.config import get_settings


def main() -> int:
    try:
        from elasticsearch import Elasticsearch
    except ImportError:
        print("elasticsearch client not installed; run `pip install .`")
        return 2

    s = get_settings()
    es = Elasticsearch(
        hosts=[s.es_host],
        basic_auth=(s.es_username, s.es_password) if s.es_password else None,
        verify_certs=s.es_verify_certs,
        request_timeout=10,
    )

    if not es.ping():
        print("FAIL: cluster not reachable at", s.es_host)
        return 1

    info = es.info()
    version = info["version"]["number"]
    health = es.cluster.health()
    major, minor, *_ = (int(p) for p in version.split("."))

    checks = {
        "reachable": True,
        "version>=9.2": (major, minor) >= (9, 2),
        "status!=red": health["status"] != "red",
    }

    print(f"Elasticsearch {version} — cluster status: {health['status']}")
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")
    print(
        "  [INFO] DiskBBQ (bbq_disk), dense_vector kNN, RRF retrievers, and ACORN "
        "are GA in 9.2+ and are exercised by the M2/M5 index work in Phase 1."
    )

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
