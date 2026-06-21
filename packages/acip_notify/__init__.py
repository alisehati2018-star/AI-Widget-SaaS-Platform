"""acip_notify — transactional email (Phase A).

Dependency-free: a console provider (dev default; logs the message) and an SMTP
provider (stdlib ``smtplib``). Sending is best-effort and never raises into the
request path — a delivery failure is logged, not propagated.
"""

from __future__ import annotations

from .mailer import send_email
from .templates import (
    contact_notification,
    invite_email,
    reset_email,
    verification_email,
)

__all__ = [
    "send_email",
    "verification_email",
    "reset_email",
    "invite_email",
    "contact_notification",
]
