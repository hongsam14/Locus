# Operations — Locus (placeholder)

AI-DLC Operations is a **placeholder** stage. For the MVP, operation is local via Docker Compose; no production deploy/monitoring workflow is in scope yet.

## Run (local)
```bash
./scripts/setup-volumes.sh     # create ./data bind-mount dirs (first run)
cp env.example .env            # set OPENAI_API_KEY + REQUIRED passwords:
                               #   NEO4J_PASSWORD, SESSION_DB_PASSWORD (no insecure defaults;
                               #   compose fails fast if unset)

docker compose up -d                            # infra: neo4j + opensearch + postgres (bind-mounted ./data)
docker compose --profile tools up -d            # + OpenSearch Dashboards (:5601)
docker compose --profile service up -d --build  # + app (uvicorn :8000, runs init-schema then serves) + web (:3000)
```
- Profiles: default=infra (neo4j + opensearch + **postgres**), `service`=app+web, `tools`=dashboard. `app` needs `OPENAI_API_KEY` and waits for postgres healthy.
- Host dev (no app container): `docker compose up -d` then `uvicorn api.main:app --port 8000` + `cd web && npm run dev`.
- `SESSION_DB_URL` (PostgreSQL) configures the game-session layer; on host use `localhost:5432`, in compose `postgres:5432` (auto-overridden for `app`).

## Typical workflow
1. `locus init-schema` (idempotent).
2. `locus build-world --world <id> --demo|--inputs <file>` — also distills that world's own
   Common-sense Wiki priors + links (no separate `build-wiki` step since the 2026-06-09 MVP-improvement cycle).
3. Query: `GET /api/query/regions/{id}/knowledge?world_id=<id>` ; author: `/api/authoring/*`.
4. Designer cross-world reference: `GET /api/authoring/worlds/{id}/related-priors` — priors from OTHER
   worlds sharing this world's domain tags (read-through; never enters NPC build/query).
5. `locus export --world <id> --out <file.json>` for NPC-runtime static bundles.

> MVP-improvement cycle (2026-06-09) changed only application/data layers — no infra/deploy change.
> Each world is now self-contained (its own WikiPriors); `__realworld__` partition removed.

## Game Session layer (Rumor / Game-Session cycle, Phase 1, 2026-06-15)
A dynamic **game-session layer** (PostgreSQL) sits over the static canonical world (Neo4j/OpenSearch).
The canonical layer is referenced by id only and never mutated by sessions (NFR-R2).
```bash
locus init-schema          # now also creates the PostgreSQL session tables (idempotent)
```
1. Start a play-through: `POST /api/session/worlds/{world_id}/sessions` (validates the world exists;
   seeds a default per-region distortion). History: `GET /api/session/worlds/{world_id}/sessions`.
2. GameMaster (per turn): generate rumors `POST …/sessions/{sid}/regions/{rid}/rumors` (LLM degree-chain
   distortion of direct + propagated knowledge + existing rumors), regenerate, `PUT …/rumors/{id}/support`,
   `PUT …/regions/{rid}/distortion`, `POST …/sessions/{sid}/advance-turn` (re-evaluate promotion, turn++).
3. NPC session query: `GET …/sessions/{sid}/regions/{rid}/knowledge` — Knowledge(+promoted rumors as
   direct-like)+rumors; distance-based `propagated`/auto-rumor excluded (designer-only).
4. Timeline / history: `GET …/sessions/{sid}/timeline`; past (closed) sessions are read-only.
5. Web: SessionBar (create/select/close) + SessionPanel (GameMaster hub: turn, timeline, generate,
   support/distortion sliders, PROMOTED badge).

> This cycle ADDS PostgreSQL (session-only) to the infra tier; Neo4j/OpenSearch stack unchanged.
> LLM rumor generation needs `OPENAI_API_KEY` and is graceful (a failed step is skipped, the turn proceeds).
> Phase 2 (Event interaction → dynamic distortion) is deferred.

## Web UI (U10)
```bash
cd web && npm install
npm run dev          # dev server :5173, proxies /api -> :8000 (run uvicorn separately)
npm run build        # static build -> web/dist (serve behind any static host / reverse proxy)
```
- Review/edit/augment UI: map-overlay topology, region knowledge, in-UI augmentation Q&A.

## Observability (current)
- Structured stdout from CLI/app; container healthchecks (Neo4j HTTP, OpenSearch cluster health, **Postgres `pg_isready`**).
- Dashboards/alerting: out of scope (future Operations expansion).

## Future Operations (not implemented)
- Containerized app service running uvicorn by default; CI/CD; cloud deploy; monitoring/alerting; backup of Neo4j/OpenSearch/**Postgres** volumes; consensus cache + scaling; managed PostgreSQL / connection pooling.
