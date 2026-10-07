# U1 경계 재정리 — 생성 코드 리뷰 01 (`/code-review`, effort max)

- **대상**: 커밋되지 않은 작업 트리 vs `HEAD` (`locus/`, `api/`, `tests/`, `web/src/`, `Dockerfile`, `.dockerignore`), 164 파일
- **일시**: 2026-09-29T15:05Z 요청 → 16:06Z 결과 (11 finder angles → 40 candidates → 15 verified findings)
- **처리 일시**: 2026-09-29T16:15Z — 15/15 처리(전부 수정, #2의 재빌드 중복은 U2로 이관)
- **검증 후 상태**: pytest **306** (292 → +14 회귀 테스트), vitest **30** (28 → +2), ruff/black/tsc/vite clean, mypy **14** (15 → 14)

| # | 파일 | 요지 | 처리 | 근거·테스트 |
|---|---|---|---|---|
| 1 | `locus/play/storage/postgres_repo.py` | 옛 `SourceKind` 값(`session-rumor`/`session-event`)이 든 PG 행을 못 읽어 기존 세션의 GM 라우트가 500. code-summary의 "init-schema가 테이블을 다시 만든다"는 거짓(CREATE IF NOT EXISTS) | **수정** — `SourceKind._missing_`이 `inferred-wiki→INFERRED`, `session-rumor/event→SIMULATION`으로 매핑. code-summary 문구 정정 | `tests/shared/models/test_models.py::test_legacy_source_kind_values_map_to_current_members` |
| 2 | `locus/shared/storage/graph_mapping.py` | Neo4j `prov_source='inferred-wiki'` 노드가 로더 전체를 깨뜨림; 재빌드는 `delete_world`를 안 불러 두 벌이 됨 | **읽기 수정**(#1과 같은 매핑). 재빌드 중복(RE A3)은 **U2 W6 `WorldBuilder.build(replace=)`** 범위(FR-B4, 이미 계획됨) | `test_legacy_neo4j_prov_source_loads`; U2 FD 가정 A3 |
| 3 | `web/src/routes/GmPage.tsx:26` | 세션 전환 뒤 늦게 도착한 응답이 이전 세션으로 화면을 되돌림 | **수정** — `sessionIdRef`로 현재 라우트와 다른 응답은 버림(loadSession·export 모두) | 코드 리뷰 재현 경로 차단; 수동 확인 |
| 4 | `locus/shared/wiring.py:77` | `assemble_shared`가 all-or-nothing이라 자원 하나만 죽어도 모든 경계가 503, 드라이버 누수, `/health`는 200 | **수정** — `strict=False`(API)는 자원별로 degrade, `strict=True`(CLI)는 연 것을 닫고 raise. `/health`가 `ok/degraded` + 경계 상태, 전부 죽으면 503 | `tests/shared/test_wiring.py`, `tests/api/test_knowledge_api.py::test_health_*` |
| 5 | `api/routers/gm.py:81` | GM 쓰기 라우트가 번역 워밍을 예약해 X1 결정(쓰기는 ko=null, 지연)과 어긋나고 같은 문장을 최대 3회 번역 | **수정** — 쓰기 핸들러 7개는 `enrich=False`; `TranslationService.enrich`에 in-flight 집합으로 중복 예약 억제 | `tests/api/test_localization_api.py::test_gm_writes_never_call_the_translator`, `tests/localization/test_translation_service.py::test_enrich_does_not_reschedule_*` |
| 6 | `tests/test_boundaries.py:55` | `from locus import play` 꼴을 못 잡음 | **수정** — `from locus import x`를 `locus.x`로 기록; 최상위 모듈 = 조립 루트만 허용하는 테스트 추가 | `test_only_composition_roots_live_at_the_top_level` |
| 7 | `web/src/routes/GmPage.tsx:38` | 같은 월드의 세션 전환에도 export 재요청 + 선택 지역 소실 | **수정** — 월드가 같으면 `data`·`selected` 유지, 월드가 바뀔 때만 재요청 | #3과 같은 파일 |
| 8 | `web/src/routes/EditorPage.tsx:26` | URL의 월드를 자동 로드하지 않아 딥링크·뒤로가기가 빈 화면 | **수정** — `[paramWorldId]` 효과로 export 자동 로드(실패는 조용히) | `components.test.tsx` "redirects / … and loads that world" |
| 9 | `locus/shared/storage/sql.py:36` | ON CONFLICT 갱신 집합에 PK가 들어가 재upsert마다 `id`가 바뀜 | **수정** — PK 컬럼 제외; 인메모리 트윈도 같은 의미로 | `tests/localization/test_translation_repo.py::test_reupsert_keeps_primary_key` |
| 10 | `web/src/routes/GmPage.tsx:65` | GM의 "— none —"이 죽은 항목, 에디터의 Close·상태가 죽음 | **수정** — `SessionBar` `variant="picker"`(에디터), `allowNone={false}`(GM) | 위 라우팅 테스트가 Close 부재·none 부재를 단언 |
| 11 | `web/src/routes/GmPage.tsx:71` | 세션 로드 실패 시 복구 수단 없음 | **수정** — 오류 + "다시 시도" 버튼 + 안내 | "keeps the GM screen recoverable" 테스트 |
| 12 | `web/src/routes/EditorPage.tsx:43` | 빈 world id로 Load 시 `/editor/`로 이동해 상태 유실 | **수정** — 빈 id 거부 + 오류 문구 | "refuses to load an empty world id" 테스트 |
| 13 | `api/main.py:103` | lifespan이 주입된 컨테이너까지 닫음; 닫힌 executor에 `enrich`가 예외 | **수정** — `Containers.owned`로 조립한 것만 닫음; `enrich`의 예약은 try/except(원문 표시) | `test_enrich_survives_a_dead_scheduler` |
| 14 | `locus/play/storage/postgres_repo.py:59` | 어댑터가 주입된 공용 엔진을 dispose | **수정** — `_owns_engine`일 때만 dispose(두 어댑터) | `tests/shared/test_wiring.py::test_injected_engine_survives_disconnect` |
| 15 | `tests/play/helpers.py:34` | 테스트가 조립 루트를 손으로 복제해 `assemble_play`에 테스트 호출자가 0 | **수정** — `assemble_play(generator=, suggester=, tuning=)` 오버라이드; `compose_play`가 그것을 감싸고 `PlayServices` 삭제 | 기존 play/api 테스트 전부가 조립 루트를 지남 |

**리뷰가 남긴 메모(대상 밖)**: `operations.md`·`web/README.md`·`examples/demo_world/README.md`의 옛 라우트, `CLAUDE.md:13`의 `locus/translation/` → 함께 고침(README 전면 갱신은 U8).
