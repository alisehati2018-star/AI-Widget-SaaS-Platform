"""Compact HS256 JWTs (stdlib): short-lived access + rotating refresh tokens.

A deliberately small, auditable JWT implementation (HMAC-SHA256) so the on-prem
deployment carries no native crypto dependency. Signatures are verified in
constant time and expiry is always enforced.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

ACCESS_TOKEN_TTL_SECONDS = 15 * 60  # 15 minutes
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
_ISSUER = "acip-auth"


class TokenError(Exception):
    """Base class for token problems."""


class ExpiredTokenError(TokenError):
    """The token's ``exp`` claim is in the past."""


class InvalidTokenError(TokenError):
    """Malformed token or signature mismatch."""


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _sign(signing_input: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _b64url(sig)


def _encode(payload: dict, secret: str) -> str:
    if not secret:
        raise TokenError("a non-empty signing secret is required")
    header = {"alg": "HS256", "typ": "JWT"}
    header_seg = _b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_seg = _b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    return f"{header_seg}.{payload_seg}.{_sign(signing_input, secret)}"


def create_access_token(
    *,
    user_id: str,
    role: str,
    tenant_id: str | None,
    email: str,
    secret: str,
    ttl_seconds: int = ACCESS_TOKEN_TTL_SECONDS,
    now: int | None = None,
) -> str:
    issued = int(now if now is not None else time.time())
    payload = {
        "iss": _ISSUER,
        "typ": "access",
        "sub": user_id,
        "role": role,
        "tid": tenant_id,
        "email": email,
        "iat": issued,
        "exp": issued + ttl_seconds,
        "jti": secrets.token_urlsafe(8),
    }
    return _encode(payload, secret)


def create_refresh_token(
    *,
    user_id: str,
    secret: str,
    ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS,
    now: int | None = None,
) -> tuple[str, str]:
    """Return ``(token, jti)``. The jti is stored (hashed) server-side so the
    token can be rotated/revoked — refresh tokens are single-use."""
    issued = int(now if now is not None else time.time())
    jti = secrets.token_urlsafe(24)
    payload = {
        "iss": _ISSUER,
        "typ": "refresh",
        "sub": user_id,
        "iat": issued,
        "exp": issued + ttl_seconds,
        "jti": jti,
    }
    return _encode(payload, secret), jti


def decode_token(token: str, secret: str, *, now: int | None = None) -> dict:
    """Verify signature + expiry and return the claims, else raise TokenError."""
    if not secret:
        raise TokenError("a non-empty signing secret is required")
    try:
        header_seg, payload_seg, sig_seg = token.split(".")
    except (ValueError, AttributeError) as exc:
        raise InvalidTokenError("malformed token") from exc
    signing_input = f"{header_seg}.{payload_seg}".encode("ascii")
    expected = _sign(signing_input, secret)
    if not hmac.compare_digest(expected, sig_seg):
        raise InvalidTokenError("signature mismatch")
    try:
        claims = json.loads(_b64url_decode(payload_seg))
    except (ValueError, json.JSONDecodeError) as exc:
        raise InvalidTokenError("undecodable payload") from exc
    current = int(now if now is not None else time.time())
    exp = claims.get("exp")
    if not isinstance(exp, int) or current >= exp:
        raise ExpiredTokenError("token expired")
    if claims.get("iss") != _ISSUER:
        raise InvalidTokenError("unexpected issuer")
    return claims
