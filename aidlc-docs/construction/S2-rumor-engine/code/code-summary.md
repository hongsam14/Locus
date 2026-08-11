# S2 (Rumor Engine) — Code Summary

Executed 2026-06-15. **177 backend tests GREEN** (was 153; +24 S2 tests), ruff + black clean. Offline (LLM + DB mocked/in-memory). S1 models/port unchanged; canonical layer read-only.

## New modules `locus/session/`
- **`rumor_generator.py`** — `RumorDraft(statement)` (LLM structured output) + `RumorGenerator.generate_chain(...)`: ascending-degree chain, text lineage (`distorted_from` step i→i-1, kind=rumor), `confidence=source_conf*(1-degree)`, `support=0`, graceful (LLM failure stops chain, keeps prefix). `SourceKind.SESSION_RUMOR` added (additive enum).
- **`promotion.py`** — `PromotionResult` + pure `evaluate(rumors, threshold=0.6)` returning promote/demote **transitions** (idempotent). PBT-tested.
- **`game_master.py`** — `GameMasterService` + `TurnResult` + `SessionClosedError`. Actions: `generate_rumors` (sources = direct + propagated + existing session rumors, degrees `[d/3,2d/3,d]` from region distortion), `regenerate_region` (delete-all incl. promoted, then regenerate), `adjust_support`, `set_region_distortion`, `advance_turn` (apply promote/demote, bump turn). Each action = exactly one TimelineEntry. Closed-session writes → `SessionClosedError`.
- **`query.py`** — `SessionQueryEngine.knowledge_for_region`: `canonical_known(view)` (direct+inherited+global; drops propagated + auto-rumor) overlaid with session rumors — promoted as direct-like `KnowledgeView(scope=direct, is_rumor=True)` in `unique_ids`, others supplementary.

## Additive helper (canonical layer unchanged)
- **`locus/query/engine.py`** — pure `canonical_known(view)` added; `QueryEngine` class/methods untouched (NFR-R6).

## API + wiring
- **`api/routers/session.py`** — +6 routes: generate / regen / support (PUT body) / distortion (PUT body) / advance-turn / knowledge. 404 (missing session/region) · 409 (closed session) · 422 (body validation).
- **`api/main.py`** — wires `game_master`=GameMasterService(session_repo, RumorGenerator(llm), loader), `session_query`=SessionQueryEngine(session_repo, loader); `_STATE_KEYS` extended.
- **`locus/session/__init__.py`** — exports S2 symbols.

## Tests added (`tests/session/`, `tests/query/`)
- `test_rumor_generator.py` (chain/lineage/confidence/graceful), `test_promotion.py` (transitions + PBT), `test_game_master.py` (generate/regenerate/support/advance-turn promote+demote/timeline/closed/missing), `test_session_query.py` (drop propagated+auto-rumor, promoted direct-like), `test_session_api.py` (+S2 flow + 404/409), `test_query.py` (+canonical_known + view_items regression guard).

## Verification
- **177 backend pytest GREEN**, ruff + black clean. New modules: rumor_generator/promotion/query 100%, game_master 97% cov.
- 11 session routes mounted (5 S1 + 6 S2). Canonical/S1 tests unaffected (regression 0).

## Deferred to S3 (Web UI)
Session create/select/close UI, "소문 생성" 버튼 + support/distortion 표시 + 승격 상태, 과거 세션·타임라인 열람, dead `buildWiki()` 정리. S2 API is the contract.
