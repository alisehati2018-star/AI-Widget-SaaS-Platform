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


def evaluate(golden: list[GoldenQuery], provider: ResultsProvider, k: int = 10) -> dict[str, float]:
    ndcgs: list[float] = []
    precisions: list[float] = []
    counts: list[int] = []
    for q in golden:
        ranked_ids = list(provider.search(q.query))
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
        "num_queries": float(len(golden)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the golden-set evaluation.")
    parser.add_argument("--golden", required=True, type=Path)
    parser.add_argument("-k", type=int, default=10)
    args = parser.parse_args()

    golden = load_golden_set(args.golden)
    # Phase 0: no search backend yet -> EmptyProvider. Swap in the M5 client later.
    results = evaluate(golden, EmptyProvider(), k=args.k)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
