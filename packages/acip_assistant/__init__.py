"""ACIP Assistant (M7) — grounded, guarded RAG shopping assistant.

Answers strictly from the tenant's own catalogue and pages: scope-locked prompt,
delimited untrusted context (injection defence), output guardrail with
search-fallback, two-tier conversational memory, and an audited agent-tool
interface (money-moving tools disabled until GA+).
"""

from .guardrails import SYSTEM_PROMPT, build_messages, is_grounded, passes_input_guardrail
from .memory import LongTermMemory, SessionMemory
from .rag import RagAssistant
from .tools import ToolRegistry, ToolSpec, default_registry

__all__ = [
    "RagAssistant",
    "SessionMemory",
    "LongTermMemory",
    "ToolRegistry",
    "ToolSpec",
    "default_registry",
    "build_messages",
    "is_grounded",
    "passes_input_guardrail",
    "SYSTEM_PROMPT",
]
