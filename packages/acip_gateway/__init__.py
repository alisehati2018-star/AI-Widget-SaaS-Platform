"""ACIP AI Gateway (M6) — Cache · Route · Compress.

The thin layer every model call traverses: an escalation ladder that stops at
the cheapest rung that can answer well (Appendix C), per-tenant budget caps and
kill switches, multi-provider failover ending at a local model, and per-call
usage metering. Built on the Phase-1 cache foundation (`acip_cache`).
"""

from .budget import BudgetGuard, Rung
from .classifier import Tier, classify
from .compress import build_context, compress_messages
from .failover import ProviderChain
from .llm_client import LLMClient, LLMResponse
from .router import GatewayRouter, TurnResult

__all__ = [
    "GatewayRouter",
    "TurnResult",
    "BudgetGuard",
    "Rung",
    "Tier",
    "classify",
    "ProviderChain",
    "LLMClient",
    "LLMResponse",
    "build_context",
    "compress_messages",
]
