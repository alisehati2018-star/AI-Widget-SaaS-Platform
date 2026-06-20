"""AI Business Analyst — natural-language insight (M10: REQ-M10-003, §11.3).

The operator asks in plain Persian ("چرا فروش این هفته کم شد؟"); the analyst
maps the question to the right Elasticsearch aggregation, runs it, and narrates
the result **from the returned numbers only** — the same grounding discipline as
the shopper assistant. It reports figures, never invents them. Narration uses
the gateway LLM when available; otherwise a deterministic template.
"""

from __future__ import annotations

import json
import re
from typing import Any

from .aggregations import funnel, most_wanted, zero_result_terms
from .insight import why_summary

_ZERO_RE = re.compile(r"بدون نتیجه|نتیجه نداش|پیدا نشد|zero.?result", re.IGNORECASE)
_WANTED_RE = re.compile(r"پرفروش|محبوب|پرتقاضا|most.?wanted|popular", re.IGNORECASE)
_WHY_RE = re.compile(r"چرا|why|دلیل|علت", re.IGNORECASE)

_ANALYST_SYSTEM = (
    "You are a business analyst for this store. You are given ONLY computed "
    "metrics as JSON. Answer the question using these numbers only. Never invent "
    "figures; if the numbers do not answer the question, say so. Answer in Persian."
)


async def route_metric(question: str, es, tenant_id: str) -> dict[str, Any]:
    """Pick + run the aggregation that fits the question (grounding data)."""
    if _WHY_RE.search(question):
        return {"kind": "why", "data": await why_summary(es, tenant_id)}
    if _ZERO_RE.search(question):
        return {"kind": "zero_results", "data": await zero_result_terms(es, tenant_id)}
    if _WANTED_RE.search(question):
        return {"kind": "most_wanted", "data": await most_wanted(es, tenant_id)}
    return {"kind": "funnel", "data": await funnel(es, tenant_id)}


def _templated(metric: dict[str, Any]) -> str:
    kind, data = metric["kind"], metric["data"]
    if kind == "why":
        return str(data.get("headline", ""))
    if kind == "zero_results":
        top = ", ".join(d["term"] for d in data[:5])
        return f"پرتکرارترین جستجوهای بدون نتیجه: {top}" if top else "موردی یافت نشد."
    if kind == "most_wanted":
        top = ", ".join(d["term"] for d in data[:5])
        return f"پرتقاضاترین جستجوها: {top}" if top else "موردی یافت نشد."
    return f"قیف رفتار کاربران: {json.dumps(data, ensure_ascii=False)}"


async def analyze(question: str, es, tenant_id: str, *, providers=None) -> dict[str, Any]:
    """Answer an NL analytics question, grounded in computed metrics."""
    metric = await route_metric(question, es, tenant_id)
    if providers is None:
        return {"answer": _templated(metric), "grounding": metric, "narrated_by": "template"}
    messages = [
        {"role": "system", "content": _ANALYST_SYSTEM},
        {"role": "user", "content": f"داده‌ها: {json.dumps(metric['data'], ensure_ascii=False)}"
                                     f"\n\nسوال: {question}"},
    ]
    try:
        resp = await providers.generate(messages, prefer_local=True)
        return {"answer": resp.text, "grounding": metric, "narrated_by": "llm"}
    except Exception:  # noqa: BLE001 - grounded template fallback
        return {"answer": _templated(metric), "grounding": metric, "narrated_by": "template"}
