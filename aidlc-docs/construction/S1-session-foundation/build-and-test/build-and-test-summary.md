# S1 (Session Foundation & Infra) — Build & Test Summary

Cycle: Rumor Distortion / Game Session, Phase 1. Date 2026-06-15. Scope: FR-R1 + NFR-R1/R2/R3 + Neo4j Rumor removal.

## Build Status
- **Backend**: `pip install -e ".[dev]"` — adds `sqlalchemy>=2.0,<3`, `psycopg[binary]>=3.1,<4`. Package imports; `api.main:app` now mounts the session router; `locus init-schema` also creates session tables.
- **Infra**: `docker-compose.yml` adds `postgres:16-alpine` to the default infra tier (bind-mount `./data/postgres`, `pg_isready` healthcheck); `app` gains `depends_on: postgres (service_healthy)`. Neo4j/OpenSearch stack unchanged.
- **Artifacts**: `locus/session/` package, `locus/storage/postgres_session_repo.py`, `api/routers/session.py`, updated compose/pyproject/setup-volumes/env.example.
- **Acceptable warnings**: FastAPI `on_event` deprecation (pre-existing); SQLAlchemy none.

## Test Execution Summary

### Unit / Component Tests (offline — external I/O mocked)
- **Backend (pytest)**: **153 passed**, 0 failed · coverage ≈ 83% · ruff ✅ · black ✅ · compileall ✅ · PBT (Partial) ✅.
- Was 124 (MVP-improvements baseline) → +session tests, −2 removed Neo4j-Rumor-only tests.
- **Session-layer tests**:
  - `tests/session/test_models.py` — validation + PBT round-trip (degree/support/confidence ∈ [0,1]).
  - `tests/session/test_repository_contract.py` — port contract (CRUD, timeline ordering, distortion upsert/PK, session isolation) via in-memory adapter.
  - `tests/session/test_service.py` — world validation (exists/missing→error), default-distortion seeding (all regions = 0.3), start→close lifecycle, history.
  - `tests/session/test_session_api.py` — TestClient happy path + 404s.
  - `tests/storage/test_postgres_session_repo.py` — **the real SQLAlchemy adapter run against in-memory SQLite** (roundtrip/mapping, ordering, idempotent close, isolation, idempotent ensure_schema).
- **Status**: ✅ PASS

### Integration Tests (live — operator-run, requires Docker PostgreSQL)
See scenarios below. **Status**: ⏳ PENDING operator run.

### Performance Tests
- **Status**: N/A (no hard targets; local single-instance MVP). Indexes on `session_rumors(session_id[,region_id])` / `timeline_entries(session_id)` per FD.

## Live Integration Scenarios (operator)

Prereq: `./scripts/setup-volumes.sh` · `cp env.example .env` · `docker compose up -d` (brings up neo4j + opensearch + **postgres**).

- **S1-A — Schema bootstrap**: `locus init-schema` → prints "… + PostgreSQL session tables ready." Verify in psql: `\dt` on `locus_session` shows `game_sessions`, `session_rumors`, `region_distortions`, `timeline_entries`. Re-run → idempotent (no error). [NFR-R3, BR-S1-17]
- **S1-B — Session start validates world + seeds distortion**: build a world first (`locus build-world --world demo --demo`); start `uvicorn api.main:app`; `POST /api/session/worlds/demo/sessions` → 200, `status=open, turn=0`. Query `region_distortions` → one row per demo region, `distortion_degree=0.3`. [FR-R1.1, BR-S1-2/3]
- **S1-C — Unknown world rejected**: `POST /api/session/worlds/does-not-exist/sessions` → **404**. [BR-S1-2]
- **S1-D — Lifecycle + history**: start 2 sessions for `demo`; `GET /api/session/worlds/demo/sessions` → 2 entries; `POST …/close` → `status=closed, closed_at` set; re-close → unchanged (idempotent); `GET …/timeline` → `[]`. [FR-R1.1]
- **S1-E — Persistence across restart**: `docker compose restart postgres`; `GET …/sessions` still returns prior sessions (bind-mount `./data/postgres`). [FR-R6.4 groundwork]
- **S1-F — App boot gating**: `docker compose --profile service up -d`; `app` becomes healthy only after `postgres` healthy; `/health` → 200. [SI-Q6=A]
- **S1-G — Canonical isolation**: confirm starting/closing sessions leaves Neo4j unchanged (node counts identical before/after). [NFR-R2]

## Requirement / NFR coverage
- **FR-R1.1** lifecycle → service + API (offline tests + S1-B/D). **FR-R1.2** id-only refs → models (no canonical copy). **FR-R1.3** PostgreSQL → adapter + S1-A.
- **NFR-R1** port abstraction → port + in-memory + Postgres adapters (contract tests). **NFR-R2** isolation → S1-G + read-only world validation. **NFR-R3** infra → compose postgres + S1-A/F.
- **NFR-R6** regression → full suite GREEN after Rumor removal; consensus auto-rumor view retained.

## Overall Status
✅ **Offline GREEN (153 tests, ruff/black/compileall clean).** Live PostgreSQL scenarios pending operator run. Canonical layer unchanged. Ready for S2 (Rumor Engine).
