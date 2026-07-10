"""DB-backed provider registry (multi-provider FinOps completion).

Loads the admin-managed `ai_providers` / `ai_models` / `ai_routes` /
`pricing_settings` tables into a small TTL cache, and hands the gateway:

* the ordered endpoint chain for a task ('chat', 'analyst'), rebuilt live so
  admin changes apply within the TTL — no process restart;
* the per-model price sheet for COGS accounting;
* the platform pricing config (credit value, margin, flat prices).

Everything degrades: with an empty registry (or PG down) the chain is exactly
the legacy env configuration (optional FRONTIER_* endpoint → local LLM_URL),
prices are absent, and pricing falls back to defaults — so an unconfigured
deployment behaves precisely as before this module existed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from acip_billing.pricing import ModelPrice, PricingConfig, parse_pricing_row
from acip_core.config import get_settings
from acip_core.logging import get_logger

from .failover import Endpoint
from .llm_client import LLMClient, LLMResponse
from .retry import call_with_retry

log = get_logger("gateway.registry")


@dataclass
class EmbeddingEndpoint:
    """One embedding provider in the `embedding` task chain. `wire` is
    derived from the provider's `is_local` flag: the platform's own local
    model always speaks the TEI `/embed` protocol; any admin-added vendor is
    assumed OpenAI-`/embeddings`-wire-compatible, same assumption `LLMClient`
    already makes for chat completions."""

    base_url: str
    api_key: str | None
    model: str
    dims: int | None
    is_local: bool
    wire: str
    max_retries: int = 0
    retry_backoff_ms: int = 250


@dataclass
class RegistrySnapshot:
    """One consistent read of the registry tables."""

    endpoints_by_task: dict[str, list[Endpoint]] = field(default_factory=dict)
    embedding_endpoints: list[EmbeddingEndpoint] = field(default_factory=list)
    prices: dict[tuple[str, str], ModelPrice] = field(default_factory=dict)
    pricing: PricingConfig = field(default_factory=PricingConfig)
    failover_enabled: bool = True
    loaded_at: float = 0.0


class _HasLocalFlag(Protocol):
    is_local: bool


_E = TypeVar("_E", bound=_HasLocalFlag)


def _apply_failover_toggle(chain: list[_E], enabled: bool) -> list[_E]:
    """When the global failover switch is off, only the primary endpoint is
    tried — EXCEPT the mandatory local terminal (REQ-M6-009) is always kept
    reachable as a last resort, so disabling failover never removes the
    platform's hard guarantee of never fully hard-depending on a vendor."""
    if enabled or len(chain) <= 1:
        return chain
    primary = chain[0]
    if primary.is_local:
        return [primary]
    local_tail = next((e for e in chain[1:] if e.is_local), None)
    return [primary, local_tail] if local_tail is not None else [primary]


def _env_endpoints() -> list[Endpoint]:
    """The legacy env chain: optional frontier → local terminal."""
    s = get_settings()
    endpoints: list[Endpoint] = []
    if s.frontier_enabled and s.frontier_url:
        endpoints.append(
            Endpoint(
                client=LLMClient(s.frontier_url, provider="frontier", api_key=s.frontier_api_key),
                model=s.frontier_model or s.llm_model,
                is_local=False,
            )
        )
    endpoints.append(
        Endpoint(client=LLMClient(s.llm_url, provider="local"), model=s.llm_model, is_local=True)
    )
    return endpoints


def _env_embedding_endpoints() -> list[EmbeddingEndpoint]:
    """The legacy env-configured single local embedding endpoint."""
    s = get_settings()
    return [
        EmbeddingEndpoint(
            base_url=s.embeddings_url, api_key=None, model=s.embedding_model,
            dims=s.embedding_dims, is_local=True, wire="tei",
        )
    ]


