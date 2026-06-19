"""Golden-set relevance metrics (REQ-M12-009 / blueprint §20.1).

Pure, deterministic functions — the arbiter of every relevance decision
(NDCG@10 headline, precision@k, zero-result rate). Used by the CI relevance
gate. No external dependencies so it runs anywhere.
"""

from __future__ import annotations

import math
from collections.abc import Sequence


def dcg(relevances: Sequence[float], k: int) -> float:
    """Discounted cumulative gain over the first k graded results."""
    total = 0.0
    for i, rel in enumerate(relevances[:k]):
        total += (2**rel - 1) / math.log2(i + 2)
    return total


def ndcg_at_k(
    ranked_relevances: Sequence[float],
    ideal_relevances: Sequence[float],
    k: int = 10,
) -> float:
    """Normalised DCG@k.

    Args:
        ranked_relevances: graded relevance of results in the order returned.
        ideal_relevances: all available grades for the query (any order).
        k: cutoff (default 10 — the headline metric).
    """
    ideal = dcg(sorted(ideal_relevances, reverse=True), k)
    if ideal == 0.0:
        return 0.0
    return dcg(ranked_relevances, k) / ideal


def precision_at_k(
    ranked_relevances: Sequence[float], k: int = 10, threshold: float = 1.0
) -> float:
    """Fraction of the top-k results judged relevant (grade >= threshold)."""
    if k <= 0:
        return 0.0
    top = ranked_relevances[:k]
    if not top:
        return 0.0
    relevant = sum(1 for r in top if r >= threshold)
    return relevant / min(k, len(top))


def zero_result_rate(result_counts: Sequence[int]) -> float:
    """Share of queries that returned no results (blueprint target < 5%)."""
    if not result_counts:
        return 0.0
    empties = sum(1 for c in result_counts if c == 0)
    return empties / len(result_counts)
