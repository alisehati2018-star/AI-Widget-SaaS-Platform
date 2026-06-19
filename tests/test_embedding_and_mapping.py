"""Unit tests for MRL truncation and the analyzer/mapping definitions (M2/M4)."""

from __future__ import annotations

import math

from acip_embedding.client import truncate_mrl
from acip_search.analyzer import ANALYSIS_SETTINGS
from acip_search.mapping import catalogue_mapping


def test_mrl_truncates_and_renormalizes():
    vec = [3.0, 4.0, 5.0, 6.0]
    out = truncate_mrl(vec, 2)
    assert len(out) == 2
    # Re-normalised to unit length for cosine.
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0, rel_tol=1e-9)


def test_mrl_noop_when_dims_ge_length():
    vec = [0.1, 0.2]
    assert truncate_mrl(vec, 8) == vec


def test_analyzer_has_persian_chain():
    analyzers = ANALYSIS_SETTINGS["analysis"]["analyzer"]
    assert "fa_text" in analyzers and "fa_search" in analyzers
    fa_text = analyzers["fa_text"]["filter"]
    required_filters = (
        "decimal_digit",
        "arabic_normalization",
        "persian_normalization",
        "persian_stop",
    )
    for required in required_filters:
        assert required in fa_text
    # Synonyms apply at search time only.
    assert "store_synonyms" in analyzers["fa_search"]["filter"]
    assert "store_synonyms" not in fa_text
    # ZWNJ char filter present on both.
    assert "zwnj_normalizer" in analyzers["fa_text"]["char_filter"]


def test_mapping_uses_diskbbq_and_dims():
    m = catalogue_mapping(768)
    emb = m["properties"]["embedding"]
    assert emb["dims"] == 768
    assert emb["index_options"]["type"] == "bbq_disk"
    assert emb["similarity"] == "cosine"
    assert m["dynamic"] == "strict"
    # tenant_id keyword for isolation + ACORN.
    assert m["properties"]["tenant_id"]["type"] == "keyword"
    # Suggest sub-field for autocomplete.
    assert m["properties"]["title"]["fields"]["suggest"]["type"] == "search_as_you_type"
