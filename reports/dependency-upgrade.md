# Dependency Upgrade & Compatibility Audit (2026-06-20)

> Goal: use the **latest** libraries (no outdated pins), mutually compatible and
> compatible with the system, and **PostgreSQL 18**. Latest versions were
> verified live against PyPI / npm / Docker Hub (not from memory). After
> upgrading, the full static suite was re-run — all green.

## Backend (Python) — `pyproject.toml`

| Package | Before | After (floor) | Latest verified |
|---|---|---|---|
| fastapi | >=0.115 | **>=0.138** | 0.138.0 |
| uvicorn[standard] | >=0.32 | **>=0.49** | 0.49.0 |
| pydantic | >=2.9 | **>=2.13** | 2.13.4 |
| pydantic-settings | >=2.6 | **>=2.14** | 2.14.2 |
| structlog | >=24.4 | **>=26.1** | 26.1.0 |
| httpx | >=0.27 | **>=0.28** | 0.28.1 |
| elasticsearch | >=9.0.0 | **>=9.4** | 9.4.1 (client) |
| asyncpg | >=0.30 | **>=0.31** | 0.31.0 (supports PG18) |
| redis | >=5.2 | **>=8.0** | 8.0.0 |
| celery | >=5.4 | **>=5.6** | 5.6.3 |
| opentelemetry-api/sdk | >=1.28 | **>=1.42** | 1.42.1 |
| opentelemetry-instrumentation-fastapi | >=0.49b0 | **>=0.63b1** | 0.63b1 |
| pytest (dev) | >=8.3 | **>=9.1** | 9.1.1 |
| pytest-asyncio (dev) | >=0.24 | **>=1.4** | 1.4.0 |
| ruff (dev) | >=0.7 | **>=0.15** | 0.15.18 |
| mypy (dev) | >=1.13 | **>=2.1** | 2.1.0 |

Compatibility note: **celery 5.6 + redis-py 8.0 + kombu** resolve with no
conflict (verified via pip dry-run + real install). `requires-python` kept at
`>=3.11` for broad compatibility; code uses no >3.11 features.

## Frontend (Node) — `apps/dashboard/package.json`

| Package | Before | After | Latest verified |
|---|---|---|---|
| next | 14.2.5 | **16.2.9** | 16.2.9 |
| react / react-dom | 18.3.1 | **19.2.7** | 19.2.7 |
| typescript | 5.5.3 | **6.0.3** | 6.0.3 |
| @types/node | 20.14.0 | **26.0.0** | 26.0.0 |
| @types/react | 18.3.3 | **19.2.17** | 19.2.17 |
| @types/react-dom | (missing) | **19.2.3** (added) | 19.2.3 |

Next 16 peer deps accept React 19; Node 22 satisfies Next 16's engine.

## Infrastructure — `docker-compose.yml`, `Dockerfile.python`, CI

| Component | Before | After |
|---|---|---|
| **PostgreSQL** | postgres:16 | **postgres:18** ✅ (requested) |
| Redis | redis:7 | **redis:8** |
| Elasticsearch / Kibana | 9.2.0 | **9.4.2** (latest 9.x) |
| Python base image | python:3.12-slim | **python:3.13-slim** |
| CI Python | 3.12 | **3.13** |
| CI Node | 20 | **22** |

(TEI / vLLM remain on their rolling tags; Elastic stays in the 9.x line so
DiskBBQ/ACORN/RRF semantics from the blueprint hold.)

## Verification (after upgrade — all green)

```
python -m ruff check .          → All checks passed!          (ruff 0.15.8)
python -m mypy packages services eval → no issues in 78 files (mypy 2.1.0)
python -m pytest -q             → 81 passed, 3 skipped         (pytest 9.1.0)
apps/dashboard: npx tsc --noEmit → exit 0   (Next 16 / React 19 / TS 6)
API import (api.main:app)        → OK
```

Installed runtime confirmed: fastapi 0.138.0, pydantic 2.13.4, elasticsearch
9.4.1, asyncpg 0.31.0, redis 8.0.0, celery 5.6.3, structlog 26.1.0, httpx 0.28.1.

**No application source changes were required** — the code is compatible with the
latest majors (Pydantic 2.13, redis-py 8, Next 16 / React 19 / TS 6). Only
dependency pins, infra image tags, and doc/version references changed.

### Known non-blocking note
- Starlette's `TestClient` emits a deprecation warning suggesting `httpx2`
  (test-only; does not affect runtime). Tracked for a future test-tooling bump.

### PostgreSQL 18 readiness
- `asyncpg>=0.31` supports the PG18 wire protocol.
- Migrations use only stable features (`gen_random_uuid()` via pgcrypto,
  `GENERATED ALWAYS AS IDENTITY`, `JSONB`, `scaled_float`-free SQL) — all valid
  on PG18; initdb auto-applies them on first boot.
- Live validation (actual `docker compose up` with PG18) remains part of the
  deferred Validation phase (no Docker in this audit environment).
