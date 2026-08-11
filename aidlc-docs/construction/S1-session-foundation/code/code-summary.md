# S1 (Session Foundation & Infra) — Code Summary

Executed 2026-06-15. **153 backend tests GREEN** (was 124; +session tests, −2 removed Neo4j-Rumor tests), ruff + black clean, compileall clean. Offline (Postgres adapter exercised against in-memory SQLite; live PostgreSQL is operator-run).

## New package `locus/session/`
- **`models.py`** — `SessionStatus`/`TimelineKind` enums; `GameSession`/`SessionRumor`/`RegionDistortion`/`TimelineEntry` (Pydantic v2); `DEFAULT_DISTORTION_DEGREE=0.3`. Canonical refs are id strings only; degree/support/confidence ∈ [0,1] enforced.
- **`repository.py`** — `SessionRepository` Protocol (sessions/rumors/region-distortion/timeline + `ensure_schema`/connect/disconnect/health_check).
- **`memory_repo.py`** — `InMemorySessionRepository` (dict-based; monotonic clock for deterministic ordering; session isolation; idempotent close).
- **`service.py`** — `SessionService` + `WorldNotFoundError`. `start_session` validates the world has ≥1 Region (read-only, BR-S1-2) then seeds a default `RegionDistortion` for **every** region (BR-S1-3); close/get/list/get_timeline.

## New adapter `locus/storage/postgres_session_repo.py`
- SQLAlchemy 2.0 Core, sync. 4 tables; hybrid schema (core = regular indexed columns; `provenance`/`payload` = JSON, JSONB-variant on PostgreSQL). `id`=`new_id()`; `created_at`=DB `CURRENT_TIMESTAMP`. `ensure_schema`=idempotent `create_all(checkfirst=True)`. Portable types so the same code runs on SQLite offline.

## API + wiring
- **`api/routers/session.py`** — 5 routes: start / history / get / close / timeline (404 on unknown world/session).
- **`api/main.py`** — `session_repo`(Postgres)+`session_service` wired into `app.state`; router included; boot calls connect + ensure_schema.
- **`locus/config/settings.py`** — `session_db_url` (`SESSION_DB_URL`).
- **`locus/__main__.py`** — `init-schema` also ensures session tables (SI-Q5=A).

## Infra
- **`docker-compose.yml`** — `postgres:16-alpine` (default infra tier, `pg_isready` healthcheck, bind-mount `postgres_data`→`./data/postgres`); `app` `depends_on: postgres (service_healthy)` + container `SESSION_DB_URL` override (host=postgres).
- **`pyproject.toml`** — `sqlalchemy>=2.0,<3`, `psycopg[binary]>=3.1,<4`.
- **`scripts/setup-volumes.sh`** — `./data/postgres`. **`env.example`** — `SESSION_DB_*`.

## Neo4j `Rumor` removal (FD-S1 Q5=A; consensus auto-rumor view kept)
- Removed: `models/graph.py` `Rumor`; `models/__init__.py` export; `models/io.py` `Rumor` import + `KnowledgeGraph.rumors`; `models/reports.py` `rumors_created`; `graph_mapping.py` `rumor_to_node`/`node_to_rumor`/`distorted_from_edges`; `persistence.py` + `orchestrator.py` + `exporter.py` + `loader.py` rumor paths; `ontology/builder.py` `rumors=[]`; `neo4j_repo.py` `NODE_LABELS` "Rumor".
- Kept: consensus `ConsensusView.rumors`/`KnowledgeView.is_rumor`/`distortion_degree`, `ScopeLink.is_rumor`, `query` `include_rumors` (distance-based propagated classification, designer-only).
- Tests: removed 2 Neo4j-Rumor-only tests; cleaned `"Rumor": []` loader mock key.

## Tests added (`tests/session/`, `tests/storage/`)
- `test_models.py` (validation + PBT round-trip), `test_repository_contract.py` (in-memory port contract), `test_service.py` (world validation + distortion seeding + lifecycle), `test_session_api.py` (TestClient happy/404), `test_postgres_session_repo.py` (adapter against SQLite: roundtrip/ordering/idempotent close/isolation).

## Deferred to S2
Rumor generation/distortion (LLM), promotion/demotion, GameMaster turns, timeline writes, session NPC query overlay. S1 models/port/service are the stable contracts they build on.
