# Component Methods — Rumor Distortion / Game Session (Phase 1)

메서드 시그니처(상세 비즈니스 규칙은 per-unit Functional Design). 타입은 의도 표현.

## SessionRepository (포트, C2)
```
ensure_schema() -> None
# sessions
create_session(world_id: str) -> GameSession
get_session(session_id: str) -> GameSession | None
list_sessions(world_id: str) -> list[GameSession]
close_session(session_id: str) -> GameSession
bump_turn(session_id: str) -> int                      # turn += 1, returns new turn
# rumors
upsert_rumor(rumor: SessionRumor) -> SessionRumor
get_rumor(session_id: str, rumor_id: str) -> SessionRumor | None
list_rumors(session_id: str, region_id: str | None = None) -> list[SessionRumor]
delete_rumor(session_id: str, rumor_id: str) -> None
# region distortion
set_region_distortion(session_id: str, region_id: str, degree: float) -> None
get_region_distortion(session_id: str, region_id: str) -> float | None
list_region_distortions(session_id: str) -> list[RegionDistortion]
# timeline
append_timeline(entry: TimelineEntry) -> TimelineEntry
list_timeline(session_id: str) -> list[TimelineEntry]   # ordered by turn, then created_at
# lifecycle
connect()/disconnect()/health_check()
```

## RumorGenerator (C5)
```
generate_chain(source_text: str, source_id: str, source_kind: str, region_id: str,
               session_id: str, degrees: list[float]) -> list[SessionRumor]
# one SessionRumor per degree; each may chain distorted_from to the previous (FR-R2.3).
# confidence = source_confidence * (1 - degree) (FR-R2.6); LLM rewrites text per degree (FR-R2.4); graceful.
```
Schema: `RumorDraft(statement: str)` (structured output per degree).

## PromotionPolicy (C6, 순수)
```
evaluate(rumors: list[SessionRumor], threshold: float) -> PromotionResult
# PromotionResult: promoted_ids, demoted_ids (support>=threshold -> promote; else demote if was promoted)
```

## GameMasterService (C7)
```
generate_rumors(session_id: str, region_id: str, *, degrees: list[float] | None = None) -> list[SessionRumor]
   # reads canonical knowledge for region (+ existing session rumors as possible sources),
   # uses region distortion as base; calls RumorGenerator; persists; appends GENERATE timeline.
regenerate_region(session_id: str, region_id: str) -> list[SessionRumor]   # drop+regenerate; REGENERATE timeline
adjust_support(session_id: str, rumor_id: str, support: float) -> SessionRumor   # ADJUST_SUPPORT timeline
set_region_distortion(session_id: str, region_id: str, degree: float) -> None    # SET_DISTORTION timeline
advance_turn(session_id: str, *, promotion_threshold: float = 0.6) -> TurnResult
   # PromotionPolicy.evaluate -> apply promoted/demoted flags; bump_turn; append PROMOTE/DEMOTE + ADVANCE_TURN timeline
```

## SessionService (C8)
```
start_session(world_id: str) -> GameSession
close_session(session_id: str) -> GameSession
get_session(session_id: str) -> GameSession
list_sessions(world_id: str) -> list[GameSession]
get_timeline(session_id: str) -> list[TimelineEntry]
```

## SessionQueryEngine (C9)
```
knowledge_for_region(session_id: str, region_id: str) -> QueryResult
   # canonical QueryEngine view: keep direct + inherited + global Knowledge; DROP propagated + auto-rumor.
   # overlay session: promoted SessionRumor -> KnowledgeView(scope_type=DIRECT-like), other rumors -> rumor views.
   # NPC sees Knowledge(+promoted) + Rumor only (FR-R5.1).
```

## SessionRumor LLM schema (C5)
```
RumorDraft(statement: str)     # the distorted text for a given degree
```

## API Router (C10) — routes
```
POST   /api/session/worlds/{world_id}/sessions                 -> GameSession        (start)
GET    /api/session/worlds/{world_id}/sessions                 -> list[GameSession]  (history)
GET    /api/session/sessions/{session_id}                      -> GameSession
POST   /api/session/sessions/{session_id}/close                -> GameSession
GET    /api/session/sessions/{session_id}/timeline             -> list[TimelineEntry]
POST   /api/session/sessions/{session_id}/regions/{region_id}/rumors        -> list[SessionRumor]  (generate)
POST   /api/session/sessions/{session_id}/regions/{region_id}/rumors:regen  -> list[SessionRumor]
PUT    /api/session/sessions/{session_id}/rumors/{rumor_id}/support         -> SessionRumor
PUT    /api/session/sessions/{session_id}/regions/{region_id}/distortion    -> RegionDistortion
POST   /api/session/sessions/{session_id}/advance-turn                      -> TurnResult
GET    /api/session/sessions/{session_id}/regions/{region_id}/knowledge     -> QueryResult  (NPC view)
```
(정확한 경로/모델은 per-unit FD에서 확정.)
