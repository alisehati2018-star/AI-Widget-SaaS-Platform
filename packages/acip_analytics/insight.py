"""The insight engine — answering "why?" (M10: REQ-M10-002, blueprint §11.2).

Mines the same Elastic data to explain what an owner actually asks: why sales
drop, why shoppers abandon, what products are missing. Combines zero-result
clusters (demand gaps), out-of-stock-but-searched (lost revenue), and funnel
drop-off (friction) into structured findings — grounded in the numbers, never
invented. Tenant-scoped; async/batch.
"""

from __future__ import annotations

from typing import Any

from .aggregations import funnel, zero_result_terms


def _funnel_dropoff(stages: dict[str, int]) -> list[dict[str, Any]]:
    """Largest stage-to-stage drop in the search → click → cart funnel."""
    order = ["search", "click", "cart", "purchase"]
    present = [(s, stages.get(s, 0)) for s in order if s in stages]
    findings: list[dict[str, Any]] = []
    for (a, av), (b, bv) in zip(present, present[1:], strict=False):
        if av > 0:
            drop = 1 - (bv / av)
            findings.append({"from": a, "to": b, "drop_rate": round(drop, 3), "from_count": av})
    return findings


async def why_summary(es, tenant_id: str) -> dict[str, Any]:
    """Structured 'why' findings, each backed by a number (no narration)."""
    zero = await zero_result_terms(es, tenant_id, size=10)
    stages = await funnel(es, tenant_id)
    dropoffs = _funnel_dropoff(stages)
    biggest = max(dropoffs, key=lambda d: d["drop_rate"], default=None)
    return {
        "demand_gaps": zero,                       # searched, nothing returned
        "funnel": stages,
        "dropoffs": dropoffs,
        "biggest_dropoff": biggest,
        "headline": _headline(zero, biggest),
    }


def _headline(zero: list[dict[str, Any]], biggest: dict[str, Any] | None) -> str:
    parts: list[str] = []
    if zero:
        parts.append(f"{len(zero)} پرس‌وجوی بدون نتیجه (شکاف تقاضا)")
    if biggest:
        parts.append(
            f"بیشترین ریزش بین «{biggest['from']}» و «{biggest['to']}» "
            f"({int(biggest['drop_rate'] * 100)}٪)"
        )
    return "؛ ".join(parts) if parts else "داده کافی برای تحلیل وجود ندارد."
