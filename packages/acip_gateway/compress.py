"""COMPRESS — fewer tokens for the same answer (M6: REQ-M6-010).

Two levers from blueprint §8.4: (1) prune retrieval to the reranked top passages
and render them as compact, clearly-delimited context; (2) trim conversation
history to a bounded window (summaries replace verbatim replay). Retrieved store
content is wrapped as *untrusted data* (never instructions) — the prompt-side of
the injection defence (REQ-M7-005).
"""

from __future__ import annotations

from typing import Any

# Delimiters make it unambiguous to the model where untrusted store data starts
# and ends, so a malicious product description cannot pose as an instruction.
_DATA_OPEN = "<<<STORE_DATA>>>"
_DATA_CLOSE = "<<<END_STORE_DATA>>>"


def build_context(docs: list[dict[str, Any]], *, max_docs: int = 5, max_chars: int = 600) -> str:
    """Render the top-N retrieved products as compact, delimited context."""
    lines: list[str] = [_DATA_OPEN]
    for i, d in enumerate(docs[:max_docs], start=1):
        title = str(d.get("title", "")).strip()
        brand = str(d.get("brand", "")).strip()
        price = d.get("price")
        desc = str(d.get("description", "")).strip()[:max_chars]
        pid = d.get("product_id", "")
        parts = [f"[{i}] id={pid}"]
        if title:
            parts.append(f"title={title}")
        if brand:
            parts.append(f"brand={brand}")
        if price is not None:
            parts.append(f"price={price}")
        if desc:
            parts.append(f"desc={desc}")
        lines.append(" | ".join(parts))
    lines.append(_DATA_CLOSE)
    return "\n".join(lines)


def compress_messages(history: list[dict], *, max_turns: int = 6) -> list[dict]:
    """Keep only the most recent turns to bound prompt size and cost."""
    if len(history) <= max_turns:
        return history
    return history[-max_turns:]
