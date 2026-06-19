"""Lead generation (M10: REQ-M10-004, blueprint §11.4).

In-conversation email/phone capture, intent detection, and abandoned-chat
signalling. PII is minimised and stored tenant-scoped in the control plane
(`leads` table). Intent detection is a cheap heuristic; it can be upgraded to a
model score without changing the interface.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from acip_core.logging import get_logger

log = get_logger("analytics.leads")

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Iran mobile or generic 10-13 digit numbers (Persian or ASCII digits).
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s-]{8,14}\d)")
_INTENT_WORDS = re.compile(
    r"\b(buy|order|price|discount|خرید|سفارش|قیمت|تخفیف|بخرم|می‌خوام)\b", re.IGNORECASE
)


@dataclass
class LeadSignal:
    email: str | None
    phone: str | None
    has_intent: bool

    @property
    def is_lead(self) -> bool:
        return bool(self.email or self.phone)


def detect_lead(message: str) -> LeadSignal:
    """Extract a lead signal from a shopper message (no I/O)."""
    email = m.group(0) if (m := _EMAIL_RE.search(message)) else None
    phone = m.group(0).strip() if (m := _PHONE_RE.search(message)) else None
    return LeadSignal(email=email, phone=phone, has_intent=bool(_INTENT_WORDS.search(message)))


async def capture_lead(pg_pool, tenant_id: str, signal: LeadSignal, source: str = "chat") -> bool:
    """Persist a captured lead (tenant-scoped). Best-effort; never breaks chat."""
    if pg_pool is None or not signal.is_lead:
        return False
    try:
        async with pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO leads (tenant_id, email, phone, has_intent, source)
                VALUES ($1, $2, $3, $4, $5)
                """,
                tenant_id, signal.email, signal.phone, signal.has_intent, source,
            )
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("leads.capture_failed", error=str(exc))
        return False
