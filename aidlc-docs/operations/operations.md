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
2. `locus world build --world <id> --inputs <file>` (or `locus world demo --name aldermoor --world <id>` for the LLM-free demo) — a build also distills that world's own
   Common-sense Wiki priors + links (no separate `build-wiki` step since the 2026-06-09 MVP-improvement cycle).
3. Query: `GET /api/knowledge/worlds/{world_id}/regions/{id}?include_hearsay=true` ; author: `/api/world/*` (U1 route prefixes).
4. Designer cross-world reference: `GET /api/world/worlds/{id}/related-priors` — priors from OTHER
   worlds sharing this world's domain tags (read-through; never enters NPC build/query).
5. `locus world export --world <id> --out <file.world.json>` — World File v1 (also the NPC-runtime static bundle).

> MVP-improvement cycle (2026-06-09) changed only application/data layers — no infra/deploy change.
> Each world is now self-contained (its own WikiPriors); `__realworld__` partition removed.

## Game Session layer (Rumor / Game-Session cycle, Phase 1, 2026-06-15)
A dynamic **game-session layer** (PostgreSQL) sits over the static canonical world (Neo4j/OpenSearch).
The canonical layer is referenced by id only and never mutated by sessions (NFR-R2).
```bash
locus init-schema          # now also creates the PostgreSQL session tables (idempotent)
locus init-schema --play --localization   # U1: flags pick a subset — --world (Neo4j/OpenSearch), --play (PostgreSQL play tables), --localization (translations); no flag = all
```
1. Start a play-through: `POST /api/play/worlds/{world_id}/sessions` (validates the world exists;
   seeds a default per-region distortion). History: `GET /api/play/worlds/{world_id}/sessions`. GameMaster tools live under `/api/gm/*`.
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

## World File · demo · backups (Purpose Restructure U2, 2026-09-30)
- **Save / load a world (World File v1)** — `locus world export --world <id> --out <id>.world.json`, `locus world import --world <id> --file <file> [--replace/--no-replace] [--remap] [--force]`. API: `GET /api/world/worlds/{id}/file` (download), `POST /api/world/worlds/{id}/file?replace=&confirm=&remap=` (JSON body) or `POST .../file/upload` (multipart). Legacy export JSON (no `format_version`) is accepted as v0; other versions → 422. Loading a file into a different world id remaps every id deterministically (`uuid5`); `remap=true` / `--remap` forces it (recovery from an `id collision with another world` error).
- **Demo world without an LLM** — `locus world demo --list`, `locus world demo --name aldermoor --world <id>`; API `GET /api/world/demos`, `POST /api/world/worlds/{id}/demo/aldermoor`. The packaged World File loads with **0 LLM calls**; the editor's "Load demo world" button uses it. The source-based build (`locus world build --world <id> --demo-sources`, `POST .../demo/aldermoor/build`) still needs `OPENAI_API_KEY`.
- **Build** — `locus world build --world <id> --inputs <file.json>` (images base64 in `map_images`/`concept_arts`); API `POST /api/world/worlds/{id}/build` (JSON) or `.../build/upload` (multipart fields: `memos`, `maps`, `images` (repeatable), `name`, `description`). `BuildReport.ok` is false only for error-severity warnings (persist failure, unreadable input, zero regions); item-level problems and unresolved names are warnings; `unscoped_knowledge_ids` lists knowledge that found no region; `llm_calls`/`embedding_calls` count that build.
- **Replacing a world** — build/import/demo replace an existing world by default (`replace=true`). Before deleting, the old world is exported to `LOCUS_DATA_DIR/backups/<id>-<UTC>.world.json` (compose: the `locus_data` volume at `/app/data`). Recover with `locus world import --world <id> --file <backup>`. If the world has **open sessions**, the API answers 409 (`open_sessions`, `session_ids`) until `confirm=true`; the CLI exits 1 until `--force`; confirmed/forced replaces close those sessions and list them in `closed_session_ids`.
- **Single worker** — play and the editor read one in-process `WorldCache` per worker; run the API with **one uvicorn worker** (compose does). Writes (build, import, edit, augmentation, prior edit) invalidate it.
- **Without `OPENAI_API_KEY`** — the API starts, `/health` reports `degraded`, and world file / demo / list / editor routes work; build, augmentation and wiki routes answer 503.
- `locus world list` prints stored worlds with name, region count and last update (`WorldMeta`; pre-U2 worlds show `name=id`). Old aliases `locus build-world` / `locus export` still work for one cycle.

## Player mode (Purpose Restructure U4, 2026-09-30)

