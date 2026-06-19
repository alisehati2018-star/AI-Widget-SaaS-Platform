"""Intent / difficulty classifier (M6: REQ-M6-015).

A lightweight, deterministic classifier (rules + heuristics) that labels each
turn so the router can send it to the cheapest rung that answers well. Kept
dependency-free and fast — it runs on every turn. An embedding/small-model
score can augment these rules later without changing the interface.
"""

from __future__ import annotations

import re
from enum import StrEnum

# Curated FAQ/rule intents — answerable from templates with no model (rung 1).
_RULE_PATTERNS = [
    r"return policy|بازگشت|مرجوع",
    r"shipping|ارسال|پست|تحویل",
    r"working hours|ساعت کاری|ساعات کار",
    r"warranty|گارانتی|ضمانت",
    r"contact|تماس|پشتیبانی",
]

# Browse/lookup intents — answerable by search results, no generation (rung 2).
_SEARCH_PATTERNS = [
    r"^\s*(do you have|show me|آیا|دارید|نشون بده|لیست)",
    r"price of|قیمت|چند",
]

_RULE_RE = re.compile("|".join(_RULE_PATTERNS), re.IGNORECASE)
_SEARCH_RE = re.compile("|".join(_SEARCH_PATTERNS), re.IGNORECASE)
# Cues that a turn is genuinely hard / needs careful synthesis (rung 4).
_HARD_RE = re.compile(
    r"\b(compare|difference|recommend|بهترین|مقایسه|فرق|پیشنهاد)\b", re.IGNORECASE
)


class Tier(StrEnum):
    RULE = "rule"          # templated FAQ answer
    SEARCH = "search"      # search results only
    SYNTHESIS = "synthesis"  # local-model RAG (workhorse)
    HARD = "hard"          # frontier-model RAG (small tail)


def classify(query: str) -> Tier:
    """Label a turn. Order matters: cheapest decidable intent wins."""
    q = query.strip()
    if not q:
        return Tier.SEARCH
    if _RULE_RE.search(q):
        return Tier.RULE
    if _HARD_RE.search(q):
        return Tier.HARD
    if _SEARCH_RE.search(q):
        return Tier.SEARCH
    return Tier.SYNTHESIS
