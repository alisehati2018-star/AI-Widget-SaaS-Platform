"""Plain + HTML bodies for transactional emails.

Kept deliberately simple (inline HTML, no template engine). Each builder returns
``(subject, text, html)``.
"""

from __future__ import annotations

_BRAND = "Vitrin"


def _wrap(
    title: str, body_html: str, cta_label: str | None = None, cta_url: str | None = None
) -> str:
    button = (
        f'<p><a href="{cta_url}" style="display:inline-block;background:#7c5cff;'
        f'color:#0a0b14;font-weight:600;padding:10px 18px;border-radius:8px;'
        f'text-decoration:none">{cta_label}</a></p>'
        if cta_label and cta_url
        else ""
    )
    return (
        f'<div style="font-family:system-ui,sans-serif;max-width:520px;margin:auto">'
        f'<h2 style="color:#7c5cff">{_BRAND}</h2><h3>{title}</h3>{body_html}{button}'
        f'<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
        f'<small style="color:#888">{_BRAND} — AI Commerce Intelligence Platform</small></div>'
    )


def verification_email(link: str) -> tuple[str, str, str]:
    subject = f"Verify your {_BRAND} email"
    text = (
        f"Welcome to {_BRAND}!\n\nConfirm your email to activate your account:\n{link}\n\n"
        "This link expires in 24 hours. If you didn't sign up, ignore this email."
    )
    html = _wrap("Confirm your email", "<p>Confirm your email to activate your account.</p>",
                 "Verify email", link)
    return subject, text, html


def reset_email(link: str) -> tuple[str, str, str]:
    subject = f"Reset your {_BRAND} password"
    text = (
        f"We received a request to reset your {_BRAND} password:\n{link}\n\n"
        "This link expires in 1 hour. If you didn't request it, ignore this email."
    )
    html = _wrap("Reset your password", "<p>Click below to choose a new password.</p>",
                 "Reset password", link)
    return subject, text, html


def invite_email(link: str, store_name: str) -> tuple[str, str, str]:
    subject = f"You've been invited to {store_name} on {_BRAND}"
    text = (
        f"You've been invited to join {store_name} on {_BRAND}.\n\n"
        f"Set your password to accept:\n{link}\n\nThis link expires in 7 days."
    )
    html = _wrap(f"Join {store_name}", f"<p>You've been invited to join <b>{store_name}</b>.</p>",
                 "Accept invitation", link)
    return subject, text, html


def contact_notification(name: str, email: str, message: str) -> tuple[str, str, str]:
    subject = f"[{_BRAND}] New contact message from {name}"
    text = f"From: {name} <{email}>\n\n{message}"
    html = _wrap("New contact message",
                 f"<p><b>{name}</b> &lt;{email}&gt;</p><p>{message}</p>")
    return subject, text, html
