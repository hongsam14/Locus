# P2 Dynamic Engine — Code Summary

> additive — 캐노니컬 불변, Phase 1 + P1 회귀 0. 오프라인 GREEN.

## 생성된 파일
- `locus/session/dynamics.py` — 순수 로직 + 상수: `distortion_delta`/`propagate_delta`(best_path_weights 재사용)/`apply_deltas`/`restore_contributions`/`evolve_support`/`merge_add`. `MAX_EVENT_DELTA=0.3`, `PROPAGATE_MIN_WEIGHT=0.15`, `SUPPORT_REINFORCE=0.1`, `SUPPORT_DECAY=0.05`.
- `locus/session/event_suggester.py` — `EventDraft`/`EventDraftList` + `EventSuggester.suggest`(graceful → []).
- `tests/session/test_dynamics.py` — 순수 함수 + PBT(hypothesis Partial): delta 범위/단조·clamp, propagate 임계/감쇠, apply↔restore 역대칭, evolve_support 부호/범위, merge_add.
- `tests/session/test_advance_turn.py` — advance_turn 통합(적용+전파, one_shot 자동 resolve / persistent 누적+해소 복원, 소문 append 보존, support 진화, no-event 회귀), suggest/approve 흐름(graceful, region 검증, 닫힌 세션 가드).

## 수정된 파일 (in-place)
- `locus/session/game_master.py` — 생성자 `suggester=None`; `TurnResult` +`applied_event_ids`/`resolved_event_ids`; `advance_turn` 6단계 재작성; `_apply_active_events` 헬퍼; `resolve_event`에 `restore_contributions` 복원; `suggest_events`/`approve_event`.
- `api/routers/session.py` — `POST …/suggest-events?n=`, `POST …/events/{eid}/approve`(404/409/400 매핑).
- `api/main.py` — `GameMasterService(..., suggester=EventSuggester(llm))` 주입.
- `locus/session/__init__.py` — `EventSuggester`/`EventDraft`/`dynamics` export.

## advance_turn 시퀀스 (구현)
활성 Event 수집 → distortion 갱신(주 대상+전파, persistent 누적 / one_shot 자동 resolve, contributions 기록) → 주 대상 리전 소문 append(기존/support 보존) → support 자동 진화(영향 +0.1 / 그 외 −0.05) → promotion.evaluate 승격/강등 → bump_turn → Timeline(EVENT_APPLIED·PROMOTE/DEMOTE·ADVANCE_TURN).

## 검증 결과 (오프라인)
- **pytest: 218 passed** (194 + 신규 24). ruff/black/compileall 클린.
- 세션 라우트 +2(suggest-events, approve) → event 관련 5 경로.
- Phase 1/P1 회귀 0(기존 advance_turn 승격/턴 동작 보존: `test_game_master.py`·`test_advance_turn_no_events_*` GREEN). NPC 쿼리/수동 소문 경로 불변.
- 결정론(dynamics PBT) + LLM graceful(suggester 없음/실패 → []) 확인.

## 스토리 커버리지
- FR-P2.2/2.3 ✅(suggest/approve) · FR-P3.1~3.6 ✅(delta/전파/누적/one_shot/복원) · FR-P4.1/4.2/4.3 ✅(append 보존/이웃 distortion만) · FR-P5.1/5.2/5.3 ✅(support 진화+승격) · FR-P6.2 ✅(TurnResult) · FR-P7 ✅(NPC 불변) · NFR-P2/P3/P4/P5 ✅.
- P3 인계: suggest/approve/resolve/advance-turn(확장) API + SessionEvent status 흐름 → 웹.
