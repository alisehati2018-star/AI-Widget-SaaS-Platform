"""Groundedness evaluation for the RAG assistant (KPI: ≥ 95%).

A turn counts as GROUNDED when the assistant either (a) refuses/asks for
clarification, or (b) answers WITH citations and every cited product actually
exists in the tenant's own index (verified directly against Elasticsearch).
An answer without citations, or citing a product the store doesn't have, is
ungrounded — that is exactly the hallucination the blueprint forbids.

Runs the real assistant pipeline in-process (gateway ladder + retrieval), so
it needs the same PG/Redis/ES environment as the API. The LLM is optional:
without one, answers come from the grounded template path.

Usage (repo root, after `scripts/seed_catalog.py`):
    PYTHONPATH=packages:services python -m eval.groundedness \
        --tenant <tenant_id> --golden eval/golden_set/golden_fa.jsonl [--limit 20]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from eval.run_eval import load_golden_set

# The assistant's honest "nothing found" answers (router `_search_answer` and
# the RAG fallback). No citations AND no claims — a refusal, not a
# hallucination, so it counts as grounded.
_NO_RESULT_MARKERS = ("موردی یافت نشد", "پاسخ دقیقی در داده‌های فروشگاه پیدا نکردم")


async def _doc_exists(es, tenant_id: str, product_id: str) -> bool:
    from acip_core.config import get_settings
    from acip_sync.ingest import doc_id

    try:
        return bool(
            await es.exists(index=get_settings().catalogue_alias,
                            id=doc_id(tenant_id, product_id))
        )
    except Exception:  # noqa: BLE001 - missing index counts as "doesn't exist"
        return False


async def run(tenant_id: str, golden_path: Path, limit: int) -> dict:
    from acip_core.clients import get_es_client
    from api.runtime import get_assistant

    assistant = get_assistant()
    es = get_es_client()
    queries = load_golden_set(golden_path)[:limit]

    grounded = 0
    details: list[dict] = []
    for gq in queries:
        turn = await assistant.answer(tenant_id, uuid.uuid4().hex, gq.query)
        citations = turn.get("citations") or []
        refused = bool(turn.get("refused"))
        if refused:
            ok = True
            reason = "refused"
        elif not citations:
            answer = str(turn.get("answer", ""))
            if any(marker in answer for marker in _NO_RESULT_MARKERS):
                ok = True
                reason = "no_results_honest"
            else:
                ok = False
                reason = "no_citations"
        else:
            checks = [
                await _doc_exists(es, tenant_id, str(c.get("product_id")))
                for c in citations
                if c.get("product_id")
            ]
            ok = bool(checks) and all(checks)
            reason = "cited_products_verified" if ok else "cited_unknown_product"
        grounded += int(ok)
        details.append({"query": gq.query, "grounded": ok, "reason": reason,
                        "citations": len(citations)})

    total = max(len(queries), 1)
    return {
        "groundedness": grounded / total,
        "grounded_turns": grounded,
        "total_turns": len(queries),
        "target": 0.95,
        "pass": (grounded / total) >= 0.95,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--golden", type=Path,
                        default=Path("eval/golden_set/golden_fa.jsonl"))
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    result = asyncio.run(run(args.tenant, args.golden, args.limit))
    details = result.pop("details")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    for d in details:
        mark = "PASS" if d["grounded"] else "FAIL"
        print(f"  {mark}  [{d['reason']}] ({d['citations']} citation(s))  {d['query']}")
    if not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
