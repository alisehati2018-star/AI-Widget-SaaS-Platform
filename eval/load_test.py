"""Lightweight async load harness (Phase G, ES-free).

Hammers cheap, dependency-light endpoints (``/healthz``, ``/metrics``) to measure
throughput + latency percentiles without needing Elasticsearch or models. Use it
to sanity-check the API under concurrency; the full search/RAG load + SLO
validation runs later against the real Elasticsearch server.

Usage:
    python -m eval.load_test --url http://localhost:8000 --requests 2000 --concurrency 50
"""

from __future__ import annotations

import argparse
import asyncio
import time


async def _worker(client, url: str, n: int, lat: list[float], errors: list[int]) -> None:
    for _ in range(n):
        start = time.perf_counter()
        try:
            r = await client.get(url, timeout=10)
            if r.status_code >= 500:
                errors.append(1)
        except Exception:  # noqa: BLE001
            errors.append(1)
        lat.append((time.perf_counter() - start) * 1000.0)


def _pct(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(round(p / 100.0 * (len(s) - 1))))
    return s[idx]


async def run(base: str, path: str, total: int, concurrency: int) -> dict:
    import httpx

    per = max(1, total // concurrency)
    lat: list[float] = []
    errors: list[int] = []
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            *[_worker(client, f"{base}{path}", per, lat, errors) for _ in range(concurrency)]
        )
    elapsed = time.perf_counter() - started
    done = len(lat)
    return {
        "requests": done,
        "errors": len(errors),
        "elapsed_s": round(elapsed, 2),
        "rps": round(done / elapsed, 1) if elapsed else 0,
        "p50_ms": round(_pct(lat, 50), 1),
        "p95_ms": round(_pct(lat, 95), 1),
        "p99_ms": round(_pct(lat, 99), 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--path", default="/healthz")
    ap.add_argument("--requests", type=int, default=1000)
    ap.add_argument("--concurrency", type=int, default=50)
    args = ap.parse_args()
    result = asyncio.run(run(args.url, args.path, args.requests, args.concurrency))
    print(result)


if __name__ == "__main__":
    main()
