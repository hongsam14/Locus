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

## Game Session layer — Phase 2 (Event → dynamic distortion, 2026-06-19)
Adds **Events** that dynamically evolve per-region distortion over turns. **No new infra** — the
`session_events` table is created by `locus init-schema` (idempotent, additive); docker-compose unchanged.
1. Create an event (GameMaster): `POST …/sessions/{sid}/events` (region, category [war/plague/politics/
   disaster/festival/discovery], magnitude, optional lifecycle). LLM suggestions: `POST …/suggest-events?n=`
   → SUGGESTED; approve `POST …/events/{eid}/approve` (→ ACTIVE) or discard `DELETE …/events/{eid}`.
2. `POST …/advance-turn` now also: applies ACTIVE events to distortion (deterministic delta + topology-decayed
   propagation; persistent accumulates, one_shot auto-resolves), appends rumors in target regions (existing +
   support preserved), auto-evolves support (event-influenced +, others −), then re-evaluates promotion.
3. Resolve a persistent event `POST …/events/{eid}/resolve` → restores its accumulated distortion. Inspect
   live values `GET …/sessions/{sid}/distortions`; events `GET …/sessions/{sid}/events?status=`.
4. Web: SessionPanel adds an event create form, session-wide event list (Approve/Discard/Resolve), a
   "Suggest events" button, and shows the real per-region distortion. Timeline records EVENT_* entries.

> Distortion/propagation/support evolution are **deterministic** (LLM-independent); only event *suggestion*
> uses the LLM and is graceful (no suggester / failure → no suggestions, the turn still advances).
> Event-to-event interaction (Phase 3 remainder) is still deferred.

### Rumor Dynamics & Hardening (U-H1/U-H2, post code-review)
support(공신력) is now the rumor "aliveness" lever, so the set stays finite without manual `regenerate`:
1. **Decay & prune** — each `advance-turn`, unreinforced rumors lose support (`RUMOR_SUPPORT_DECAY`, 0.05)
   and any below `RUMOR_PRUNE_FLOOR` (0.05) are **soft-flagged** (`active=false`, row kept) — promoted rumors
   are exempt. New rumors are born at `RUMOR_BIRTH_SUPPORT` (0.2) so they survive a few quiet turns.
2. **Propagation gate** — only rumors with `support ≥ RUMOR_MIN_SOURCE_SUPPORT` (0.3) re-seed new rumors on
   the auto-append path (manual `generate`/`regenerate` unchanged).
3. **Rumor→region feedback** — high-support rumor density bumps a region's distortion each turn
   (`RUMOR_FEEDBACK_WEIGHT` 0.1 × density of rumors ≥ `RUMOR_HIGH_SUPPORT_THRESHOLD` 0.6), so strong rumors
   keep a region dynamic even with no events. `TurnResult` now reports `pruned_rumor_ids` + `feedback_regions`.
4. All knobs are env-tunable (`RUMOR_*` in `.env`); the engine stays deterministic (LLM-independent).

**Schema migration**: `init-schema` (and `ensure_schema` on app start) adds `session_rumors.active` idempotently
(`ADD COLUMN IF NOT EXISTS`, default TRUE) — existing sessions upgrade in place, no data change.

**Build path fixes**: topology now sees this world's persisted common-sense priors (wiki injected before
`topology.build`); a barrier terrain not bordering exactly 2 regions is reported in `IngestionResult.errors`
instead of being silently dropped. Web SessionPanel loads its reads in parallel.

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

## Localization & UX (UX Improvement cycle, 2026-08-11)
- **Translation (X1)**: LLM-backed ko translation of session content (rumors/events) + canonical Knowledge, cached in the PostgreSQL `translations` table (created by `init-schema`, additive). Reuses the OpenAI provider. Config: `TRANSLATION_ENABLED`(기본 true), `TRANSLATION_TARGET_LANG`(ko). **Reads never block on the LLM** — cache-only on read, misses warm on a background thread; so the first view of new content may show English, then Korean on refetch. Disabled → all English (graceful).
- **Turn-change notifications**: `advance-turn` returns `region_changes` (per-region promoted/demoted/pruned/events/added); the web SessionPanel shows one auto-dismiss toast per changed region.
- **Regenerate preserves promoted**: `regenerate_region` keeps promoted rumors and reseeds the rest from **canonical knowledge only** (promoted rumors are not reused as chain seeds). Applies to per-region and "전체 재생성".
- **Frontend (X2/X3)**: Tailwind v4 ("Doodly" paper+ink theme) + self-hosted Gaegu Korean handwriting font (`@fontsource/gaegu`, no CDN). Korean UI labels + timeline i18n. Build: `cd web && npm install --legacy-peer-deps && npm run build`.
- **No new infra**: canonical graph unchanged; only additive session-layer `translations` table + response-only ko fields + `region_changes`. Rollback is additive-safe.

## Future Operations (not implemented)
- Containerized app service running uvicorn by default; CI/CD; cloud deploy; monitoring/alerting; backup of Neo4j/OpenSearch/**Postgres** volumes; consensus cache + scaling; managed PostgreSQL / connection pooling.
