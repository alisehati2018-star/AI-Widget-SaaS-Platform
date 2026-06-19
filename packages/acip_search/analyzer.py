"""Persian analysis settings (M2: REQ-M2-001..006, blueprint Appendix A.1).

`fa_text` (index-time) keeps tokens clean and synonym-free; `fa_search`
(search-time) adds the updateable tenant synonym set so vocabulary can be tuned
without a reindex. The ZWNJ char_filter + decimal_digit + arabic/persian
normalization collapse the spelling and half-space variation that breaks naive
Persian search.
"""

from __future__ import annotations

ANALYSIS_SETTINGS: dict = {
    "analysis": {
        "char_filter": {
            "zwnj_normalizer": {
                "type": "mapping",
                # Map the ZWNJ half-space (U+200C) to a regular space so a word
                # with/without the half-space tokenizes identically. "‌" is
                # the real ZWNJ char — the same value JSON delivers from "‌".
                "mappings": ["‌=> "],
            }
        },
        "filter": {
            "persian_stop": {"type": "stop", "stopwords": "_persian_"},
            "store_synonyms": {
                "type": "synonym_graph",
                "synonyms_path": "analysis/synonyms_fa.txt",  # tenant-tunable
                "updateable": True,
            },
        },
        "analyzer": {
            "fa_text": {
                "type": "custom",
                "char_filter": ["zwnj_normalizer"],
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "decimal_digit",          # Persian/Arabic digits -> 0-9
                    "arabic_normalization",    # unify Arabic forms
                    "persian_normalization",   # unify Persian forms (ye/ke)
                    "persian_stop",
                ],
            },
            "fa_search": {
                "type": "custom",
                "char_filter": ["zwnj_normalizer"],
                "tokenizer": "standard",
                "filter": [
                    "lowercase",
                    "decimal_digit",
                    "arabic_normalization",
                    "persian_normalization",
                    "persian_stop",
                    "store_synonyms",
                ],
            },
        },
    }
}
