# P1 Event Foundation — Code Summary

> 모든 변경 additive — 캐노니컬 불변, Phase 1 회귀 0. 오프라인 GREEN.

## 수정된 파일 (brownfield in-place)
- `locus/models/enums.py` — `SourceKind.SESSION_EVENT` 추가.
- `locus/session/models.py` — `EventCategory`/`EventLifecycle`/`EventStatus` enums, `CATEGORY_DEFAULT_LIFECYCLE` + `default_lifecycle()`, `SessionEvent` 모델, `TimelineKind`에 `EVENT_CREATED`/`EVENT_APPLIED`/`EVENT_RESOLVED`.
- `locus/session/repository.py` — 포트에 Event CRUD 5메서드(create/get/list/update/delete) 추가.
- `locus/session/memory_repo.py` — in-memory Event 저장(`_events`) + CRUD(정렬 created_turn,id / 세션 격리 / deepcopy).
- `locus/storage/postgres_session_repo.py` — `session_events` Table(하이브리드: 정규 컬럼+인덱스, contributions/provenance `_JSON`) + Event CRUD + `_event_to_values`/`_row_to_event`/`_enum_value`; `Enum` import.
- `locus/session/game_master.py` — `create_event`/`list_events`/`resolve_event`(상태전이)/`discard_event` + `_require_region` 헬퍼 + EVENT_* 타임라인.
- `api/routers/session.py` — `EventCreate` body + 4 라우트(POST/GET events, POST resolve, DELETE event); ValueError→400.
- `locus/session/__init__.py` — Event 심볼 export.

## 생성된 파일
- `tests/session/test_events.py` — 모델/enum/default_lifecycle/직렬화 + 서비스(create/list/resolve idempotent/discard/닫힌 세션 가드/region 검증/클램프). (15 tests)
- 확장 테스트: `tests/session/test_repository_contract.py`(+event CRUD/status 필터/격리), `tests/storage/test_postgres_session_repo.py`(+event roundtrip/JSONB contributions/필터), `tests/session/test_session_api.py`(+event API flow/검증).

## 검증 결과 (오프라인)
- **pytest: 194 passed** (기존 177 + 신규 17). 
- ruff/black 클린, `compileall locus api` 클린.
- 세션 라우트 16(=13 경로, P1이 4 라우트 추가). Phase 1 회귀 0.
- Postgres 어댑터는 SQLite 엔진으로 오프라인 검증(라이브 PG는 operator-run/Build&Test).

## 스토리 커버리지
- FR-P1.1/1.2/1.3 ✅(모델/포트/어댑터/스키마) · FR-P2.1 ✅(수동 create+API) · FR-P2.4 ✅(default_lifecycle+override) · FR-P6.1 ✅(TimelineKind EVENT_*) · NFR-P1/P5/P6 ✅.
- P2 인계: distortion 적용/복원(resolve에 추가), EventSuggester(suggested/llm), advance_turn 통합, contributions 채움.
