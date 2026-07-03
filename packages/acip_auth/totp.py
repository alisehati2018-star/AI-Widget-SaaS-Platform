"""TOTP two-factor auth for platform admins (RFC 6238, stdlib only).

SHA-1 / 6 digits / 30-second steps — the profile every authenticator app
(Google Authenticator, Aegis, FreeOTP, 1Password …) uses by default. No new
dependency: HMAC comes from the standard library.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

STEP_SECONDS = 30
DIGITS = 6


def generate_totp_secret() -> str:
    """A new 160-bit base32 secret (the RFC 4226 recommended size)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def totp_code(secret: str, at: float | None = None) -> str:
    """The 6-digit code for the given (or current) unix time."""
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    counter = int((time.time() if at is None else at) // STEP_SECONDS)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10**DIGITS)).zfill(DIGITS)


def verify_totp(secret: str, code: str, *, window: int = 1, at: float | None = None) -> bool:
    """Constant-time check of the code against ±`window` time steps (clock skew)."""
    return verify_totp_step(secret, code, window=window, at=at) is not None


def verify_totp_step(
    secret: str, code: str, *, window: int = 1, at: float | None = None
) -> int | None:
    """Like ``verify_totp`` but returns the absolute time step that matched.

    Callers persist the matched step and reject codes at or before it — a
    sniffed code can then never be replayed, even inside the skew window.
    """
    code = code.strip().replace(" ", "")
    if not code.isdigit() or len(code) != DIGITS:
        return None
    now = time.time() if at is None else at
    matched: int | None = None
    for offset in range(-window, window + 1):
        ts = now + offset * STEP_SECONDS
        expected = totp_code(secret, at=ts)
        # No early exit: check every step so timing doesn't leak which matched.
        if hmac.compare_digest(expected, code):
            matched = int(ts // STEP_SECONDS)
    return matched


def otpauth_uri(secret: str, email: str, issuer: str = "Vitrin Admin") -> str:
    """The otpauth:// URI authenticator apps import (shown as text or QR)."""
    label = quote(f"{issuer}:{email}")
    return (
        f"otpauth://totp/{label}?secret={secret}"
        f"&issuer={quote(issuer)}&algorithm=SHA1&digits={DIGITS}&period={STEP_SECONDS}"
    )
