# P2 Dynamic Engine — Code Generation Plan

> 단위: P2. 입력: `construction/P2-dynamic-engine/functional-design/*`. Brownfield in-place(복사본 금지). additive — 캐노니컬 불변, Phase 1 + P1 회귀 0.
> 스토리: FR-P2.2/2.3, FR-P3, FR-P4, FR-P5, FR-P6.2, FR-P7(불변 확인); NFR-P2/P3/P4/P5.
> 의존: P1(SessionEvent/Event CRUD/status enum). 워크스페이스 루트: `/home/thinkpad/Desktop/src/Locus`.

## 단위 컨텍스트
- **소유**: dynamics 순수 로직, EventSuggester(LLM), advance_turn 통합, suggest/approve, resolve 복원.
- **인터페이스(P3용)**: suggest-events/approve API, advance-turn 확장 결과(TurnResult), SessionEvent status 흐름.
- **결정**: FD-P2 all A (MAX_EVENT_DELTA=0.3 / min_weight=0.15 / one_shot 영구 / support ±0.1/−0.05 / append / suggest n graceful).

## 단계
- [x] **Step 1 — NFR-light 노트**: `construction/P2-dynamic-engine/nfr/nfr-light.md` (NFR-P2 격리 / NFR-P3 LLM graceful / NFR-P4 결정론·PBT / NFR-P5 회귀).
- [x] **Step 2 — dynamics (pure)**: `locus/session/dynamics.py`(신규) — 상수 + `distortion_delta`/`propagate_delta`(best_path_weights)/`apply_deltas`/`restore_contributions`/`evolve_support` + `_clamp`. (FR-P3.1/3.2/3.4, FR-P5.1 / BR-P2-1,2,3,5,8,12)
- [x] **Step 3 — EventSuggester (LLM)**: `locus/session/event_suggester.py`(신규) — `EventDraft`/`EventDraftList` + `EventSuggester.suggest`(graceful). (FR-P2.2 / BR-P2-10,11)
- [x] **Step 4 — Service 확장**: `locus/session/game_master.py` — 생성자 `suggester=None` 추가; `advance_turn` 6단계 시퀀스(이벤트 적용+전파+누적·소문 append·support 진화·승격/강등·one_shot resolve·timeline); `resolve_event`에 contributions 복원 추가; `suggest_events`/`approve_event`; `TurnResult` +applied_event_ids/+resolved_event_ids; `_merge_add` 헬퍼. (FR-P2.3, P3, P4, P5, P6.2 / BR-P2-4,5,6,7,9,13,14,16)
- [x] **Step 5 — API**: `api/routers/session.py` — `POST …/suggest-events?n=`, `POST …/events/{eid}/approve`(+ValueError→409/400). advance-turn 기존 라우트(확장 결과 자동). (FR-P2.2/2.3)
- [x] **Step 6 — Wiring**: `api/main.py` — `GameMasterService(..., suggester=EventSuggester(llm))` 주입(line 82). (NFR-P3)
- [x] **Step 7 — Exports**: `locus/session/__init__.py` — `EventSuggester`/`EventDraft` + dynamics 주요 심볼/상수 export.
- [x] **Step 8 — Tests (dynamics, PBT)**: `tests/session/test_dynamics.py` — delta 범위·단조, propagate 임계/감쇠, apply/restore 역대칭(clamp 내), evolve_support 부호. hypothesis(Partial).
- [x] **Step 9 — Tests (service)**: `tests/session/test_advance_turn.py` — 통합 시퀀스(적용→소문 append 보존→support→승격/강등→one_shot resolve), persistent 누적 다턴+해소 복원, 전파 이웃 distortion만, applied/resolved ids, suggest(graceful/region 검증)/approve 전이, 닫힌 세션 가드, Phase 1 회귀(기존 advance_turn 동작).
- [x] **Step 10 — Tests (API)**: `tests/session/test_session_api.py` 확장 — suggest-events/approve/advance-turn 확장 흐름 + 상태코드.
- [x] **Step 11 — Code summary**: `construction/P2-dynamic-engine/code/code-summary.md`.

## 검증 게이트
- `pytest`(194 + 신규 GREEN), `ruff`/`black` 클린, `compileall locus api` 클린. 세션 라우트 +2(suggest/approve).
- Phase 1/P1 회귀 0; NPC 쿼리·수동 소문 경로 불변.

## 리스크/주의
- advance_turn 재작성 시 기존 promotion/turn 동작 보존(회귀 테스트 우선). 소문 append는 기존 `_generate_for_region` 재사용(wipe 없음).
- EventSuggester None 경로(테스트/미주입) graceful.
