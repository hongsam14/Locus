# Operations — Locus (placeholder)

AI-DLC Operations is a **placeholder** stage. For the MVP, operation is local via Docker Compose; no production deploy/monitoring workflow is in scope yet.

## Run (local)
```bash
./scripts/setup-volumes.sh     # create ./data bind-mount dirs (first run; safe to rerun)
cp env.example .env            # REQUIRED passwords: NEO4J_PASSWORD, SESSION_DB_PASSWORD
                               #   (no insecure defaults; compose fails fast if unset)
                               #   OPENAI_API_KEY is optional (see "Without OPENAI_API_KEY")

docker compose --profile service up -d --build  # infra + app (uvicorn :8000, runs init-schema then serves) + web (:3000)
docker compose up -d                            # or infra only: neo4j + opensearch + postgres (bind-mounted ./data)
docker compose --profile tools up -d dashboard  # + OpenSearch Dashboards (:5601)
docker compose --profile service --profile tools down   # stop everything
```
- Profiles (U8): default=infra (neo4j + opensearch + postgres), `service`=app+web, `tools`=dashboard. `app` waits for the three infra services to be healthy, `web` for `app`.
- Host dev (no app container): `docker compose up -d` then `uvicorn api.main:app --port 8000` + `cd web && npm run dev`.
- `SESSION_DB_URL` (PostgreSQL) configures the game-session layer; on host use `localhost:5432`, in compose `postgres:5432` (auto-overridden for `app`).

## Typical workflow
1. `locus init-schema` (idempotent).
2. `locus world build --world <id> --inputs <file>` (or `locus world demo --name emberleaf --world <id>` for the LLM-free demo) — a build also distills that world's own
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
- **Demo world without an LLM** — `locus world demo --list`, `locus world demo --name emberleaf --world <id>`; API `GET /api/world/demos`, `POST /api/world/worlds/{id}/demo/{name}`. The packaged World File loads with **0 LLM calls**; the home screen's demo cards use it (U8). The source-based build (`locus world build --world <id> --demo <name>`, `POST .../demo/{name}/build`) still needs `OPENAI_API_KEY`. 〔U8〕 The demos come from a manifest — see the U8 section.
- **Build** — `locus world build --world <id> --inputs <file.json>` (images base64 in `map_images`/`concept_arts`); API `POST /api/world/worlds/{id}/build` (JSON) or `.../build/upload` (multipart fields: `memos`, `maps`, `images` (repeatable), `name`, `description`). `BuildReport.ok` is false only for error-severity warnings (persist failure, unreadable input, zero regions); item-level problems and unresolved names are warnings; `unscoped_knowledge_ids` lists knowledge that found no region; `llm_calls`/`embedding_calls` count that build.
- **Replacing a world** — build/import/demo replace an existing world by default (`replace=true`). Before deleting, the old world is exported to `LOCUS_DATA_DIR/backups/<id>-<UTC>.world.json` (compose: the `locus_data` volume at `/app/data`). Recover with `locus world import --world <id> --file <backup>`. If the world has **open sessions**, the API answers 409 (`open_sessions`, `session_ids`) until `confirm=true`; the CLI exits 1 until `--force`; confirmed/forced replaces close those sessions and list them in `closed_session_ids`.
- **Single worker** — play and the editor read one in-process `WorldCache` per worker; run the API with **one uvicorn worker** (compose does). Writes (build, import, edit, augmentation, prior edit) invalidate it.
- **Without `OPENAI_API_KEY`** 〔U8 정정〕 — the API starts and `/health` reports `ok` (the LLM is not a boundary). `GET /api/capabilities` says `{"llm": false, …}`. The routes that need an LLM answer 503: build (`…/build`, `…/build/upload`, `…/demo/{name}/build`), NPC drafts, rumor generate/regenerate, event suggestion, NPC dialogue `start`/`say`. Everything else works: World File, demo load, world list, the editor, augmentation Q&A (templates), wiki priors, sessions, moves, turns, seeds, GM manual events.
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