class ProviderRegistry:
    """TTL-cached view of the provider/pricing tables."""

    def __init__(self, pool_getter, ttl_seconds: float = 30.0) -> None:
        self._pool_getter = pool_getter
        self._ttl = ttl_seconds
        self._snap: RegistrySnapshot | None = None

    async def snapshot(self) -> RegistrySnapshot:
        snap = self._snap
        if snap is not None and (time.monotonic() - snap.loaded_at) < self._ttl:
            return snap
        try:
            snap = await self._load()
        except Exception as exc:  # noqa: BLE001 - PG down: keep stale or fall to env
            log.warning("registry.load_failed", error=str(exc))
            if self._snap is not None:
                return self._snap
            snap = RegistrySnapshot(loaded_at=time.monotonic())
        self._snap = snap
        return snap

    async def _load(self) -> RegistrySnapshot:
        pool = await self._pool_getter()
        async with pool.acquire() as conn:
            route_rows = await conn.fetch(
                "SELECT r.task, r.position, m.model, m.input_usd_per_1m, m.output_usd_per_1m, "
                "p.name AS provider, p.base_url, p.api_key, p.is_local, p.timeout_s, "
                "p.max_retries, p.retry_backoff_ms "
                "FROM ai_routes r "
                "JOIN ai_models m ON m.id = r.model_id AND m.enabled AND m.modality = 'chat' "
                "JOIN ai_providers p ON p.id = m.provider_id AND p.enabled "
                "ORDER BY r.task, r.position"
            )
            embed_rows = await conn.fetch(
                "SELECT r.position, m.model, m.dims, p.base_url, p.api_key, p.is_local, "
                "p.max_retries, p.retry_backoff_ms "
                "FROM ai_routes r "
                "JOIN ai_models m ON m.id = r.model_id AND m.enabled AND m.modality = 'embedding' "
                "JOIN ai_providers p ON p.id = m.provider_id AND p.enabled "
                "WHERE r.task = 'embedding' ORDER BY r.position"
            )
            price_rows = await conn.fetch(
                "SELECT p.name AS provider, m.model, m.input_usd_per_1m, m.output_usd_per_1m "
                "FROM ai_models m JOIN ai_providers p ON p.id = m.provider_id"
            )
            pricing_row = await conn.fetchrow("SELECT * FROM pricing_settings WHERE id")
            routing_row = await conn.fetchrow(
                "SELECT failover_enabled FROM ai_routing_settings WHERE id"
            )

        by_task: dict[str, list[Endpoint]] = {}
        for r in route_rows:
            by_task.setdefault(r["task"], []).append(
                Endpoint(
                    client=LLMClient(
                        r["base_url"],
                        provider=r["provider"],
                        api_key=r["api_key"] or None,
                        timeout=float(r["timeout_s"] or 30),
                    ),
                    model=r["model"],
                    is_local=bool(r["is_local"]),
                    max_retries=int(r["max_retries"] or 0),
                    retry_backoff_ms=int(r["retry_backoff_ms"] or 250),
                )
            )
        embedding_endpoints = [
            EmbeddingEndpoint(
                base_url=r["base_url"],
                api_key=r["api_key"] or None,
                model=r["model"],
                dims=r["dims"],
                is_local=bool(r["is_local"]),
                wire="tei" if r["is_local"] else "openai",
                max_retries=int(r["max_retries"] or 0),
                retry_backoff_ms=int(r["retry_backoff_ms"] or 250),
            )
            for r in embed_rows
        ]
        prices = {
            (r["provider"], r["model"]): ModelPrice(
                provider=r["provider"],
                model=r["model"],
                input_usd_per_1m=float(r["input_usd_per_1m"]),
                output_usd_per_1m=float(r["output_usd_per_1m"]),
            )
            for r in price_rows
        }
        return RegistrySnapshot(
            endpoints_by_task=by_task,
            embedding_endpoints=embedding_endpoints,
            prices=prices,
            pricing=parse_pricing_row(pricing_row),
            failover_enabled=bool(routing_row["failover_enabled"]) if routing_row else True,
            loaded_at=time.monotonic(),
        )

    async def endpoints(self, task: str = "chat") -> list[Endpoint]:
        """Ordered chain for a task; ALWAYS terminated by a local endpoint.

        DB endpoints come first (admin-configured priority). If the DB chain
        carries no local endpoint, the env local LLM is appended so the
        failover invariant (REQ-M6-009: never hard-depend on an external
        vendor) holds no matter what the admin configures.
        """
        snap = await self.snapshot()
        chain = list(snap.endpoints_by_task.get(task, []))
        if not chain:
            return _env_endpoints()
        if not chain[-1].is_local:
            local = [e for e in _env_endpoints() if e.is_local]
            chain.extend(local)
        return _apply_failover_toggle(chain, snap.failover_enabled)

    async def embedding_endpoints(self) -> list[EmbeddingEndpoint]:
        """Ordered chain for the `embedding` task; falls back to the single
        env-configured local model when unconfigured — same degrade-to-env
        pattern as `.endpoints()` for chat/analyst."""
        snap = await self.snapshot()
        chain = list(snap.embedding_endpoints) or _env_embedding_endpoints()
        return _apply_failover_toggle(chain, snap.failover_enabled)

    async def price_for(self, provider: str, model: str) -> ModelPrice | None:
        snap = await self.snapshot()
        return snap.prices.get((provider, model))

    async def pricing(self) -> PricingConfig:
        return (await self.snapshot()).pricing

    def invalidate(self) -> None:
        """Drop the cache so the next call reloads (used by admin writes)."""
        self._snap = None


class DynamicProviderChain:
    """ProviderChain-compatible facade over the registry: endpoints are
    re-resolved per call, so admin routing changes apply without restart."""

    def __init__(self, registry: ProviderRegistry, task: str = "chat") -> None:
        self._registry = registry
        self._task = task

    async def generate(
        self, messages: list[dict], *, prefer_local: bool = False, max_tokens: int = 512
    ) -> LLMResponse:
        endpoints = await self._registry.endpoints(self._task)
        chain = [e for e in endpoints if e.is_local] if prefer_local else endpoints
        last_exc: Exception | None = None
        for ep in chain:

            async def _call(ep: Endpoint = ep) -> LLMResponse:
                return await ep.client.chat(messages, ep.model, max_tokens=max_tokens)

            try:
                return await call_with_retry(
                    _call, max_retries=ep.max_retries, backoff_ms=ep.retry_backoff_ms
                )
            except Exception as exc:  # noqa: BLE001 - fail over to the next endpoint
                last_exc = exc
                log.warning(
                    "registry.endpoint_failed", model=ep.model, is_local=ep.is_local
                )
                continue
        raise RuntimeError(f"all providers failed; last error: {last_exc}")


def snapshot_summary(snap: RegistrySnapshot) -> dict[str, Any]:
    """Compact JSON-able view for the admin monitoring endpoint."""
    return {
        "tasks": {
            task: [
                {"provider": e.client.provider_name, "model": e.model, "is_local": e.is_local}
                for e in eps
            ]
            for task, eps in snap.endpoints_by_task.items()
        },
        "models_priced": len(snap.prices),
    }
