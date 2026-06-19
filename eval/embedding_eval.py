"""Embedding-candidate evaluation skeleton (T-P0-012 / REQ-M4-001, REQ-M4-003).

Scores each candidate embedding model (BGE-M3, Qwen3-Embedding, varying MRL
dims) on the golden set so the choice is made on data, not opinion (§21.4).

Phase 0 ships the *structure*: a candidate spec and the evaluation loop shape.
Actual embedding + kNN scoring is wired once the embedding service (M4) and the
search index (M2/M5) exist in Phase 1. Running it now emits the planned matrix
with TBD metrics, which feeds `eval/decision-log.md`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    name: str
    dims: int
    licence: str


CANDIDATES: list[Candidate] = [
    Candidate(name="BAAI/bge-m3", dims=1024, licence="MIT"),
    Candidate(name="Qwen/Qwen3-Embedding", dims=1024, licence="Apache-2.0"),
]


def planned_matrix() -> list[dict[str, object]]:
    """Return the candidate matrix to be filled by the Phase-1 wiring."""
    return [
        {
            "candidate": c.name,
            "dims": c.dims,
            "licence": c.licence,
            "ndcg@10": "TBD",
            "p95_latency_ms": "TBD",
            "vector_ram_per_1m": "TBD",
        }
        for c in CANDIDATES
    ]


if __name__ == "__main__":
    import json

    print(json.dumps(planned_matrix(), indent=2, ensure_ascii=False))
