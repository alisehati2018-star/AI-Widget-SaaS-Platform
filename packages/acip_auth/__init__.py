"""acip_auth — identity, authentication, and authorization (Phase 5).

Security foundation for the human-facing surfaces (platform-admin panel,
store-owner dashboard, self-serve signup). Distinct from the machine-to-machine
scoped API keys in ``acip_core.security`` (those authenticate stores/widgets;
this authenticates *people*).

Design choices (security-first, dependency-free):
- Passwords: PBKDF2-HMAC-SHA256 (OWASP-recommended KDF; Django's default),
  per-user random salt, constant-time verification.
- Tokens: compact HS256 JWTs (access + rotating refresh), signed with a
  server secret from the environment. Implemented on the stdlib so the
  on-prem deployment carries no fragile native crypto dependency.
"""

from __future__ import annotations

from .models import AuthPrincipal, Role
from .passwords import (
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from .tokens import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

__all__ = [
    "Role",
    "AuthPrincipal",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "validate_password_strength",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenError",
    "ExpiredTokenError",
    "InvalidTokenError",
]