- **Routes**: `POST /api/play/worlds/{w}/sessions` with `{name, start_region_id}` starts a
  player session (201 `{session, player}`); without a body it still creates a GM-only session
  (200). `GET /api/play/sessions/{s}/region` is the player screen; `POST .../act`
  (`{type: move|wait|end_talk}`) answers **202** with a `TurnRun` and the turns run in the
  background; poll `GET .../turn-runs/{id}` until `done` / `failed`; `GET .../log`.
- **Turn engine**: one entry point for GM manual turns and player actions. A turn is
  compute → draft (LLM) → one transaction. Caps (env, see `env.example`): `LLM_MAX_CALLS_PER_TURN`
  (8), `RUMOR_MAX_NEW_PER_REGION_TURN` (2), `RUMOR_MAX_ACTIVE_PER_REGION` (20), move cost cap
  `PLAY_MAX_MOVE_COST` (5). Worst case per action = `PLAY_MAX_MOVE_COST × LLM_MAX_CALLS_PER_TURN`
  calls. GM manual generate/regenerate ignore the caps (intentional). `llm_calls` in the
  results counts *reserved* calls (upper bound).
- **Concurrency**: one running turn per session (in-process guard). A second action, a GM
  manual turn, closing the session, or a GM write (rumors / support / distortion / events)
  while a run is in flight answers **409 `turn in progress`**; reads are never blocked. The
  guard is process-local: keep **`--workers 1`** (compose already does). Raising the worker
  count breaks two things, not one: two workers can run turns for the same session at the
  same time, and a starting worker's `fail_stale_runs` marks **another worker's live run**
  `failed` (code review U4 #5, accepted for this demo scale — there is no cross-process
  fencing).
- **Background executor**: one daemon worker thread, FIFO across sessions. A queued run is
  shown as `running` before it actually starts (demo scale: fine). On shutdown the API waits
  `TURN_SHUTDOWN_TIMEOUT_S` (30s) for the current run; a hung LLM call does not block process
  exit. On startup any run still `running` is marked `failed` (`error=interrupted`).
- **LLM outage**: each LLM call makes 3 attempts with a 30s timeout
  (`locus/shared/llm/retry.py`). Between attempts it waits 1s then 2s, or what the server
  asked for in `Retry-After` / `retry-after-ms` (rate limits, 503), capped at 8s. Worst case
  per call: **106s** (30 × 3 + 8 + 8). All three OpenAI clients (chat, vision, embeddings)
  set `max_retries=0` and the 30s timeout, so the SDK does not retry underneath; its timeout
  applies per phase, so 106s is the design bound rather than a hard one (U5 review: 93s
  before the Retry-After wait, ≈97s before that). A turn whose rumor chain comes back short
  trips a circuit breaker (remaining drafts of that turn are skipped, `llm_failed=true` in
  the result), so an action is bounded by ≈ `PLAY_MAX_MOVE_COST × 106s`. Without an LLM key the engine still runs
  (moves, waits, events, promotion); only rumor drafts are skipped (`llm_available=false`).
- **Timeline order**: a turn's entries are written in one transaction, so they are stamped
  by the application with a strictly increasing clock (`locus/play/storage/clock.py`) rather
  than the database default, and read back ordered by `(turn, created_at, id)`. This is the
  one table whose `created_at` is not DB server time.
- **Failure records**: a failed run stores the fixed message `turn processing failed`; the
  timeline `turn_run_failed` payload holds only the exception class name (details go to the
  server log). Turns already committed stay.
- **Tables** (idempotent `init-schema --play` / startup): `players` (one per session),
  `turn_runs`.

## NPC dialogue & display language (Purpose Restructure U5, 2026-09-30)

- **Routes** (under `/api/play/sessions/{s}`): `GET npcs` lists the NPCs of the player's
  region with `has_conversation` / `message_count`; `POST npcs/{n}/start` returns the
  conversation and its history, creating it on first use (**no LLM**); `POST npcs/{n}/say?lang=`
  with `{text}` returns the NPC's answer (**one LLM call**); `GET npcs/{n}/history` reads a
  conversation, closed sessions included. Errors: 400 for empty or too-long text, an
  unsupported `lang`, or an NPC outside the player's region; 404 for an unknown NPC, session
  or conversation; 409 for a closed session; **503 on `say` only** when no LLM provider is
  configured (everything else keeps working).
- **Turns**: talking spends no turn and takes no turn lock, so it works while a turn runs.
  "End talk" is the U4 action `POST .../act {type: end_talk, npc_id}`: one turn, plus an
  `npc_talked` timeline entry with the message count.
