# Phase 2 — Units of Work

> 3 단위, 순차 빌드 P1 → P2 → P3 (AD-P Q6=A, UOW-P Q1=A). 모든 단위 additive — 캐노니컬 불변.
> 코드 조직: 기존 `locus/session/`, `locus/storage/`, `api/routers/`, `web/src/` 내 additive(신규 디렉터리 없음).

## P1 — Event Foundation
- **책임**: Event 데이터 계층 + 수동 Event 라이프사이클(엔진 비의존 부분). P1 단독으로 Event 생성/조회/상태전이 검증 가능.
- **컴포넌트**: C1 SessionEvent(model) · C2 enums(EventCategory/Lifecycle/Status) + CATEGORY_DEFAULT_LIFECYCLE + TimelineKind(EVENT_*) · C6 SessionRepository Event CRUD(repository 포트 + memory_repo + postgres_session_repo + ensure_schema `session_events`) · C7 수동 Event API(`POST /events`, `GET /events?status=`, `POST …/events/{eid}/resolve`(상태전이), `DELETE …/events/{eid}`).
- **요구사항**: FR-P1.1/1.2/1.3, FR-P2.1, FR-P2.4(매핑), FR-P6.1(enum).
- **산출물**: `locus/session/models.py`(확장), `repository.py`/`memory_repo.py`/`postgres_session_repo.py`(확장), `api/routers/session.py`(라우트), `main.py` 와이어링, tests.
- **독립 검증**: in-memory repo로 Event CRUD + 상태전이; postgres 어댑터 오프라인(SQLite) 스모크.
- **비고**: `resolve`의 distortion 복원(dynamics)은 P2에서 완성 — P1은 ACTIVE→RESOLVED 상태전이까지.

## P2 — Dynamic Engine
- **책임**: 동적 distortion 진화 + support 자동 진화 + LLM 제안 + advance_turn 통합 시퀀스.
- **컴포넌트**: C3 dynamics(순수: distortion_delta/propagate_delta/apply_deltas/restore_contributions/evolve_support) · C4 EventSuggester(LLM) + EventDraft · C5 GameMasterService 확장(create/suggest/approve/discard/resolve + advance_turn 6단계) · C7 API(`POST …/suggest-events`, `POST …/events/{eid}/approve`, advance-turn 확장) · TurnResult 확장.
- **요구사항**: FR-P2.2/2.3, FR-P3(전체), FR-P4(전체), FR-P5(전체), FR-P6.2, FR-P7(불변 확인).
- **산출물**: `locus/session/dynamics.py`(신규), `event_suggester.py`(신규), `game_master.py`(확장), `api/routers/session.py`(라우트), `main.py`(EventSuggester 주입), `__init__` exports, tests(PBT 포함).
- **독립 검증**: 순수 로직 PBT + mock LLM/in-memory repo로 advance_turn 시퀀스; resolve 복원 완성.
- **의존**: P1(SessionEvent/Event CRUD/status enum).

## P3 — Web UI
- **책임**: GameMaster 허브에 Event 워크플로 노출(풀 UI).
- **컴포넌트**: C8 — SessionPanel 확장(Event 생성 폼·LLM 제안 승인/폐기·활성/해소 Event 목록·해소 버튼·per-region distortion 표시·Timeline event 항목), `api.ts`(신규 메서드), TS 타입(SessionEvent/EventDraft/EventCategory/EventStatus).
- **요구사항**: FR-P8(전체).
- **산출물**: `web/src/` (types, api.ts, SessionPanel, 필요 시 SessionBar/App 보조), vitest.
- **독립 검증**: vitest + tsc + vite build.
- **의존**: P2(advance-turn 확장 결과·event API·TS 계약).

## 요구사항 → 단위 커버리지
- 모든 FR-P1..P8 + NFR-P1..P6이 P1/P2/P3에 할당됨(상세 매트릭스: unit-of-work-story-map.md). 누락 없음.
