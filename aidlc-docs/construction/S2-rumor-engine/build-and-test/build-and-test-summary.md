# S2 (Rumor Engine) — Build & Test Summary

Cycle: Rumor Distortion / Game Session, Phase 1. Date 2026-06-15. Scope: FR-R2/R3/R4/R5.

## Build Status
- **Backend**: no new dependency (reuses S1 stack + existing LLMProvider). Package imports; `api.main:app` mounts 11 session routes (5 S1 + 6 S2). `SourceKind.SESSION_RUMOR` added (additive enum).
- **Infra**: unchanged (S1 PostgreSQL + Neo4j/OpenSearch). No compose/pyproject change.
- **Artifacts**: `locus/session/{rumor_generator,promotion,game_master,query}.py`, pure `canonical_known` in `locus/query/engine.py`, extended `api/routers/session.py`.

## Test Execution Summary

### Unit / Component Tests (offline — LLM + DB mocked/in-memory)
- **Backend (pytest)**: **177 passed**, 0 failed · coverage ≈ 84% · ruff ✅ · black ✅ · PBT (Partial) ✅.
- Was 153 (S1) → +24 S2 tests.
- **S2 tests**:
  - `tests/session/test_rumor_generator.py` — chain length, `distorted_from` lineage/kind, `confidence=src*(1-degree)`, graceful chain-stop on LLM failure.
  - `tests/session/test_promotion.py` — promote/demote transitions, inclusive threshold, idempotence + **PBT**.
  - `tests/session/test_game_master.py` — generate (source collection + chain), regenerate (delete-all incl. promoted), adjust_support (clamp), advance_turn (promote→demote across turns, turn++, timeline kinds), closed-session reject, missing-session.
  - `tests/session/test_session_query.py` — drops propagated + auto-rumor, keeps direct, promoted rumor direct-like in `unique_ids`, missing session/region.
  - `tests/session/test_session_api.py` — S2 flow (generate→support→advance→knowledge), distortion/regen, 404/409.
  - `tests/query/test_query.py` — `canonical_known` + `view_items` regression guard.
- New modules coverage: rumor_generator/promotion/query 100%, game_master 97%.
- **Status**: ✅ PASS

### Integration Tests (live — operator-run, requires Docker PostgreSQL + OPENAI_API_KEY)
See scenarios below. **Status**: ⏳ PENDING operator run.

## Live Integration Scenarios (operator)

Prereq: `docker compose up -d` (+postgres) · `.env` with `OPENAI_API_KEY` · `locus build-world --world demo --demo` · `uvicorn api.main:app`. Start a session: `POST /api/session/worlds/demo/sessions` → `{sid}`.

- **S2-A — Rumor generation (LLM)**: `POST /api/session/sessions/{sid}/regions/{rid}/rumors` → list of rumors. Verify a degree chain (ascending `distortion_degree`), `distorted_from` lineage (step≥1 kind=rumor), `confidence` decreasing, `statement` actually distorted by LLM. GENERATE timeline entry present. [FR-R2]
- **S2-B — Distortion controls chain**: `PUT …/regions/{rid}/distortion {degree:0.8}` then generate → stronger degrees `[0.27,0.53,0.8]`; vs a low-distortion region → weaker. [FR-R2.5, Q1]
- **S2-C — Support + promotion**: `PUT …/rumors/{rid}/support {support:0.9}`; `POST …/advance-turn` → `promoted_ids` includes it, `turn`→1; PROMOTE + ADVANCE_TURN in timeline. Then drop support `<0.6`, advance again → `demoted_ids`. [FR-R3]
- **S2-D — NPC session query**: `GET …/regions/{rid}/knowledge` → items include direct Knowledge + promoted rumor (direct-like, `is_rumor=true`) + other rumors; **no `propagated` / auto-rumor** items. Promoted rumor id in `unique_ids`. [FR-R5.1]
- **S2-E — Regenerate**: `POST …/rumors/regen` → old region rumors (incl. promoted) gone, new set created, REGENERATE timeline. [FR-R2.7, Q4]
- **S2-F — Graceful LLM failure**: with an invalid `OPENAI_API_KEY`, generate → partial/empty result, no 500 crash, session/turn still operable. [NFR-R4]
- **S2-G — Canonical isolation**: confirm Neo4j node counts unchanged after generation/promotion (session writes never touch canonical). [NFR-R2]
- **S2-H — Non-session regression**: canonical `GET /api/query/...` unchanged (propagated still present there). [FR-R5.2]

## Requirement coverage
- **FR-R2** → RumorGenerator + generate_rumors (offline + S2-A/B/E). **FR-R3** → PromotionPolicy + adjust_support/advance_turn (offline + S2-C). **FR-R4** → GameMaster turns + timeline (offline + S2-C). **FR-R5** → SessionQueryEngine + canonical_known (offline + S2-D/H).
- **NFR-R2** isolation → S2-G. **NFR-R4** graceful → S2-F. **NFR-R5** PBT → promotion. **NFR-R6** regression → full suite GREEN, QueryEngine untouched.

## Overall Status
✅ **Offline GREEN (177 tests, ruff/black clean).** Live LLM+PostgreSQL scenarios pending operator run. Canonical layer unchanged. Ready for S3 (Web UI).
