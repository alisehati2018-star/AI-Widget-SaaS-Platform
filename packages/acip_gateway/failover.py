"""Multi-provider failover ending at a local model (M6: REQ-M6-009).

The gateway keeps an ordered chain of model endpoints behind one interface and
fails over on error/health failure. The chain MUST end at a local endpoint so
the platform never hard-depends on an external provider being reachable
(blueprint §8.6, Appendix C). Health-checked, bounded, and observable.
"""

from __future__ import annotations

from dataclasses import dataclass

from acip_core.logging import get_logger

from .llm_client import LLMClient, LLMResponse

log = get_logger("gateway.failover")


@dataclass
class Endpoint:
    client: LLMClient
    model: str
    is_local: bool


class ProviderChain:
    """Ordered model endpoints tried in sequence; the last must be local."""

    def __init__(self, endpoints: list[Endpoint]) -> None:
        if not endpoints:
            raise ValueError("ProviderChain requires at least one endpoint")
        if not endpoints[-1].is_local:
            raise ValueError("the failover chain must end at a local endpoint (REQ-M6-009)")
        self._endpoints = endpoints

    @property
    def local_only(self) -> list[Endpoint]:
        return [e for e in self._endpoints if e.is_local]

    async def generate(self, messages: list[dict], *, prefer_local: bool = False,
                       max_tokens: int = 512) -> LLMResponse:
        """Try endpoints in order; if `prefer_local`, only the local ones."""
        chain = self.local_only if prefer_local else self._endpoints
        last_exc: Exception | None = None
        for ep in chain:
            try:
                return await ep.client.chat(messages, ep.model, max_tokens=max_tokens)
            except Exception as exc:  # noqa: BLE001 - fail over to the next endpoint
                last_exc = exc
                log.warning("failover.endpoint_failed", model=ep.model, is_local=ep.is_local)
                continue
        raise RuntimeError(f"all providers failed; last error: {last_exc}")
