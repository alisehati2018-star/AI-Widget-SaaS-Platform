"""Hermetic tests for the stdlib TOTP implementation (RFC 6238)."""

from __future__ import annotations

import base64

from acip_auth.totp import generate_totp_secret, otpauth_uri, totp_code, verify_totp

# RFC 6238 Appendix B reference secret: ASCII "12345678901234567890".
_RFC_SECRET = base64.b32encode(b"12345678901234567890").decode()


def test_rfc6238_reference_vectors():
    # Last 6 digits of the RFC's 8-digit SHA-1 vectors.
    assert totp_code(_RFC_SECRET, at=59) == "287082"
    assert totp_code(_RFC_SECRET, at=1111111109) == "081804"
    assert totp_code(_RFC_SECRET, at=1234567890) == "005924"
    assert totp_code(_RFC_SECRET, at=20000000000) == "353130"


def test_verify_accepts_adjacent_window_and_rejects_garbage():
    at = 1111111109.0
    code = totp_code(_RFC_SECRET, at=at)
    assert verify_totp(_RFC_SECRET, code, at=at)
    assert verify_totp(_RFC_SECRET, code, at=at + 30)   # one step of clock skew
    assert not verify_totp(_RFC_SECRET, code, at=at + 120)
    assert not verify_totp(_RFC_SECRET, "000000", at=at) or code == "000000"
    assert not verify_totp(_RFC_SECRET, "12345", at=at)     # wrong length
    assert not verify_totp(_RFC_SECRET, "abcdef", at=at)    # not digits


def test_generated_secret_roundtrips():
    secret = generate_totp_secret()
    assert len(secret) == 32  # 160 bits base32
    code = totp_code(secret)
    assert verify_totp(secret, code)


def test_otpauth_uri_shape():
    uri = otpauth_uri("ABC234", "ops@vitrin.ai")
    assert uri.startswith("otpauth://totp/Vitrin%20Admin%3Aops%40vitrin.ai?secret=ABC234")
    assert "issuer=Vitrin%20Admin" in uri and "digits=6" in uri and "period=30" in uri
