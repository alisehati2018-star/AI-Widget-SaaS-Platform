"""The RAG assistant pipeline (M7: REQ-M7-001, blueprint §7.1).

Orchestrates the fixed, observable pipeline:
  understand → cache check → retrieve → rerank → compress → generate →
  guardrail → stream + cache.
Cache/route/budget/metering live in the gateway `GatewayRouter`; this module
owns the assistant concerns: input guardrail, memory, prompt construction
(scope-lock + delimited untrusted context), output guardrail, and the
search-fallback when generation is unavailable or ungrounded (REQ-M7-009).
"""

from __future__ import annotations

from typing import Any

from acip_core.logging import get_logger
from acip_gateway.budget import Rung
from acip_gateway.router import GatewayRouter, TurnResult

from .guardrails import build_messages, is_grounded, passes_input_guardrail
from .memory import SessionMemory

log = get_logger("assistant.rag")


class RagAssistant:
    def __init__(
        self,
        router: GatewayRouter,
        *,
        retrieve,            # async (tenant_id, query) -> list[docs]
        embed=None,          # async (text) -> vector | None
        session_memory: SessionMemory | None = None,
        data_version=None,   # async (tenant_id) -> int
        rule_match=None,     # (query) -> str | None
    ) -> None:
        self._router = router
        self._retrieve = retrieve
        self._embed = embed
        self._mem = session_memory
        self._data_version = data_version
        self._rule_match = rule_match

    async def answer(self, tenant_id: str, session_id: str, message: str) -> dict[str, Any]:
        if not passes_input_guardrail(message):
            return {"answer": "لطفاً سوال خود را کوتاه‌تر بپرسید.", "rung": "rule",
                    "citations": [], "refused": True}

        if self._mem is not None:
            await self._mem.append(tenant_id, session_id, "user", message)

        dv = await self._data_version(tenant_id) if self._data_version else 0

        result: TurnResult = await self._router.answer_turn(
            tenant_id,
            message,
            data_version=dv,
            retrieve=self._retrieve,
            build_messages=build_messages,
            embed=self._embed,
            rule_match=self._rule_match,
        )

        # Output guardrail: ungrounded synthesis falls back to ranked search.
        if result.rung in (Rung.LOCAL, Rung.FRONTIER) and not is_grounded(
            result.answer, result.citations
        ):
            log.warning("assistant.ungrounded_fallback")
            result.answer = _fallback_text(result.citations)
            result.rung = Rung.SEARCH

        if self._mem is not None:
            await self._mem.append(tenant_id, session_id, "assistant", result.answer)

        return {
            "answer": result.answer,
            "rung": result.rung.value if hasattr(result.rung, "value") else str(result.rung),
            "citations": result.citations,
            "cached": result.cached,
            "latency_ms": result.latency_ms,
        }


def _fallback_text(docs: list[dict[str, Any]]) -> str:
    if not docs:
        return "متأسفم، پاسخ دقیقی در داده‌های فروشگاه پیدا نکردم."
    titles = [str(d.get("title", "")).strip() for d in docs[:5] if d.get("title")]
    return "این محصولات مرتبط را پیدا کردم:\n" + "\n".join(f"- {t}" for t in titles)
