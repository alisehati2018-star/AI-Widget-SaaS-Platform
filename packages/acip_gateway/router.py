"""The escalation ladder, made concrete (M6: REQ-M6-001/006, Appendix C).

A turn climbs only as far as it must: L1 exact cache → L2 semantic cache → rule/
FAQ → search-only → local-model RAG → frontier RAG — each step gated by budget
and stopping at the cheapest rung that answers well. Every answer is metered and
written back to cache. Generation is delegated (the assistant builds the
guardrailed prompt); the router owns cache, routing, budget, failover, metering.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from acip_cache.l1 import L1ExactCache
from acip_cache.l2 import L2SemanticCache
from acip_core.logging import get_logger

from .budget import RUNG_COST, BudgetGuard, Rung
from .classifier import Tier, classify
from .failover import ProviderChain

log = get_logger("gateway.router")

RetrieveFn = Callable[[str, str], Awaitable[list[dict[str, Any]]]]
BuildMessagesFn = Callable[[str, list[dict[str, Any]]], list[dict]]
EmbedFn = Callable[[str], Awaitable[list[float] | None]]
RuleFn = Callable[[str], str | None]


@dataclass
class TurnResult:
    answer: str
    rung: Rung
    tier: Tier | None = None
    cached: bool = False
    citations: list[dict[str, Any]] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0


class GatewayRouter:
    def __init__(
        self,
        *,
        l1: L1ExactCache | None = None,
        l2: L2SemanticCache | None = None,
        budget: BudgetGuard | None = None,
        providers: ProviderChain | None = None,
        meter: Callable[..., Awaitable[None]] | None = None,
    ) -> None:
        self._l1 = l1
        self._l2 = l2
        self._budget = budget
        self._providers = providers
        self._meter = meter

    async def _record(
        self, tenant_id: str, rung: Rung, result: TurnResult, cache_outcome: str
    ) -> None:
        cost = RUNG_COST.get(rung, 0.0)
        if self._budget is not None:
            await self._budget.charge(tenant_id, cost)
        if self._meter is not None:
            await self._meter(
                tenant_id,
                route="chat",
                rung=rung.value,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cache_outcome=cache_outcome,
                latency_ms=result.latency_ms,
                cost=cost,
            )

    async def answer_turn(
        self,
        tenant_id: str,
        query: str,
        *,
        data_version: int = 0,
        retrieve: RetrieveFn | None = None,
        build_messages: BuildMessagesFn | None = None,
        embed: EmbedFn | None = None,
        rule_match: RuleFn | None = None,
        max_tokens: int = 512,
    ) -> TurnResult:
        started = time.perf_counter()

        def _elapsed() -> int:
            return int((time.perf_counter() - started) * 1000)

        # 1) L1 exact cache.
        if self._l1 is not None:
            hit = await self._l1.get(tenant_id, query, data_version)
            if hit is not None:
                r = TurnResult(answer=hit["answer"], rung=Rung.CACHE, cached=True,
                               citations=hit.get("citations", []), latency_ms=_elapsed())
                await self._record(tenant_id, Rung.CACHE, r, "l1_hit")
                return r

        # 2) L2 semantic cache.
        query_vector: list[float] | None = None
        if self._l2 is not None and embed is not None:
            query_vector = await embed(query)
            if query_vector is not None:
                near = await self._l2.lookup(tenant_id, query_vector)
                if near is not None:
                    ans = near["answer"]
                    answer_text = ans["answer"] if isinstance(ans, dict) else ans
                    cites = ans.get("citations", []) if isinstance(ans, dict) else []
                    r = TurnResult(
                        answer=answer_text, rung=Rung.CACHE, cached=True,
                        citations=cites, latency_ms=_elapsed(),
                    )
                    await self._record(tenant_id, Rung.CACHE, r, "l2_hit")
                    return r

        # 3) Deterministic rule / FAQ.
        if rule_match is not None and (templated := rule_match(query)) is not None:
            r = TurnResult(answer=templated, rung=Rung.RULE, tier=Tier.RULE, latency_ms=_elapsed())
            await self._record(tenant_id, Rung.RULE, r, "miss")
            await self._store(tenant_id, query, data_version, query_vector, r)
            return r

        # 4) Classify + budget.
        tier = classify(query)
        budget = await self._budget.state(tenant_id) if self._budget else None
        local_only = bool(budget and budget.local_only)

        # 5) Retrieve grounding (always Elastic, never a model call).
        docs = await retrieve(tenant_id, query) if retrieve else []

        # 6) Route to the cheapest capable rung.
        if tier is Tier.SEARCH or build_messages is None or self._providers is None:
            r = TurnResult(answer=_search_answer(docs), rung=Rung.SEARCH, tier=Tier.SEARCH,
                           citations=docs[:5], latency_ms=_elapsed())
            await self._record(tenant_id, Rung.SEARCH, r, "miss")
            await self._store(tenant_id, query, data_version, query_vector, r)
            return r

        prefer_local = local_only or tier is Tier.SYNTHESIS
        rung = Rung.LOCAL if prefer_local else Rung.FRONTIER
        messages = build_messages(query, docs)
        try:
            resp = await self._providers.generate(
                messages, prefer_local=prefer_local, max_tokens=max_tokens
            )
            answer = resp.text
            tokens_in, tokens_out = resp.tokens_in, resp.tokens_out
        except Exception:  # noqa: BLE001 - generation down: degrade to search (REQ-M7-009)
            log.warning("router.generation_degraded")
            r = TurnResult(answer=_search_answer(docs), rung=Rung.SEARCH, tier=tier,
                           citations=docs[:5], latency_ms=_elapsed())
            await self._record(tenant_id, Rung.SEARCH, r, "degraded")
            return r

        r = TurnResult(answer=answer, rung=rung, tier=tier, citations=docs[:5],
                       tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=_elapsed())
        await self._record(tenant_id, rung, r, "miss")
        await self._store(tenant_id, query, data_version, query_vector, r)
        return r

    async def _store(self, tenant_id: str, query: str, data_version: int,
                     query_vector: list[float] | None, r: TurnResult) -> None:
        payload = {"answer": r.answer, "citations": r.citations}
        if self._l1 is not None:
            await self._l1.set(tenant_id, query, data_version, payload)
        if self._l2 is not None and query_vector is not None:
            await self._l2.store(tenant_id, query_vector, payload)


def _search_answer(docs: list[dict[str, Any]]) -> str:
    """Templated, grounded fallback that lists the top matches (no generation)."""
    if not docs:
        return "موردی یافت نشد."  # "No results found."
    titles = [str(d.get("title", "")).strip() for d in docs[:5] if d.get("title")]
    return "این محصولات را پیدا کردم:\n" + "\n".join(f"- {t}" for t in titles)
