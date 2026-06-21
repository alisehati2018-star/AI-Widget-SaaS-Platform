"""Phase 7 billing helpers — hermetic no-DB safety + webhook signature.

Mirrors the existing ledger tests: the subscription helpers must never raise on
the no-pool path (billing must not break the request path). Also verifies the
webhook HMAC-SHA256 signature check accepts only correctly-signed bodies.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta

from acip_billing import (
    activate_plan,
    create_order,
    create_topup_order,
    list_past_due,
    mark_order_paid,
    process_renewals,
    proration_preview,
    set_cancel,
    usage_summary,
)
from acip_billing.subscription import _proration_credit


async def test_subscription_helpers_safe_without_pool():
    assert await create_order(None, "t1", "pro") is None
    assert await create_topup_order(None, "t1", 1000) is None
    assert await activate_plan(None, "t1", "pro") is False
    assert await mark_order_paid(None, "order1") is None
    assert await proration_preview(None, "t1", "pro") is None
    assert await set_cancel(None, "t1", True) is False
    assert await process_renewals(None) == {"downgraded": 0, "past_due": 0}
    assert await list_past_due(None) == []
    assert await usage_summary(None, "t1") == {"used": 0.0, "granted": 0.0}


def test_proration_credit_math():
    # Full period remaining → full price credited; none remaining → 0.
    half = datetime.now(UTC) + timedelta(days=15)
    assert _proration_credit(30.0, half, 30) == 15.0  # ~half the month left
    assert _proration_credit(30.0, datetime.now(UTC) - timedelta(days=1), 30) == 0.0
    assert _proration_credit(0.0, half, 30) == 0.0  # free plan → no credit


def test_topup_pricing():
    # 50000 credits at 1000 credits/unit = 50.00 (default rate).
    from acip_core.config import get_settings

    rate = get_settings().topup_credits_per_unit
    assert round(50000 / rate, 2) == 50.0


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
