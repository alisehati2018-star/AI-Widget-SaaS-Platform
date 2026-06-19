"""Unit tests for the RAG assistant (M7): guardrails, tools, pipeline."""

from __future__ import annotations

from acip_assistant.guardrails import (
    SYSTEM_PROMPT,
    build_messages,
    is_grounded,
    passes_input_guardrail,
)
from acip_assistant.rag import RagAssistant
from acip_assistant.tools import default_registry
from acip_cache.l1 import L1ExactCache
from acip_gateway.budget import BudgetGuard
from acip_gateway.failover import Endpoint, ProviderChain
from acip_gateway.llm_client import LLMResponse
from acip_gateway.router import GatewayRouter

from tests.test_gateway import FakeRedis


class FakeLLM:
    def __init__(self, text):
        self._text = text
        self._provider = "local"

    async def chat(self, messages, model, *, max_tokens=512, temperature=0.2):
        return LLMResponse(text=self._text, model=model, provider="local")


# --- guardrails ---

def test_build_messages_scope_locked_and_delimited():
    msgs = build_messages("قیمت گوشی؟", [{"title": "گوشی", "product_id": "1"}])
    assert msgs[0]["role"] == "system" and SYSTEM_PROMPT in msgs[0]["content"]
    assert "<<<STORE_DATA>>>" in msgs[1]["content"]


def test_input_guardrail():
    assert passes_input_guardrail("سلام") is True
    assert passes_input_guardrail("") is False
    assert passes_input_guardrail("x" * 5000) is False


def test_is_grounded():
    assert is_grounded("یک پاسخ", [{"title": "t"}]) is True       # has context
    assert is_grounded("نمی‌دانم", []) is True                    # refusal w/o context ok
    assert is_grounded("قطعا بله", []) is False                   # claim w/o context -> ungrounded
    assert is_grounded("", [{"title": "t"}]) is False             # empty -> ungrounded


# --- agent tools (money-moving disabled until GA+) ---

async def test_money_moving_tools_disabled():
    reg = default_registry()
    out = await reg.invoke("create_payment_link", "t1", {"amount": 100})
    assert out["error"] == "tool_disabled"
    assert reg.audit and reg.audit[-1]["tool"] == "create_payment_link"


async def test_safe_tool_enabled():
    reg = default_registry()
    out = await reg.invoke("check_stock", "t1", {"product_id": "1"})
    assert "error" not in out


# --- pipeline ---

async def _retrieve(_tenant, _query):
    return [{"title": "کفش ورزشی", "product_id": "10"}]


def _build_messages(query, docs):
    return build_messages(query, docs)


async def test_assistant_answers_grounded_turn():
    r = FakeRedis()
    router = GatewayRouter(
        l1=L1ExactCache(r),
        budget=BudgetGuard(r),
        providers=ProviderChain([Endpoint(FakeLLM("کفش‌های ورزشی موجود است."), "m", is_local=True)]),
    )
    assistant = RagAssistant(router, retrieve=_retrieve)
    out = await assistant.answer("t1", "sess1", "کفش ورزشی دارید؟")
    assert out["answer"]
    assert out["rung"] in ("local", "search", "rule")
    assert "session_id" not in out  # session id is added by the API layer


async def test_assistant_rejects_empty_input():
    router = GatewayRouter(providers=ProviderChain([Endpoint(FakeLLM("x"), "m", is_local=True)]))
    assistant = RagAssistant(router, retrieve=_retrieve)
    out = await assistant.answer("t1", "s", "   ")
    assert out["refused"] is True