## Deeds & spread (Purpose Restructure U6, 2026-10-01)

- **What it does**: the player's arrivals, the things said to an NPC and declared actions become
  *deeds* (session-only, never canonical). When a talk ends, the NPC judges the deeds it saw in this
  stay (one LLM call). A deed it would pass on becomes a rumor in that region, and each turn
  deed rumors move **one hop** along passable connections, more distorted each time.
  The GM sees every deed and can **void** it.
- **Routes**
  - `POST /api/play/sessions/{s}/act?lang=` with `{type: "declare", text}` answers 202.
    The narration arrives with the run result (`result.declaration`).
  - An empty or over-limit declaration is **400**.
  - `GET /api/gm/sessions/{s}/deeds?lang=` lists deeds with names, appraisals, rumors and
    reached regions.
  - `POST /api/gm/sessions/{s}/deeds/{d}/void` holds the GM write lease (409 during a turn),
    is idempotent, and turns off every rumor of the deed, promoted ones included.
- **Who judges**
  - A statement is judged by the NPC who heard it.
  - Arrivals and declarations are judged by every witness the player talked to. Each
    noteworthy judgement seeds its own version.
  - An `end_talk` with no new player line since the last talk judges nothing (0 calls).
  - Leaving a region without talking means its deeds never become rumors.
