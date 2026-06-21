"""Email delivery: console (dev) + SMTP (stdlib) providers."""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from acip_core.config import get_settings
from acip_core.logging import get_logger

log = get_logger("notify.email")


def _build(to: str, subject: str, text: str, html: str | None) -> EmailMessage:
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = s.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    return msg


def _send_smtp(msg: EmailMessage) -> None:
    s = get_settings()
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
        if s.smtp_starttls:
            server.starttls()
        if s.smtp_user:
            server.login(s.smtp_user, s.smtp_password)
        server.send_message(msg)


async def send_email(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send an email via the configured provider. Best-effort: returns False on
    failure (logged) and never raises into the caller."""
    s = get_settings()
    try:
        if s.email_provider == "smtp" and s.smtp_host:
            msg = _build(to, subject, text, html)
            await asyncio.to_thread(_send_smtp, msg)
            log.info("email.sent", to=to, subject=subject, provider="smtp")
            return True
        # Console provider (dev): log instead of sending.
        log.info("email.console", to=to, subject=subject, body=text)
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("email.failed", to=to, subject=subject, error=str(exc))
        return False
