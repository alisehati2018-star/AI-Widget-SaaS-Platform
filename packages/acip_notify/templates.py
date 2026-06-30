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


def _loc(locale: str | None) -> str:
    """Normalize a request locale to a supported email locale (fa/en)."""
    return "fa" if (locale or "").lower().startswith("fa") else "en"


def verification_email(link: str, locale: str | None = "en") -> tuple[str, str, str]:
    if _loc(locale) == "fa":
        subject = f"ایمیل {_BRAND} خود را تأیید کنید"
        text = (
            f"به {_BRAND} خوش آمدید!\n\nبرای فعال‌سازی حسابتان ایمیل خود را تأیید کنید:\n{link}\n\n"
            "این لینک تا ۲۴ ساعت معتبر است. اگر شما ثبت‌نام نکرده‌اید، این ایمیل را نادیده بگیرید."
        )
        html = _wrap("تأیید ایمیل", "<p>برای فعال‌سازی حساب، ایمیل خود را تأیید کنید.</p>",
                     "تأیید ایمیل", link)
        return subject, text, html
    subject = f"Verify your {_BRAND} email"
    text = (
        f"Welcome to {_BRAND}!\n\nConfirm your email to activate your account:\n{link}\n\n"
        "This link expires in 24 hours. If you didn't sign up, ignore this email."
    )
    html = _wrap("Confirm your email", "<p>Confirm your email to activate your account.</p>",
                 "Verify email", link)
    return subject, text, html


def reset_email(link: str, locale: str | None = "en") -> tuple[str, str, str]:
    if _loc(locale) == "fa":
        subject = f"بازنشانی گذرواژهٔ {_BRAND}"
        text = (
            f"درخواست بازنشانی گذرواژهٔ {_BRAND} شما را دریافت کردیم:\n{link}\n\n"
            "این لینک تا ۱ ساعت معتبر است. اگر شما درخواست نداده‌اید، این ایمیل را نادیده بگیرید."
        )
        html = _wrap("بازنشانی گذرواژه", "<p>برای انتخاب گذرواژهٔ جدید روی دکمه بزنید.</p>",
                     "بازنشانی گذرواژه", link)
        return subject, text, html
    subject = f"Reset your {_BRAND} password"
    text = (
        f"We received a request to reset your {_BRAND} password:\n{link}\n\n"
        "This link expires in 1 hour. If you didn't request it, ignore this email."
    )
    html = _wrap("Reset your password", "<p>Click below to choose a new password.</p>",
                 "Reset password", link)
    return subject, text, html


def invite_email(link: str, store_name: str, locale: str | None = "en") -> tuple[str, str, str]:
    if _loc(locale) == "fa":
        subject = f"به {store_name} در {_BRAND} دعوت شده‌اید"
        text = (
            f"شما به پیوستن به {store_name} در {_BRAND} دعوت شده‌اید.\n\n"
            f"برای پذیرش، گذرواژهٔ خود را تنظیم کنید:\n{link}\n\nاین لینک تا ۷ روز معتبر است."
        )
        html = _wrap(f"پیوستن به {store_name}",
                     f"<p>شما به پیوستن به <b>{store_name}</b> دعوت شده‌اید.</p>",
                     "پذیرش دعوت", link)
        return subject, text, html
    subject = f"You've been invited to {store_name} on {_BRAND}"
    text = (
        f"You've been invited to join {store_name} on {_BRAND}.\n\n"
        f"Set your password to accept:\n{link}\n\nThis link expires in 7 days."
    )
    html = _wrap(f"Join {store_name}", f"<p>You've been invited to join <b>{store_name}</b>.</p>",
                 "Accept invitation", link)
    return subject, text, html


def invoice_email(
    number: int, description: str, amount: float, currency: str
) -> tuple[str, str, str]:
    subject = f"{_BRAND} invoice #{number}"
    text = (
        f"Thanks for your payment.\n\nInvoice #{number}\n{description}\n"
        f"Amount: {currency} {amount:.2f}\n\nThis is your receipt."
    )
    html = _wrap(
        f"Invoice #{number}",
        f"<p>Thanks for your payment.</p><p>{description}<br><b>{currency} {amount:.2f}</b></p>",
    )
    return subject, text, html


def dunning_email(plan: str, amount: float, currency: str) -> tuple[str, str, str]:
    subject = f"Action needed: your {_BRAND} subscription payment is due"
    text = (
        f"Your {plan} subscription renewal ({currency} {amount:.2f}) is past due.\n\n"
        "Please complete payment to keep your store's AI features active."
    )
    html = _wrap(
        "Payment past due",
        f"<p>Your <b>{plan}</b> renewal ({currency} {amount:.2f}) is past due. "
        "Complete payment to keep your AI features active.</p>",
    )
    return subject, text, html


def contact_notification(name: str, email: str, message: str) -> tuple[str, str, str]:
    subject = f"[{_BRAND}] New contact message from {name}"
    text = f"From: {name} <{email}>\n\n{message}"
    html = _wrap("New contact message",
                 f"<p><b>{name}</b> &lt;{email}&gt;</p><p>{message}</p>")
    return subject, text, html
