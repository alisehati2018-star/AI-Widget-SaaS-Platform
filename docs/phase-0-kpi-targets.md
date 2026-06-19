# ACIP — KPI Targets (the project contract, T-P0-013 / §18)

Recorded in Phase 0 as the agreed contract the system holds itself to. Tracked
on the four-dimension dashboard (M9/M12). Baselines for relevance are set
against the golden set in Phase 0; the rest become live as their features ship.

## Relevance & search quality (§18.1)
| Metric | Target |
|---|---|
| NDCG@10 on golden set | Beat native by a clear margin; track toward ≥ 0.80 |
| Zero-result rate | < 5% of searches |
| Click-through / engagement | Trending up release over release |
| Assistant groundedness | ≥ 95% of answers attributable to store data |

## Performance & latency (§18.2)
| Metric | Target |
|---|---|
| Search latency p95 | < 150 ms |
| Search latency p99 | < 300 ms |
| Assistant time-to-first-token | < 1.5 s |
| Suggest / autocomplete | < 50 ms |

## AI cost efficiency (§18.3)
| Metric | Target |
|---|---|
| Cache hit rate (L1+L2) | > 60% of assistant turns |
| Turns served without paid API | > 85% |
| Cost per assistant turn | Trending toward near-zero |
| Local-model share of inference | Majority at steady state |

## Reliability & multi-tenancy (§18.4)
| Metric | Target |
|---|---|
| Search availability | ≥ 99.9% |
| Tenant-isolation test | 100% pass — release blocker |
| Sync freshness (event path) | < 1 min typical |
| Mean time to recovery | Bounded, rehearsed via DR drills |

> Open items affecting these targets: GAP-A2 (concrete NDCG margin), GAP-B1
> (error-budget numbers), GAP-B3 (RPO/RTO) — see `docs/generated/gap-analysis.md`.
