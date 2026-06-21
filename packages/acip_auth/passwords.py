"""Password hashing + strength policy (stdlib PBKDF2-HMAC-SHA256).

Stored format (Django-compatible): ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``.
Only the derived hash is ever persisted — never the raw password.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
# OWASP (2023) guidance for PBKDF2-HMAC-SHA256. Tunable upward over time;
# `needs_rehash` lets us transparently upgrade stored hashes on next login.
DEFAULT_ITERATIONS = 600_000
_SALT_BYTES = 16
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256  # bound work / avoid DoS on absurd inputs


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode("ascii"))


def hash_password(raw: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Hash a plaintext password into a self-describing PBKDF2 string."""
    if not raw:
        raise ValueError("password must not be empty")
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${_b64(salt)}${_b64(derived)}"


def verify_password(raw: str, stored: str) -> bool:
    """Constant-time verify a plaintext password against a stored hash."""
    try:
        algorithm, iter_s, salt_b64, hash_b64 = stored.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        iterations = int(iter_s)
        salt = _unb64(salt_b64)
        expected = _unb64(hash_b64)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def needs_rehash(stored: str, *, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """True if a stored hash uses a weaker scheme/parameter than current policy."""
    try:
        algorithm, iter_s, _, _ = stored.split("$", 3)
    except ValueError:
        return True
    return algorithm != ALGORITHM or int(iter_s) < iterations


def validate_password_strength(raw: str) -> list[str]:
    """Return a list of policy violations (empty list == acceptable).

    Conservative, locale-agnostic policy: length floor + character diversity.
    Length is the dominant factor; diversity blocks trivially weak choices.
    """
    problems: list[str] = []
    if len(raw) < MIN_PASSWORD_LENGTH:
        problems.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(raw) > MAX_PASSWORD_LENGTH:
        problems.append(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    classes = sum(
        bool(p)
        for p in (
            any(c.islower() for c in raw),
            any(c.isupper() for c in raw),
            any(c.isdigit() for c in raw),
            any(not c.isalnum() for c in raw),
        )
    )
    if classes < 3:
        problems.append(
            "Password must mix at least three of: lowercase, uppercase, digits, symbols."
        )
    return problems