- **What an NPC knows**: the region's canonical facts of scope direct / inherited / global
  (`NPC_MAX_FACTS`, 12) and its active rumors (`NPC_MAX_RUMORS`, 8). A picked rumor hides the
  fact it distorts, so the NPC does not tell both versions. **Hearsay is not included**: the
  player's region screen still shows it, under a hint that the locals may not know it. The
  prompt also replays the last `NPC_MAX_RECENT_MESSAGES` (10) lines; a line is at most
  `NPC_MAX_MESSAGE_CHARS` (500) characters. These limits bound the prompt, so its size does
  not grow with the length of a conversation.
- **Cost and failure**: one call per `say`, outside the turn budget (`LLM_MAX_CALLS_PER_TURN`
  does not apply; the player's pace is the limit). Worst case **106s** per call (see "LLM
  outage" above). The web image's nginx waits 130s for `/api/` (`web/nginx.conf`), so a slow
  answer is not cut off with a 504 while the backend still saves it. A reverse proxy in
  front of the API needs the same allowance. The call runs before the transaction, so a failed call stores nothing: no
  conversation row and no message. A call that still fails after its retries answers **500**,
  because BR-U5-30 only says the error is raised and gives no status. An empty answer is
  replaced by a fixed line in the display language.
- **Display language**: `SUPPORTED_LANGS` (default `ko,en`) is the `?lang=` allow-list.
  `TRANSLATION_TARGET_LANG` is the default, and startup fails if it is not in the list.
  `?lang=` is taken by the player region, the session and canonical region-knowledge reads,
  the GM rumor and event lists, and `say`. The timeline does not take it (it has no
  translated field). `lang=en` returns the `*_ko` fields empty and warms no translation,
  because the sources are English. Dialogue lines are stored in the language they were
  written in and are never translated. `GET /api/langs` returns `{default, supported}`.
  The web UI reads it at start, offers only languages the server takes, and sends `?lang=`
  only when it differs from the server default. Before the answer arrives, or if it fails,
  no `?lang=` is sent, so an English-only server never receives `?lang=ko`. The choice is
  kept in `localStorage` (`locus.lang`), the ko | en toggle sits in the top bar, and a
  switch re-reads the screen; a late answer in the previous language is dropped.
- **Closed sessions**: `say` re-checks the session inside its transaction, so a session
  closed while the LLM answered gains no lines (409). The dialogue panel of a closed session
  reads `GET .../history` and shows it read-only.
- **Translation cleanup**: regenerating a region purges the translations of the rumors it
  deleted. The six world-replace routes (`build`, `build/upload`, `file`, `file/upload`,
  `demo/{name}`, `demo/{name}/build`) purge the old world's canonical-knowledge translations
  when the world was actually replaced, open sessions or not. A warm-up already in flight can
  leave one harmless row behind, which the next purge removes. A failed purge is logged and
  never fails the request. **Known gap**: the CLI (`locus world build|import|demo` with a
  replace) builds no localization container and purges nothing. Those orphan rows go away
  with the next API-side replace of that world.
- **Accepted risks** (local single-player demo, no auth): the player's text goes into the
  prompt as is. The guard is the system prompt's knowledge boundary plus the length cap, so a
  crafted line can still make the NPC invent things outside its knowledge. Because recent
  lines are replayed, a poisoned answer can persist for the rest of that conversation. No
  stored data outside the conversation changes. `say` has **no rate limit**, and every call
  costs one LLM request. The latency target (`start`, `history`, `npcs` p95 ≤ 100ms, no LLM)
  is operator-run. The offline gate is structural: one `say` = one LLM call and one
  transaction.
  Each `say` holds a worker thread of the API's sync thread pool (40) for up to one LLM
  call; more than 40 slow calls at once delay other sync routes (U5 review #15, accepted).
- **Tables** (idempotent `init-schema --play` / startup): `conversations` (unique
  `(session_id, npc_id)`; the NPC id is a plain reference, so a conversation outlives an NPC
  removed by an edit: `history` still reads, `say` answers 404) and `messages` (app-stamped
  `created_at`, read in `(created_at, id)` order). No retention policy.

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
- **Frontend (X2/X3)**: Tailwind v4 ("Doodly" paper+ink theme) + self-hosted Gaegu Korean handwriting font (`@fontsource/gaegu`, no CDN). Korean UI labels + timeline i18n (U5: every label is in a ko and an en dictionary in `web/src/i18n.ts`; see the dialogue section for the toggle). Build: `cd web && npm install --legacy-peer-deps && npm run build`.
- **No new infra**: canonical graph unchanged; only additive session-layer `translations` table + response-only ko fields + `region_changes`. Rollback is additive-safe.

## Future Operations (not implemented)
- Containerized app service running uvicorn by default; CI/CD; cloud deploy; monitoring/alerting; backup of Neo4j/OpenSearch/**Postgres** volumes; consensus cache + scaling; managed PostgreSQL / connection pooling.
