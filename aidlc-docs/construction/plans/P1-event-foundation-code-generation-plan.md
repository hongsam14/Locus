# P1 Event Foundation — Code Generation Plan

> 단위: P1. 입력: `construction/P1-event-foundation/functional-design/*`, `application-design/rumor-phase2/*`.
> Brownfield: 기존 파일 **in-place 수정**(복사본 금지). 모든 변경 additive — 캐노니컬 불변, Phase 1 회귀 0.
> 스토리(요구사항): FR-P1.1/1.2/1.3, FR-P2.1, FR-P2.4, FR-P6.1(enum), NFR-P1/P5/P6.
> 워크스페이스 루트: `/home/thinkpad/Desktop/src/Locus` (Python 3.11, pydantic v2, SQLAlchemy, FastAPI).

## 단위 컨텍스트
- **의존**: 없음(기존 세션 레이어 기반). P2/P3가 P1에 의존.
- **소유 엔티티**: SessionEvent / `session_events` 테이블 / Event 관련 enums.
- **인터페이스(후속 단위용)**: SessionRepository Event CRUD, GameMasterService 수동 event 메서드, 4 API 라우트.
- **비고**: EventSuggester/dynamics/advance_turn 확장·main.py EventSuggester 주입은 **P2**. P1은 main.py/CLI 변경 불필요(ensure_schema가 metadata로 신규 테이블 자동 생성).

## 단계

- [x] **Step 1 — NFR-light 노트**: `aidlc-docs/construction/P1-event-foundation/nfr/nfr-light.md` 작성(NFR-P1 포트 additive / NFR-P5 회귀 / NFR-P6 인프라 무변경·ensure_schema additive). (문서)
- [x] **Step 2 — Models (business logic)**: `locus/session/models.py` 수정 — `EventCategory`/`EventLifecycle`/`EventStatus` enums, `CATEGORY_DEFAULT_LIFECYCLE` + `default_lifecycle()`, `SessionEvent` 모델, `TimelineKind`에 `EVENT_CREATED`/`EVENT_APPLIED`/`EVENT_RESOLVED` 추가. (FR-P1.2, FR-P2.4, FR-P6.1 / BR-P1-1,3,5,12,13)
- [x] **Step 3 — Repository port**: `locus/session/repository.py` 수정 — `create_event`/`get_event`/`list_events`/`update_event`/`delete_event` 시그니처 추가(기존 불변). (FR-P1.3)
- [x] **Step 4 — In-memory adapter**: `locus/session/memory_repo.py` 수정 — Event 저장(dict[session_id][event_id]) + CRUD, 정렬(created_turn,id), 세션 격리, deepcopy. (FR-P1.3 / BR-P1-9)
- [x] **Step 5 — Postgres adapter**: `locus/storage/postgres_session_repo.py` 수정 — `session_events` Table(하이브리드: 정규 컬럼+인덱스, contributions/provenance=`_JSON`) + Event CRUD + `_row_to_event`/`_event_to_values`. ensure_schema 자동 포함. (FR-P1.3 / BR-P1-10)
- [x] **Step 6 — Service (business logic)**: `locus/session/game_master.py` 수정 — `create_event`/`list_events`/`resolve_event`(상태전이)/`discard_event` + `_require_region(world_id, region_id)` 헬퍼 + EVENT_* 타임라인. (FR-P2.1, FR-P3.6 부분 / BR-P1-2,4,6,7,8,11)
- [x] **Step 7 — API layer**: `api/routers/session.py` 수정 — `POST /sessions/{sid}/events`, `GET /sessions/{sid}/events?status=`, `POST /sessions/{sid}/events/{eid}/resolve`, `DELETE /sessions/{sid}/events/{eid}` + Pydantic body(EventCreate) + 에러 매핑(404/409/400). (FR-P2.1)
- [x] **Step 8 — Exports**: `locus/session/__init__.py` 수정 — SessionEvent/EventCategory/EventLifecycle/EventStatus/CATEGORY_DEFAULT_LIFECYCLE export.
- [x] **Step 9 — Tests (business logic)**: `tests/` — 모델/enum/기본 lifecycle(+override), magnitude 범위(PBT round-trip 직렬화). 
- [x] **Step 10 — Tests (repository)**: Event CRUD round-trip(in-memory + postgres SQLite 엔진), 정렬·status 필터·세션 격리·delete·ensure_schema 멱등.
- [x] **Step 11 — Tests (service+API)**: create(region 검증 404)/list/resolve(idempotent)/discard(상태 제약)/닫힌 세션 409; API 라우트 스모크(create/list/resolve/delete). Phase 1 회귀 확인.
- [x] **Step 12 — Code summary**: `aidlc-docs/construction/P1-event-foundation/code/code-summary.md` (수정/생성 파일, 테스트 수, story 매핑).

## 검증 게이트(생성 후, Build&Test에서 정식)
- `pytest`(기존 177 + 신규 GREEN), `ruff`/`black` 클린, `python -m compileall locus api` 클린.
- buildWiki/잔재 없음 확인; 세션 라우트 마운트 수 증가 확인.

## 스토리 추적
- FR-P1.1/1.2/1.3 → Step 2,3,4,5. FR-P2.1 → Step 6,7. FR-P2.4 → Step 2,6. FR-P6.1 → Step 2. NFR-P1/P5/P6 → Step 1,3,5.
