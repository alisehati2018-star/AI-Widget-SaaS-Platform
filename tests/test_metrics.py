"""Unit tests for the golden-set metrics (REQ-M12-008 unit layer)."""

from __future__ import annotations

import math

from eval.metrics import ndcg_at_k, precision_at_k, zero_result_rate


def test_ndcg_perfect_ranking_is_one():
    ranked = [3, 2, 1]
    ideal = [3, 2, 1]
    assert math.isclose(ndcg_at_k(ranked, ideal, k=10), 1.0)


def test_ndcg_reversed_ranking_is_less_than_one():
    ranked = [1, 2, 3]
    ideal = [3, 2, 1]
    score = ndcg_at_k(ranked, ideal, k=10)
    assert 0.0 < score < 1.0


def test_ndcg_empty_ideal_is_zero():
    assert ndcg_at_k([0, 0], [0, 0], k=10) == 0.0


def test_precision_at_k_counts_relevant():
    # 2 of top-4 are relevant (grade >= 1)
    assert math.isclose(precision_at_k([3, 0, 1, 0], k=4), 0.5)


def test_precision_at_k_empty():
    assert precision_at_k([], k=10) == 0.0


def test_zero_result_rate():
    # 1 empty out of 4 queries
    assert math.isclose(zero_result_rate([5, 0, 3, 2]), 0.25)


def test_zero_result_rate_no_queries():
    assert zero_result_rate([]) == 0.0
