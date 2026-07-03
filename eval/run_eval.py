"""Golden-set evaluation runner (Phase 0 harness, REQ-M12-009 / T-P0-011).

Loads a JSONL golden set, scores a results provider against it, and prints
NDCG@10 / precision@k / zero-result rate. Phase 0 provides the harness and a
pluggable `ResultsProvider`; the real search-backed provider arrives with M5
(Phase 1). A baseline (e.g. native search) is captured the same way.

Usage:
    python -m eval.run_eval --golden eval/golden_set/golden_set.example.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from eval.metrics import ndcg_at_k, precision_at_k, zero_result_rate


@dataclass
class GoldenQuery:
    query_id: str
    query: str
    category: str
    grades: dict[str, int]  # product_id -> grade


class ResultsProvider(Protocol):
    """Returns an ordered list of product_ids for a query."""

    def search(self, query: str) -> Sequence[str]: ...


class EmptyProvider:
    """Phase-0 placeholder: returns nothing. Replaced by the M5 search client."""

    def search(self, query: str) -> Sequence[str]:  # noqa: ARG002
        return []


def load_golden_set(path: Path) -> list[GoldenQuery]:
    queries: list[GoldenQuery] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        grades = {j["product_id"]: int(j["grade"]) for j in obj.get("judgements", [])}
        queries.append(
            GoldenQuery(
                query_id=obj["query_id"],
                query=obj["query"],
                category=obj.get("category", "unknown"),
                grades=grades,
            )
        )
    return queries


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round(0.95 * len(ordered))) - 1))
    return ordered[idx]


def evaluate(golden: list[GoldenQuery], provider: ResultsProvider, k: int = 10) -> dict[str, float]:
    import time

    ndcgs: list[float] = []
    precisions: list[float] = []
    counts: list[int] = []
    latencies_ms: list[float] = []
    for q in golden:
        started = time.perf_counter()
        ranked_ids = list(provider.search(q.query))
        latencies_ms.append((time.perf_counter() - started) * 1000)
        counts.append(len(ranked_ids))
        ranked_grades = [float(q.grades.get(pid, 0)) for pid in ranked_ids]
        ideal_grades = [float(g) for g in q.grades.values()]
        ndcgs.append(ndcg_at_k(ranked_grades, ideal_grades, k))
        precisions.append(precision_at_k(ranked_grades, k))
    n = max(len(golden), 1)
    return {
        f"ndcg@{k}": sum(ndcgs) / n,
        f"precision@{k}": sum(precisions) / n,
        "zero_result_rate": zero_result_rate(counts),
        "p95_latency_ms": _p95(latencies_ms),
        "num_queries": float(len(golden)),
    }


# Headline KPI targets (blueprint §1/§18) checked by --kpi.
KPI_TARGETS = {
    "ndcg@10": (">=", 0.80),
    "p95_latency_ms": ("<", 150.0),
    "zero_result_rate": ("<", 0.05),
}


def kpi_report(results: dict[str, float]) -> tuple[str, bool]:
    lines = ["", "KPI report:"]
    all_ok = True
    for metric, (op, target) in KPI_TARGETS.items():
        value = results.get(metric)
        if value is None:
            continue
        ok = value >= target if op == ">=" else value < target
        all_ok = all_ok and ok
        mark = "PASS" if ok else "FAIL"
        lines.append(f"  {mark}  {metric} = {value:.4g}  (target {op} {target})")
    return "\n".join(lines), all_ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the golden-set evaluation.")
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("-k", type=int, default=10)
    parser.add_argument(
        "--tenant",
        default=None,
        help="Tenant id to evaluate against a live ES cluster (M5). Omit for a dry run.",
    )
    parser.add_argument(
        "--kpi", action="store_true",
        help="Check results against the headline KPI targets (exit 1 on failure).",
    )
    args = parser.parse_args()

    golden = load_golden_set(args.golden)
    if args.tenant:
        # Live search backend (requires a reachable Elasticsearch cluster).
        from eval.es_provider import ESResultsProvider

        provider: ResultsProvider = ESResultsProvider(args.tenant, size=args.k)
    else:
        # Dry run with no backend (Phase-0 behaviour).
        provider = EmptyProvider()
    results = evaluate(golden, provider, k=args.k)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    if args.kpi:
        report, ok = kpi_report(results)
        print(report)
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