- **Turn budget order** (`LLM_MAX_CALLS_PER_TURN`, default 8)
  1. The action's own call: narration or appraisal, reserved first.
  2. Spread hops, one call each.
  3. Canonical rumor drafts with what is left.
  - Seeds need no call: the NPC's retelling is the rumor.
  - A failed prep call or a failed hop trips that turn's breaker, so the rest of its LLM
    work is skipped.
  - A budget of 0 gives the fallback narration (a fixed line, the player's words as the record).
- **Worst case per action**: B is the per-call bound, 106s.

  | Action | LLM outage | Slow but successful calls |
  |---|---|---|
  | Declaration or end of talk | ≈ B (prep fails, breaker) | ≤ 8 × B = 848s |
  | Move of k turns | ≤ k × B | ≤ k × 8 × B |

  The background executor is a single FIFO worker, so other sessions wait meanwhile (U4,
  accepted).
- **Spread rules**
  - Reach weight is the best path from the deed's region over passable connections read both
    ways, times the hop. A hop needs reach ≥ `SPREAD_MIN_WEIGHT`.
  - Degree is at least `max(parent, 1 − reach)`.
  - Support is `parent × (0.5 + 0.5 × edge)`. Hops that would be pruned by the next turn are not
    tried.
  - One version reaches a region once. A region takes at most `MAX_SPREAD_PER_REGION_TURN` hops
    per turn.
  - Seeds, hops and canonical drafts share the per-region active cap.
  - Newborn deed rumors skip that turn's decay. Seed support is `birth_support × (1 + salience)`.
- **Never mixed**: canonical rumor chains never extend a deed rumor, so a void reaches
  everything a deed produced. A region regenerate keeps deed rumors.
- **Schema** (idempotent `init-schema --play` / startup)
  - New tables `deeds` and `deed_appraisals` (unique `(deed_id, npc_id)`).
  - Existing tables gain columns, added with the inspector on PostgreSQL and SQLite (old rows
    are kept and read as `canonical`):
    - `session_rumors`: `origin_kind` (default `canonical`), `origin_deed_id` (indexed),
      `origin_appraisal_id`, `spread_from_region_id`
    - `turn_runs`: `lang`, `turns_charged` (default 0), `from_region_id`
    - `deed_appraisals`: `run_id` (indexed; review fix). A turn run that fails before its
      first turn removes its appraisals, including those of earlier deeds.
  - **U4 fix**: the PostgreSQL adapter used to drop `turns_charged` and `from_region_id`, so a
    failed run's turn refund and position restore never happened on PostgreSQL. They are stored
    now.
- **Failed and interrupted runs**
  - A run that fails before any turn advanced deletes its deeds: an undone move's arrival, a
    declaration, a statement, and their appraisals. Their timeline lines stay as an audit trail.
  - A run marked `interrupted` at restart keeps the deeds its prep step committed (accepted).
- **Env** (`env.example`): `SPREAD_MIN_WEIGHT` (0.15), `DEED_SEED_MIN_SALIENCE` (0.5),
  `MAX_SPREAD_PER_REGION_TURN` (1), `DECLARE_MAX_CHARS` (300), `NPC_MAX_DEEDS` (5),
  `APPRAISAL_MAX_DEEDS` (8).
- **Without an LLM**: a declaration is accepted with the fallback narration and recorded, and an
  ended talk judges nothing. Nothing spreads. The GM deed view and void still work.
- **Accepted risks**
  - Player words reach the narration prompt (declaration) and, through the appraisal's summary
    and retelling, other NPCs' prompts and spread prompts.
  - The guards are the material-not-instructions framing and length caps: narration 1,000
    characters, record, summary and retelling 300, slant 40.
  - A crafted line can still steer what an NPC retells. The GM void undoes it.
  - The player log hides appraisal, seed and spread lines on screen only. `GET /log` returns
    everything; its server-side filter is U7.
  - The latency target (`GET deeds` p95 ≤ 100ms with 300 deeds, 600 appraisals and 100 deed
    rumors) is operator-run.

## GM mode & hardening (Purpose Restructure U7, 2026-10-01)

- **GM mode** (Q1=B)
  - The play screen's "GM mode" button opens `/gm/:sessionId`.
  - The GM screen's "Back to play" button returns to `/play/:sessionId`. It shows only for sessions with a player.
  - The GM screen shows the player's name, region and turn, plus a running mark, and rings the player's region on the map.
  - The GM tools are split by feature under `web/src/features/gm/`:
    - `GmHub` holds the state.
    - `ManualTurnPanel`, `EventPanel`, `DistortionPanel`, `RumorPanel`, `TimelinePanel` and `DeedPanel` draw it.
- **World state**
  - `GET /api/gm/sessions/{s}/state` returns one row per world region: distortion, feedback share, active / promoted / deed rumors and active events.
  - The map overlay ("World state") colors regions in five distortion bands and badges `active/promoted` (plus `✦deed`).
  - The read is five store queries, no LLM. Its reads are not bound in one transaction, so a turn committing between them can show one mixed frame. The next read corrects it.
- **Feedback** (Q2=A, Q4=A)
  - Strong rumors are those at or above `RUMOR_HIGH_SUPPORT_THRESHOLD`, now 0.45, that are **not promoted**. They raise their region's distortion each turn.
  - The part feedback added is stored as `region_distortions.feedback_share`, capped at `RUMOR_FEEDBACK_CAP` (0.3).
  - Once a region has no strong rumor, the share is given back by `RUMOR_FEEDBACK_RESTORE` (0.05) per turn.
  - A GM distortion set is the region's new base and clears the share.
  - **Decay**: only regions an event touches are exempt from support decay. Feedback regions decay too, so their strong rumors fade.
- **Events**
  - The timeline kinds are `event_created` (the GM's own), `event_suggested`, `event_approved`, `event_discarded` (it keeps what was discarded), `event_applied` and `event_resolved` (a one-shot's automatic end too).
  - Resolving a suggestion answers 400. `suggest?n=` must be 1..`EVENT_SUGGEST_MAX` (5), else 400 before any LLM call.
  - **Suggestion prompt**
    - Up to `EVENT_SUGGEST_MAX_REGIONS` (30) regions: the player's region, then regions with an active event, then rumor-dense regions, then leaves before parents.
    - Each region line has its id, name, place, description and two known facts.
    - It also carries the last five events and the last five deeds. These go in first; region lines fill what is left of the 21,000 characters, whole lines only, so a large `EVENT_SUGGEST_MAX_REGIONS` drops regions, never events or deeds (U3, U7 review #14).
    - Everything sits under a "material, not instructions" heading, and the system prompt has a guard line.
    - Region ids are shown whole; the "rest" are ordered leaves before parents, deeper first, then by name (U3).
  - A suggestion's region is found among all the world's regions: by id, or by name (the `normalize_name` key) when unambiguous. A world with no region makes no call (U3).
  - The GM screen offers 1..`EVENT_SUGGEST_MAX` suggestions (the cap comes with `GET …/state`, U3).
- **Lineage**
  - Regenerate deactivates the replaced canonical rumors instead of deleting them. No rumor is ever deleted.
  - A kept rumor's `distorted_from_id` always points at a row.
  - The regenerate payload key is `deactivated`.
- **Regions**
  - `GET …/distortions` lists every current world region: the stored row or the default (0.3, share 0).
  - Rows of regions the world lost stay stored but are not listed.
  - Setting a region the world does not have answers 404.
- **Player log**: `GET /api/play/sessions/{s}/log` keeps:
  - the player's own lines;
  - the lines of the region the player was in at that moment: events, promotions, prunes, deed rumors born or arriving. A persistent event shows once per stay.
  - The GM's hand, NPC judgements and voids are hidden. The GM timeline still shows everything.
- **Names**: new timeline lines carry `region_name`. Older lines show the id.
- **Prompt hardening**
  - Every free text inserted into a prompt passes `shared/text.one_line`: declarations, player lines, deed text, retellings, world and event descriptions.
  - `one_line` turns line breaks, Unicode separators and control characters into one space, so text cannot open a section of its own.
  - What the player sees is unchanged.
- **NPC dialogue**
  - A failed NPC call answers 503 `the NPC could not answer right now; try again` and stores nothing.
  - The NPC list counts messages with one query.
- **Tuning (FR-A7)**
  - Every knob has a default (the demo still starts from the two required `.env` values).
  - A bad value fails startup: out of range, broken JSON, an unknown connection kind, or `CONSENSUS_HEARSAY_MIN` above `CONSENSUS_PROPAGATE_MIN`.
  - The new env:
    - `CONSENSUS_PROPAGATE_MIN`, `CONSENSUS_HEARSAY_MIN`
    - `TOPOLOGY_BASE_WEIGHTS` and `TOPOLOGY_TERRAIN_MODIFIERS` (JSON objects that override only the keys they name; NaN or Infinity fails startup, U3)
    - 〔U3 정정〕 `TOPOLOGY_DEFAULT_BASE` was removed: the kinds are an enum of four and an unknown kind is built as `adjacent`, so it was never read (A3-15).
    - `ONTOLOGY_DEDUP_THRESHOLD`
    - `RUMOR_FEEDBACK_CAP`, `RUMOR_FEEDBACK_RESTORE`, `RUMOR_PROMOTION_THRESHOLD`
    - `EVENT_MAX_DELTA`, `EVENT_PROPAGATE_MIN`, `EVENT_SUPPORT_REINFORCE`, `EVENT_SUGGEST_MAX`, `EVENT_SUGGEST_MAX_REGIONS`
- **Schema** (idempotent, both dialects): `region_distortions.feedback_share FLOAT NOT NULL DEFAULT 0` is added to existing databases. Play timestamps read back as UTC on SQLite too.
- **Review fixes** (U7 code review 01, choice A)
  - GM writes now **share** the session with each other: bulk generate/regenerate runs five at once again. A turn still excludes every GM write, and a GM write still waits for no turn (409 during a turn).
  - `locus world build` builds with the same WorldTuning env as the API.
  - GM sliders save only a value the GM moved to; a refused save can be sent again.
  - A failed move's `turn_run_failed` line carries `restored_region_id`, and the player log follows it.
- **Operator checks** (live compose; this host's 7474/7687 belong to another project)
  - Play → GM mode → approve a suggested event → advance three turns → World state shows the distortion spreading from the event region along connections.
  - p95 of `/state`, `/log` and `/distortions` ≤ 100 ms with 3,000 timeline lines, 15 regions and 300 active rumors.

## World editor (Purpose Restructure U3, 2026-10-01)
- **Screens**
  - `/` lists the worlds (name, regions, last edit, open sessions) with [Edit] and [Start session], and [Build from sources]. 〔U8〕 Demo cards from the manifest sit above the list, with or without worlds (no [Load the demo] button).
  - `/editor/:worldId`: the World File bar (save = download, load = replace after a yes, close open sessions after a second yes, build from sources, the "open sessions" band), the map, and the Region / Unscoped / Augment / Wiki tabs.
  - The map has three tools: select/move (a click saves nothing; a drag over 4px saves the position once), add region (click an empty spot), connect (click two regions in turn).
- **Edits** (`/api/world/worlds/{w}/…`, `api/routers/world_editor.py`)
  - An edit replaces the node's properties whole: a cleared field is gone (build and import still merge).
  - A path id that does not match the body is 400; a missing referenced region is 404; a parent that is the region or one of its descendants is 400.
  - A connection is always a pair (a→b, b→a) with one kind, weight, rationale and prior; changing the kind keeps them. A road and a river between the same two regions are two connections.
  - Adding knowledge on a region gives it one DIRECT scope; editing it keeps its scopes; `PUT …/scopes` sets exactly the given regions (an empty list leaves it unscoped).
  - Deleting knowledge — from the inspector, the unscoped list, an augmentation "remove" answer or the undo of an added fact (U8, U3 review S10) — also deletes its search document and its translations. NPC text is never translated.
  - `DELETE /worlds/{w}/nodes/{n}` was removed: deletes go by kind.
- **Region delete** (`GET …/delete-plan`, `DELETE …/regions/{r}`)
  - What happens, in this order: children move under the deleted region's parent; entities lose their location; its scopes go (knowledge stays — an item scoped only there becomes "unscoped"); its NPCs are deleted (search document, then node); both directions of its connections go; then the region.
  - A cut part-way leaves no dangling id, and sending the same delete again finishes it.
  - The router holds the GM lease of every open session of the world over the check and the delete: a session mid-turn is 409 ("turn in progress"), and a region where an open session's player stands is 409 with those session ids.
  - Known limit: a session started, or a GM write made, while the delete runs is not held; such a session may point at the deleted region (the play screen then answers that the player's region no longer exists).
- **Augmentation Q&A**
  - Detectors: gap, low_confidence, wiki_conflict (reads `terrain_kind`), orphan, dangling (a `parent_id`, `located_in`, connection `wiki_prior_ref`, or an id in `derived_from_prior_ids` / `about_entity_ids` that points at nothing — one issue per id), unscoped.
  - A question names its target and offers fixed actions; the answer is applied to the question's target. 20 questions per detection; 30 answers per run.
  - Undo is latest first; it is refused (409) for an undone change, a change that is not the latest, or a target edited outside the run since. Ignore is not in the undo order; an ignored question can be asked again (`unignore`).
  - Runs live in process memory, 20 per world: a restart loses them and the screen offers a new search. A 404 for a target removed meanwhile keeps the run and shows the reason (U8, U3 review #12).
  - Known limit (one designer, A-4; U3 review S16): an answer's change record is the edge difference around the nodes it watches, so a map save made during the answer's embedding call (~1 s) joins that change, and undoing the answer undoes it too.
  - LLM: none needed (template questions, no wiki-conflict check). With one: 5 question rewrites per detection, 20 (knowledge, terrain) checks per detection against priors found by search only (no LLM-made priors), at most 60 calls per run (`llm_budget_exhausted` then).
- **NPC drafts**: `POST …/regions/{r}/npc-drafts` — one LLM call, 0–3 drafts, nothing saved (503 without an LLM, 200 with `failed` when the call fails).
- **Wiki grounds**
  - A build stores the priors its wiki made by LLM fallback (one per distinct query, at most 40 per build), so connection and knowledge references to them stay. The report shows `priors_created`.
  - `GET …/priors`, `GET …/prior-refs` (each prior with what cites it, and cited ids the world lacks), `DELETE …/priors/{p}`.
- **Uploads** (constants in `api/uploads.py`, not env)
  - A request body over 48 MiB is refused with 413 before the route runs (World File routes: 20 MiB).
  - `build/upload`: memos ≤ 20 files of 256 KiB and 60,000 characters each; maps ≤ 5 × 2 MiB (JSON); map images ≤ 4 and concept art ≤ 8, 8 MiB each, PNG/JPEG/WebP by their first bytes (else 422).
- **GM (U7 carry)**: setting a region's distortion also clears that region's contribution of every ACTIVE event (`event_contributions_cleared` on the line), so resolving the event later does not take the region below the GM's value. NaN or Infinity in a GM value is 422.

## Demo · deploy · docs (Purpose Restructure U8, 2026-10-01)
- **Demos are data**
  - `locus/world/demo/worlds/manifest.json` lists the demos: `name`, `title`, `description`, `file` (a World File next to it), `start_region_id`, `credits`, optional `sources` (memos, maps, map images for `world build --demo`). The home cards, `GET /api/world/demos` and `locus world demo --list` read it; no demo name is in the code (TP-U8-6 scans `locus`, `api`, `web/src`).
  - Entries are checked once at assembly; a bad entry is left out with a warning (`DemoWorlds.problems`). `python -c "from locus.world.demo import check_packaged; print(check_packaged())"` prints the problems of the installed package ([] when fine; the CI images job runs it).
  - Adding a demo: put `<name>.world.json` (and its sources) in that folder and add an entry; a reinstall (`pip install .` / the image build) ships it.
  - Old command → new: `world demo --name aldermoor` → `world demo --name emberleaf`; `build-world --demo` (alias) → `world build --demo emberleaf`. The old Aldermoor file lives on only as a test fixture (`tests/fixtures/aldermoor/`).
  - [play now] on a card: load the demo into the world id of its name if it is not there (or on [load fresh]), start a session named "여행자"/"Traveler" at `start_region_id`, open `/play/:id`. Loading never calls an LLM.
- **Event seeds**
  - World File optional section `event_seeds` (format_version stays 1): `id`, `region_id`, `title`, `description`, `category`, `magnitude`, optional `lifecycle`. Stored as `EventSeed` nodes; a region delete removes its seeds (the delete plan lists `seed_ids`).
  - `GET /api/gm/sessions/{sid}/seeds` (each with its region name and running event id) and `POST /api/gm/sessions/{sid}/seeds/{seed_id}/start` → 201 with an ACTIVE event (no LLM), under the GM lease. A second start while its event runs is 409; after a resolve it starts again. The timeline line reads "씨앗 사건 시작: {title}".
  - Hosts running the API outside compose: run `locus init-schema --world` once after upgrading (the `EventSeed` constraint). Compose runs `init-schema` on every start.
- **Keyless** — `GET /api/capabilities` → `{llm, vlm, embedding}` from the assembled providers. The home, editor and GM screens show one line when `llm` is false and turn the LLM buttons off with "LLM 키가 필요합니다"; a failed read turns nothing off; a 503 naming the provider reads the same.
- **Ports and profiles**
  - Infra ports bind 127.0.0.1 and take `NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `OPENSEARCH_PORT`, `SESSION_DB_PORT`, `DASHBOARD_PORT` from `.env` (defaults unchanged). `API_PORT`/`WEB_PORT` stay open on all addresses.
  - A host where 7474/7687 are taken (another Neo4j): add `NEO4J_HTTP_PORT=17474` and `NEO4J_BOLT_PORT=17687` to `.env`; with host uvicorn also set `NEO4J_URI=bolt://localhost:17687`.
  - `web` has a healthcheck (`wget -q --spider http://127.0.0.1/`).
- **CI** — `.github/workflows/ci.yml`: backend (ruff, black, pytest with a printed hypothesis seed: re-run a failure with `pytest --hypothesis-seed=<seed>`), frontend (`npm ci`, tsc, vitest), audit (`npm audit --omit=dev --audit-level=moderate`), images (both builds, `check_packaged()` in the installed package, `import api.main`). No secrets, no services. mypy stays local (baseline 11).
- **Live scenario** — `python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf` after `docker compose --profile service up -d --build`. Standard library only, not in CI. It **replaces** the target world, then walks the demo: health and capabilities, demo load (12 regions), a session at the harbor, a move, a talk, a declaration, the blight seed, the walk back, the one-hop deed rumor, a wait, the two regions' distortion, a talk about the blight, no deed rumor in Ironcrag by T+2, the world state. Each step prints PASS/FAIL/SKIP (LLM steps SKIP without a key; the spread steps SKIP when the witnesses did not seed the deed); any FAIL exits 1. Its first step is the compose check (Infra R-01).
- **Known gap (A8-10)** — replacing a world from the CLI (`world import`/`world demo`/`world build`) does not purge its translations; the API paths (and so the screens) do. Stale rows are filtered by source hash on read; they only take space.
- **License** — MIT (`LICENSE`, `pyproject.toml`). The demo world's credits are in the manifest and the README.

## Web UI
```bash
cd web && npm ci     # the lock as committed (no --legacy-peer-deps needed)
npm run dev          # dev server :5173, proxies /api -> :8000 (run uvicorn separately)
npm run build        # tsc + vite build -> web/dist
```
- In compose the `web` service builds this with `npm ci` on `node:22-alpine` and serves `dist/` from nginx, which proxies `/api` to `app:8000` (`client_max_body_size 49m`, read timeout 130 s) — U8.
- Screens: `/` (demo cards, world list), `/editor/:worldId`, `/gm/:sessionId`, `/play/:sessionId`. See `web/README.md`.

## Observability (current)
- Structured stdout from CLI/app; container healthchecks (Neo4j HTTP, OpenSearch cluster health, **Postgres `pg_isready`**).
- Dashboards/alerting: out of scope (future Operations expansion).

## Localization & UX (UX Improvement cycle, 2026-08-11)
- **Translation (X1)**: LLM-backed ko translation of session content (rumors/events) + canonical Knowledge, cached in the PostgreSQL `translations` table (created by `init-schema`, additive). Reuses the OpenAI provider. Config: `TRANSLATION_ENABLED`(기본 true), `TRANSLATION_TARGET_LANG`(ko). **Reads never block on the LLM** — cache-only on read, misses warm on a background thread; so the first view of new content may show English, then Korean on refetch. Disabled → all English (graceful).
- **Turn-change notifications**: `advance-turn` returns `region_changes` (per-region promoted/demoted/pruned/events/added); the web SessionPanel shows one auto-dismiss toast per changed region.
- **Regenerate preserves promoted**: `regenerate_region` keeps promoted rumors and reseeds the rest from **canonical knowledge only** (promoted rumors are not reused as chain seeds). Applies to per-region and "전체 재생성".
- **Frontend (X2/X3)**: Tailwind v4 ("Doodly" paper+ink theme) + self-hosted Gaegu Korean handwriting font (`@fontsource/gaegu`, no CDN). Korean UI labels + timeline i18n (U5: every label is in a ko and an en dictionary in `web/src/i18n.ts`; see the dialogue section for the toggle). Build: `cd web && npm ci && npm run build` (U8: the peer conflict is gone).
- **No new infra**: canonical graph unchanged; only additive session-layer `translations` table + response-only ko fields + `region_changes`. Rollback is additive-safe.

## Future Operations (not implemented)
- CD and cloud deploy (U8 added the app/web containers and a CI workflow); monitoring/alerting; backup of Neo4j/OpenSearch/**Postgres** volumes; consensus cache + scaling; managed PostgreSQL / connection pooling.
