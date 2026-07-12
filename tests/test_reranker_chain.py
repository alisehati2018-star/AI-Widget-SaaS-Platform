"""Unit tests for the registry-routed application-side reranker chain."""

from __future__ import annotations

from acip_gateway.registry import ProviderRegistry, RegistrySnapshot, RerankEndpoint
from acip_search.reranker import ChainedReranker
from acip_search.retrieval import SearchService


def _ep(base: str, *, is_local: bool = False, retries: int = 0) -> RerankEndpoint:
    return RerankEndpoint(
        base_url=base, api_key="k" if not is_local else None, model="rr-1",
        is_local=is_local, wire="tei" if is_local else "cohere",
        max_retries=retries, retry_backoff_ms=1,
    )


def _registry_with(endpoints: list[RerankEndpoint]) -> ProviderRegistry:
    reg = ProviderRegistry(pool_getter=None)
    snap = RegistrySnapshot(rerank_endpoints=endpoints, loaded_at=0.0)

    async def fake_snapshot():
        return snap

    reg.snapshot = fake_snapshot  # type: ignore[method-assign]
    return reg


async def test_has_chain_reflects_admin_binding_not_env(monkeypatch):
    # Env reranker configured but NO admin binding → has_chain is False, so
    # existing env-only deployments keep ES-side/off behavior untouched.
    monkeypatch.setenv("RERANKER_URL", "http://tei:8081")
    rr = ChainedReranker(_registry_with([]))
    assert await rr.has_chain() is False
    rr2 = ChainedReranker(_registry_with([_ep("http://x")]))
    assert await rr2.has_chain() is True


async def test_rerank_fails_over_and_degrades_to_identity(monkeypatch):
    calls: list[str] = []

    async def fake_call(**kwargs):
        calls.append(kwargs["base_url"])
        raise RuntimeError("down")

    import acip_search.reranker as mod

    monkeypatch.setattr(mod, "_rerank_call", fake_call)
    rr = ChainedReranker(_registry_with([_ep("http://a"), _ep("http://b")]))
    order = await rr.rerank("q", ["d1", "d2", "d3"])
    assert order == [0, 1, 2]  # identity degrade (REQ-M5-009)
    assert calls == ["http://a", "http://b"]  # tried the whole chain in order


async def test_rerank_uses_first_healthy_endpoint(monkeypatch):
    async def fake_call(**kwargs):
        if kwargs["base_url"] == "http://a":
            raise RuntimeError("down")
        return [2, 0, 1]

    import acip_search.reranker as mod

    monkeypatch.setattr(mod, "_rerank_call", fake_call)
    rr = ChainedReranker(_registry_with([_ep("http://a"), _ep("http://b")]))
    assert await rr.rerank("q", ["d1", "d2", "d3"]) == [2, 0, 1]


class _FakeES:
    def __init__(self) -> None:
        self.last_body = None

    async def search(self, *, index, body):
        self.last_body = body
        return {"hits": {"hits": [
            {"_source": {"title": "A"}, "_score": 3.0},
            {"_source": {"title": "B"}, "_score": 2.0},
            {"_source": {"title": "C"}, "_score": 1.0},
        ]}}


class _FakeChainReranker:
    def __init__(self, bound: bool) -> None:
        self._bound = bound
        self.called_with: list[str] | None = None

    async def has_chain(self) -> bool:
        return self._bound

    async def rerank(self, query, docs, top_n=None):
        self.called_with = docs
        return [2, 0, 1]


async def test_search_applies_admin_bound_rerank_order():
    es = _FakeES()
    rr = _FakeChainReranker(bound=True)
    svc = SearchService(es, reranker=rr)
    out = await svc.search("t1", "کفش")
    assert [r["title"] for r in out["results"]] == ["C", "A", "B"]
    assert rr.called_with == ["A", "B", "C"]
    # App-side rerank must NOT also request the ES-side reranker.
    assert "text_similarity" not in str(es.last_body)


async def test_search_untouched_when_no_chain_bound():
    es = _FakeES()
    rr = _FakeChainReranker(bound=False)
    svc = SearchService(es, reranker=rr)
    out = await svc.search("t1", "کفش")
    assert [r["title"] for r in out["results"]] == ["A", "B", "C"]
    assert rr.called_with is None
