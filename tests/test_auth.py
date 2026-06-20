"""Phase 5 identity/auth primitives: password hashing, JWTs, role model.

Hermetic — exercises the stdlib crypto/token layer with no DB or network.
"""

from __future__ import annotations

import time

import pytest
from acip_auth import (
    Role,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from acip_auth.models import AuthPrincipal
from acip_auth.passwords import DEFAULT_ITERATIONS
from acip_auth.tokens import ExpiredTokenError, InvalidTokenError, TokenError

SECRET = "test-secret-please-change-0123456789abcdef"


# --- passwords ------------------------------------------------------------- #
def test_hash_is_salted_and_verifies():
    h1 = hash_password("Sup3rStr0ng!")
    h2 = hash_password("Sup3rStr0ng!")
    assert h1 != h2  # unique salt per hash
    assert h1.startswith(f"pbkdf2_sha256${DEFAULT_ITERATIONS}$")
    assert verify_password("Sup3rStr0ng!", h1)
    assert not verify_password("wrong-password", h1)


def test_verify_rejects_garbage_stored_value():
    assert not verify_password("x", "not-a-valid-hash")
    assert not verify_password("x", "")


def test_needs_rehash_on_lower_iterations():
    weak = hash_password("Sup3rStr0ng!", iterations=1000)
    assert needs_rehash(weak)
    assert not needs_rehash(hash_password("Sup3rStr0ng!"))


def test_password_strength_policy():
    assert validate_password_strength("Sup3rStr0ng!") == []
    assert validate_password_strength("short")  # too short
    assert validate_password_strength("alllowercaseonly")  # too few classes


# --- tokens ---------------------------------------------------------------- #
def test_access_token_roundtrip():
    token = create_access_token(
        user_id="u1", role="store_owner", tenant_id="t1", email="a@b.co", secret=SECRET
    )
    claims = decode_token(token, SECRET)
    assert claims["sub"] == "u1"
    assert claims["typ"] == "access"
    assert claims["tid"] == "t1"
    assert claims["role"] == "store_owner"


def test_refresh_token_has_unique_jti():
    t1, j1 = create_refresh_token(user_id="u1", secret=SECRET)
    t2, j2 = create_refresh_token(user_id="u1", secret=SECRET)
    assert j1 != j2
    assert decode_token(t1, SECRET)["typ"] == "refresh"


def test_tampered_signature_rejected():
    token = create_access_token(
        user_id="u1", role="platform_admin", tenant_id=None, email="a@b.co", secret=SECRET
    )
    with pytest.raises(InvalidTokenError):
        decode_token(token, "a-different-secret")
    with pytest.raises(InvalidTokenError):
        decode_token(token + "x", SECRET)


def test_expired_token_rejected():
    past = int(time.time()) - 10_000
    token = create_access_token(
        user_id="u1", role="store_owner", tenant_id="t1", email="a@b.co",
        secret=SECRET, ttl_seconds=1, now=past,
    )
    with pytest.raises(ExpiredTokenError):
        decode_token(token, SECRET)


def test_empty_secret_refused():
    with pytest.raises(TokenError):
        create_access_token(
            user_id="u1", role="store_owner", tenant_id="t1", email="a@b.co", secret=""
        )


# --- role model ------------------------------------------------------------ #
def test_admin_sees_all_tenants_owner_sees_own():
    admin = AuthPrincipal(user_id="a", email="a@b.co", role=Role.PLATFORM_ADMIN, tenant_id=None)
    owner = AuthPrincipal(user_id="o", email="o@b.co", role=Role.STORE_OWNER, tenant_id="t1")
    assert admin.is_admin and admin.can_access_tenant("anything")
    assert not owner.is_admin
    assert owner.can_access_tenant("t1")
    assert not owner.can_access_tenant("t2")
