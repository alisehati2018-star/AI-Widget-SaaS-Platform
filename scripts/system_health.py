"""Full-system health check for operators (and cron/monitoring).

Calls the API's deep-health endpoint and prints a per-component table;
exits 0 when every probed component is ok, 1 when degraded, 2 on
transport/auth failure — so it drops straight into cron or CI:

    python scripts/system_health.py
    API_BASE=https://vitrin.example.com ADMIN_TOKEN=... python scripts/system_health.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    base = os.environ.get("API_BASE", "http://127.0.0.1:8000").rstrip("/")
    token = os.environ.get("ADMIN_TOKEN", "")
    req = urllib.request.Request(
        f"{base}/admin/health/deep", headers={"x-admin-token": token}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            report = json.load(resp)
    except urllib.error.HTTPError as exc:
        print(f"system-health: HTTP {exc.code} from {base} — check ADMIN_TOKEN", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - report any transport failure
        print(f"system-health: cannot reach {base}: {exc}", file=sys.stderr)
        return 2

    status = report.get("status", "unknown")
    print(f"overall: {status}\n")
    print(f"{'component':<16}{'status':<16}{'latency':<10}detail")
    for c in report.get("components", []):
        lat = f"{c['latency_ms']}ms" if c.get("latency_ms") is not None else "-"
        detail = ", ".join(f"{k}={v}" for k, v in (c.get("detail") or {}).items() if v is not None)
        print(f"{c['component']:<16}{c['status']:<16}{lat:<10}{detail}")
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
