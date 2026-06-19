# Golden query set (the backbone of quality)

The single most valuable testing asset the project owns (blueprint §20.1).
~50 representative Persian queries from a **real** store, each with
human-judged relevance. Built in Phase 0 (T-P0-010), grown continuously, and
used as the CI relevance gate (REQ-M12-009).

## Format

JSONL — one record per line, conforming to `schema.json`. See
`golden_set.example.jsonl` for a 5-row illustrative sample (synthetic ids).

## Coverage (must span all buckets, §20.1)

- `common` — frequent product searches
- `long_tail` / `conversational` — natural phrasing
- `misspelling` — typos, colloquial spellings
- `zwnj_spacing` — ZWNJ / half-space variants (e.g. می‌روم vs میروم)
- `synonym_brand` — brand transliterations, Arabic/Persian char variants
- `hard_ambiguous` — known difficult queries

## Status

`golden_set.example.jsonl` is a **template sample only**. The production
golden set (real store, judged) is assembled during Phase 0 and is a hard exit
criterion (see `docs/generated/phase-0.md`). Open item: **GAP-B7** (ownership
and refresh cadence) and **ASM-4** (a real pilot store is available).
