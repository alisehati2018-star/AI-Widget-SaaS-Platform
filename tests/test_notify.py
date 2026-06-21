"""Phase A notifications — email templates + console provider (hermetic)."""

from __future__ import annotations

from acip_notify import (
    contact_notification,
    invite_email,
    reset_email,
    send_email,
    verification_email,
)


def test_templates_return_subject_text_html():
    for builder, args in (
        (verification_email, ("https://x/verify?token=abc",)),
        (reset_email, ("https://x/reset?token=abc",)),
        (invite_email, ("https://x/invite?token=abc", "Acme Shop")),
        (contact_notification, ("Sam", "sam@ex.com", "hello")),
    ):
        subject, text, html = builder(*args)
        assert subject and isinstance(subject, str)
        assert isinstance(text, str) and isinstance(html, str)
        assert "Vitrin" in html


def test_verification_link_embedded():
    link = "https://app/verify-email?token=tok123"
    _, text, html = verification_email(link)
    assert link in text and link in html


async def test_console_send_does_not_raise_and_reports_success():
    # Default provider is 'console' → logs and returns True without network.
    ok = await send_email("user@example.com", "Hi", "body", "<p>body</p>")
    assert ok is True
