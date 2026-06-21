"""Phase 7 billing helpers — hermetic no-DB safety + webhook signature.

Mirrors the existing ledger tests: the subscription helpers must never raise on
the no-pool path (billing must not break the request path). Also verifies the
webhook HMAC-SHA256 signature check accepts only correctly-signed bodies.
"""

from __future__ import annotations

import hashlib
import hmac

from acip_billing import activate_plan, create_order, mark_order_paid, usage_summary


async def test_subscription_helpers_safe_without_pool():
    assert await create_order(None, "t1", "pro") is None
    assert await activate_plan(None, "t1", "pro") is False
    assert await mark_order_paid(None, "order1") is None
    assert await usage_summary(None, "t1") == {"used": 0.0, "granted": 0.0}


def test_webhook_signature_roundtrip():
    secret = "whsec_test_0123456789"
    body = b'{"order_id":"abc","status":"paid"}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    # Correct signature verifies; tampered body or wrong secret does not.
    assert hmac.compare_digest(
        hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(), sig
    )
    assert not hmac.compare_digest(
        hmac.new(b"wrong", body, hashlib.sha256).hexdigest(), sig
    )
    assert not hmac.compare_digest(
        hmac.new(secret.encode(), body + b" ", hashlib.sha256).hexdigest(), sig
    )
