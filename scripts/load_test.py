"""Load test for the Vitrin API (Phase 9 acceptance).

Fires N concurrent shoppers at an endpoint and reports throughput + latency
percentiles against the blueprint targets (search p95 < 150 ms, p99 < 300 ms —
measured WITH a live ES; without one this still load-tests the HTTP path).

Usage (repo root):
    PYTHONPATH=packages:services python scripts/load_test.py \
        --url http://localhost:8000/v1/search --key <WIDGET_KEY> \
        --concurrency 20 --requests 500 --query "گوشی سامسونگ"

    python scripts/load_test.py --url http://localhost:8000/healthz   # no key

Windows PowerShell:
    $env:PYTHONPATH = "packages;services"
    python scripts/load_test.py --url http://localhost:8000/v1/search --key KEY
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time

import httpx


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(p / 100 * len(ordered)) - 1))
    return ordered[idx]


async def _run(url: str, key: str | None, query: str, concurrency: int, total: int) -> dict:
    latencies: list[float] = []
    statuses: dict[int, int] = {}
    sem = asyncio.Semaphore(concurrency)
    headers = {"content-type": "application/json"}
    if key:
        headers["x-api-key"] = key
    is_post = url.rstrip("/").endswith(("/search", "/chat"))

    async with httpx.AsyncClient(timeout=30) as client:

        async def one(i: int) -> None:
            async with sem:
                started = time.perf_counter()
                try:
                    if is_post:
                        body = {"query": query} if "search" in url else {"message": query}
                        r = await client.post(url, headers=headers, json=body)
                    else:
                        r = await client.get(url, headers=headers)
                    status = r.status_code
                except Exception:  # noqa: BLE001 - connection error counts as 0
                    status = 0
                latencies.append((time.perf_counter() - started) * 1000)
                statuses[status] = statuses.get(status, 0) + 1

        wall_start = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(total)))
        wall = time.perf_counter() - wall_start

    return {
        "url": url,
        "requests": total,
        "concurrency": concurrency,
        "wall_seconds": round(wall, 2),
        "rps": round(total / wall, 1) if wall else 0.0,
        "statuses": statuses,
        "latency_ms": {
            "p50": round(_pct(latencies, 50), 1),
            "p95": round(_pct(latencies, 95), 1),
            "p99": round(_pct(latencies, 99), 1),
            "max": round(max(latencies), 1) if latencies else 0.0,
        },
        "targets": {"search_p95_ms": 150, "search_p99_ms": 300},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8000/v1/search")
    parser.add_argument("--key", default=None, help="widget api key (for /v1/*)")
    parser.add_argument("--query", default="گوشی سامسونگ")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=500)
    args = parser.parse_args()

    result = asyncio.run(_run(args.url, args.key, args.query, args.concurrency, args.requests))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
