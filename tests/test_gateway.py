"""Unit tests for the AI gateway (M6): classifier, budget, failover, ladder."""

from __future__ import annotations

import pytest
from acip_cache.l1 import L1ExactCache
from acip_gateway.budget import BudgetGuard, Rung
from acip_gateway.classifier import Tier, classify
from acip_gateway.compress import build_context, compress_messages
from acip_gateway.failover import Endpoint, ProviderChain
from acip_gateway.llm_client import LLMResponse
from acip_gateway.router import GatewayRouter


class FakeRedis:
    """Minimal in-memory async Redis supporting the methods we use."""

    def __init__(self) -> None:
        self.kv: dict = {}

    async def get(self, k):
        return self.kv.get(k)

    async def set(self, k, v, ex=None):
        self.kv[k] = v

    async def delete(self, k):
        self.kv.pop(k, None)

    async def incr(self, k):
        self.kv[k] = int(self.kv.get(k, 0)) + 1
        return self.kv[k]

    async def incrbyfloat(self, k, amt):
        self.kv[k] = float(self.kv.get(k, 0.0)) + amt
        return self.kv[k]


class FakeLLM:
    def __init__(self, text: str = "پاسخ", provider: str = "local") -> None:
        self._text = text
        self._provider = provider

    async def chat(self, messages, model, *, max_tokens=512, temperature=0.2):
        return LLMResponse(text=self._text, model=model, provider=self._provider,
                           tokens_in=10, tokens_out=5)


def _msgs(query, docs):
    return [{"role": "system", "content": "s"}, {"role": "user", "content": query}]


async def _retrieve(_tenant, _query):
    return [{"title": "محصول ۱", "product_id": "1"}, {"title": "محصول ۲", "product_id": "2"}]


# --- classifier ---

def test_classify_tiers():
    assert classify("return policy") is Tier.RULE
    assert classify("do you have red shoes") is Tier.SEARCH
    assert classify("مقایسه کن این دو را") is Tier.HARD
    assert classify("یک متن معمولی") is Tier.SYNTHESIS


# --- budget / kill switch ---

async def test_budget_kill_switch_forces_local_only():
    r = FakeRedis()
    guard = BudgetGuard(r, default_cap=100.0)
    st = await guard.state("t1")
    assert st.local_only is False
    await guard.set_kill_switch("t1", True)
    assert (await guard.state("t1")).local_only is True


async def test_budget_hard_cap_forces_local_only():
    r = FakeRedis()
    guard = BudgetGuard(r, default_cap=1.0)
    await guard.charge("t1", 2.0)
    assert (await guard.state("t1")).local_only is True


# --- failover chain ---

def test_provider_chain_must_end_local():
    with pytest.raises(ValueError):
        ProviderChain([Endpoint(FakeLLM(provider="frontier"), "m", is_local=False)])


async def test_provider_chain_fails_over_to_local():
    class Boom:
        _provider = "frontier"

        async def chat(self, *a, **k):
            raise RuntimeError("down")

    chain = ProviderChain([
        Endpoint(Boom(), "f", is_local=False),
        Endpoint(FakeLLM("local-answer"), "l", is_local=True),
    ])
    resp = await chain.generate([{"role": "user", "content": "x"}])
    assert resp.text == "local-answer"


# --- compress ---

def test_build_context_delimits_untrusted_data():
    ctx = build_context([{"title": "t", "product_id": "1", "description": "d"}])
    assert "<<<STORE_DATA>>>" in ctx and "<<<END_STORE_DATA>>>" in ctx


def test_compress_messages_truncates():
    history = [{"role": "user", "content": str(i)} for i in range(20)]
    assert len(compress_messages(history, max_turns=6)) == 6


# --- escalation ladder ---

async def test_router_synthesis_then_l1_cache_hit():
    r = FakeRedis()
    router = GatewayRouter(
        l1=L1ExactCache(r),
        budget=BudgetGuard(r),
        providers=ProviderChain([Endpoint(FakeLLM("answer"), "m", is_local=True)]),
    )
    res1 = await router.answer_turn("t1", "یک سوال معمولی", retrieve=_retrieve,
                                    build_messages=_msgs)
    assert res1.rung is Rung.LOCAL and res1.cached is False
    res2 = await router.answer_turn("t1", "یک سوال معمولی", retrieve=_retrieve,
                                    build_messages=_msgs)
    assert res2.rung is Rung.CACHE and res2.cached is True


async def test_router_rule_rung():
    router = GatewayRouter(providers=ProviderChain([Endpoint(FakeLLM(), "m", is_local=True)]))
    res = await router.answer_turn("t1", "anything", retrieve=_retrieve, build_messages=_msgs,
                                   rule_match=lambda q: "templated")
    assert res.rung is Rung.RULE and res.answer == "templated"


async def test_router_search_tier_no_generation():
    router = GatewayRouter(providers=ProviderChain([Endpoint(FakeLLM(), "m", is_local=True)]))
    res = await router.answer_turn("t1", "do you have shoes", retrieve=_retrieve,
                                   build_messages=_msgs)
    assert res.rung is Rung.SEARCH and res.citations


async def test_router_budget_local_only_never_frontier():
    r = FakeRedis()
    guard = BudgetGuard(r)
    await guard.set_kill_switch("t1", True)
    router = GatewayRouter(
        budget=guard,
        providers=ProviderChain([
            Endpoint(FakeLLM("f"), "f", is_local=False),
            Endpoint(FakeLLM("local"), "l", is_local=True),
        ]),
    )
    # A "hard" query would normally hit frontier; budget forces local.
    res = await router.answer_turn("t1", "مقایسه کن", retrieve=_retrieve, build_messages=_msgs)
    assert res.rung is Rung.LOCAL and res.answer == "local"
