"""Unit tests for the cache foundation (M6: REQ-M6-002/003/005)."""

from __future__ import annotations

import math

from acip_cache.l1 import cache_key, normalize_text
from acip_cache.l2 import cosine


def test_l1_key_normalises_whitespace_and_case():
    assert normalize_text("  Hello   World  ") == "hello world"
    assert cache_key("t1", "Hello World", 0) == cache_key("t1", "  hello   world ", 0)


def test_l1_key_changes_with_data_version():
    # A data-version bump (sync event) invalidates the entry (REQ-M6-005).
    assert cache_key("t1", "q", 0) != cache_key("t1", "q", 1)


def test_l1_key_is_tenant_scoped():
    assert cache_key("t1", "q", 0) != cache_key("t2", "q", 0)


def test_cosine_identity_and_orthogonal():
    assert math.isclose(cosine([1.0, 0.0], [1.0, 0.0]), 1.0)
    assert math.isclose(cosine([1.0, 0.0], [0.0, 1.0]), 0.0)
    assert cosine([], [1.0]) == 0.0
