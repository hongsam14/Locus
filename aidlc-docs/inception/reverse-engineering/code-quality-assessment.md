# Code Quality Assessment

> Reverse Engineering — Purpose Restructure Cycle (2026-09-29). 기준 커밋 `ee61277`.
> **[재현]** 표시는 인메모리 시뮬레이션이나 실제 실행으로 확인한 것이다. 나머지는 코드를 읽고 확인했다.

## Test Coverage

- **Overall**: Good. 백엔드 라인 커버리지 87%(`locus`+`api`). 오프라인 305 테스트가 GREEN이다(pytest 281, 약 10초 + vitest 24).
- **Unit Tests**:
  - 양호하다. 세션 순수 모듈과 서비스는 대부분 95~100%, consensus·models·translation도 높다.
  - 약한 곳:
    - CLI `__main__.py` 0%
    - `augmentation/graph.py` 0% (죽은 코드)
    - augmentation `detectors`·`engine` 48%, `apply` 68%
    - `llm/openai_provider.py` 35%
    - `opensearch_repo` 41%, `neo4j_repo` 56%, `schema` 56%
- **Integration Tests**:
  - 라이브 통합 테스트가 **없다.** API 테스트는 TestClient와 mock으로만 돈다.
  - PostgreSQL 어댑터는 SQLite로 검증한다.
  - 계약 테스트는 인메모리 어댑터만 대상으로 한다.
  - 라이브 시나리오는 운영자가 직접 돌리는 문서뿐이다.
- **테스트 목적 분포**: SIMULATION 약 47%, L10N 약 8%, DESIGNER 약 9%, KNOWLEDGE 약 8%, INFRA 약 8%, TOPOLOGY·WIKI 약 6%씩, 수집 약 5%, NPC 서빙 약 4%. **테스트가 가장 촘촘한 곳이 핵심 산출물이 아니다.**
- **프론트**: 24 테스트 중 62%가 세션이다. App, Toolbar, 지도 드래그 저장, 보강 답변·되돌리기, `api.ts` URL, 타입-백엔드 일치는 테스트가 없다.

## Code Quality Indicators

- **Linting**:
  - ruff·black은 설정되어 있고 clean하다.
  - mypy는 설정만 있고 오류 16개(10 파일)가 있다.
  - 프론트는 `tsc --noEmit`만 있고 ESLint가 없다. 그런데 `SessionBar.tsx:18`에 eslint-disable 주석이 있다.
  - **CI 없음.** "GREEN" 상태는 수동 실행에만 기댄다.
- **Code Style**: 대체로 일관된다(DI 생성자 주입, 포트, 순수 함수). 하지만 이름이 겹치는 곳이 여럿이다(아래 D절).
- **Documentation**: Poor.
  - 최상위 README가 크게 낡았다(구체적 항목 10개). 예: "U1 Foundation 구현 중", 없는 `tools` 프로파일, 필수 비밀번호 누락, 9개 패키지 누락.
  - `web/README.md`는 U10 시점에 머물러 있다.
  - `session/__init__.py`, `game_master.py`, `api/routers/session.py`의 docstring이 낡았다.
  - `CLAUDE.md`와 aidlc-docs는 최신이다.

## Technical Debt

### A. 핵심 산출물을 조용히 손상시키는 결함 (캐노니컬)

| # | 결함 | 위치 | 영향 |
|---|---|---|---|
| A1 | **지역 병합 시 연결 힌트 유실** [재현] | `ingestion/mapping.py:191-200`, `structured_map_ingestor.py:131-132` | 메모와 지도가 같은 지역을 내면, 지도의 연결이 경고 없이 사라진다(데모: 연결 2개 → 0개) |
| A2 | **입력 사이 엔티티 id 끊김** [재현] | `mapping.py:175-188`, `ingestion/service.py:29-32` | 관계·ABOUT 엣지가 조용히 만들어지지 않는다 |
| A3 | **재빌드 시 월드 중복** | `graph.py:29-31`, `orchestrator.py:69-74` | 같은 world_id로 다시 빌드하면 모든 노드가 두 벌이 된다 (`delete_world`를 호출하지 않음) |
| A4 | 지역을 해석하지 못한 지식이 사라짐 | `ontology/builder.py:102` | 스코프 없이 저장되어 어떤 합의 뷰에도 나오지 않고, 보강 탐지에도 잡히지 않는다 |
| A5 | 관계를 다시 읽지 않음 | `query/loader.py:19-21` | export에서 관계가 빠지고, DANGLING 탐지가 불가능하며, ORPHAN은 오탐한다 |
| A6 | 교차 월드 prior 검색이 실환경에서 매칭되지 않음 | `commonsense_wiki/cross_world.py:55` vs `graph_mapping.py:328-335` | `domains` 필터 경로가 `meta.domains`와 다르다. 테스트 fake가 이를 놓친다 |
| A7 | **이미지를 JSON으로 보낼 수 없음** [재현] | `ingestion/service.py:16-24` | `list[bytes]`가 base64를 디코드하지 않아 API·CLI `--inputs`로 VLM 경로를 쓸 수 없다 |
| A8 | `KnowledgeView.title`이 채워지지 않음 | `consensus/engine.py:51-60` | NPC 응답에 제목이 없고, 번역할 `title_ko`도 없다 |
| A9 | LLM 폴백 prior는 저장되지 않는데 id가 참조됨 | `commonsense_wiki/base.py:96-114` | `wiki_prior_ref`와 `derived_from_prior_ids`가 끊긴 참조가 된다 |
| A10 | 합의 전파의 특이점 | `consensus/engine.py:107-132` | 같은 지식이 여러 지역에 있으면 가장 강한 경로가 아니라 먼저 발견된 원점이 이긴다. `unknown_count`가 부정확하고 노출되지도 않는다. 신뢰도 기준이 경로마다 다르다 |
| A11 | 이름이 같고 레벨이 다른 지역이 비결정적으로 해석됨 | `topology/builder.py:37`, `hierarchy.py:22`, `ontology/builder.py:34` | parent, 힌트, 스코프가 엉뚱한 지역에 붙을 수 있다 |
| A12 | 동시 빌드 경합 | `orchestrator.py:75-80` | 공유 빌더 상태를 `set_wiki`로 바꾼다 |
| A13 | 빌드 리포트가 문제를 숨김 | `topology/builder.py:85-86`, `reports.py:29-32` | 수집 오류, 계층 경고, 스코프 없는 지식이 리포트에 없고 `ok`는 항상 True다 |

### B. 기획자 도구 결함

| # | 결함 | 위치 |
|---|---|---|
| B1 | **보강 UI가 target을 보내지 않음.** confirm·edit·remove는 아무 일도 안 하고, add는 빈 Knowledge를 만든다 | `web/src/AugmentPanel.tsx`, `augmentation/apply.py:15-72`, `types.py:46-84` (질문에 target 정보가 없음) |
| B2 | **"Revert last"가 항상 404** (답할 때마다 새 세션으로 바꿈) | `AugmentPanel.tsx:33`, `augmentation/service.py:54-61` |
| B3 | Entity를 confirm·edit하면 `KeyError` → 500 [재현] | `augmentation/apply.py:57-69` |
| B4 | LLM이 선택지를 다시 쓰면 enum 검증 실패 → 422 | `augmentation/questions.py:55-57` |
| B5 | wiki 충돌 탐지가 `attributes["terrain"]`을 읽는데, 수집은 `terrain_kind`에 쓴다 | `detectors.py:90`, `mapping.py:102` |
| B6 | revert가 엣지를 복원하지 않고, 재색인하지 않으며, 두 번 적용될 수 있다 | `apply.py:73-79` |
| B7 | **지도에서 클릭만 해도 지역 위치가 백엔드에 저장됨** | `web/src/MapOverlay.tsx:64,100` |
| B8 | 지역 패널 ✕가 확인 없이 `DETACH DELETE`하고 OpenSearch 문서를 남긴다. 세션 루머에서는 아무 효과가 없다 | `RegionPanel.tsx`, `services/editor.py:38` |
| B9 | 토폴로지(연결·가중치) 편집 API·UI 없음 | `api/routers/authoring.py` |
| B10 | UI에서 사용자 입력으로 월드를 빌드할 수 없음 (데모만, `with_map=false`) | `web/src/App.tsx:48`, `Toolbar.tsx` |

### C. 시뮬레이터 결함 (세션)

| # | 결함 | 위치 |
|---|---|---|
| C1 | **루머·LLM 호출이 기하급수로 증가** [재현]: persistent 이벤트 하나로 턴마다 9 → 36 → 144 → 576 호출. 탄생 지지도 0.2 + 강화 0.1 = 원본 기준 0.3이고, 캐노니컬 원본은 매 턴 다시 씨앗이 된다 | `turn.py:94-99`, `rumor_service.py:176-184`, `rumor_dynamics.py:32,35` |
| C2 | **승격 루머 하나가 지역 전체의 감쇠를 끔** [재현]: 이벤트를 해결한 뒤에도 765개가 줄지 않는다. 되먹임 왜곡도는 복원되지 않아 올라가기만 한다 | `turn.py:105,113`, `rumor_dynamics.py:55` |
| C3 | `advance_turn`이 원자적이지 않고 동시 실행을 막지 않는다. LLM을 HTTP 요청 안에서 동기로 부른다 | `turn.py:78-183` |
| C4 | `start_session`이 원자적이지 않다 | `service.py:35-38` |
| C5 | SUGGESTED 이벤트를 승인 없이 resolve할 수 있다 | `event_service.py:87-109` |
| C6 | 재생성이 부모를 hard-delete해서 계보가 끊긴다. 가지치기는 soft-flag다(삭제 방식이 둘) | `rumor_service.py:66-69` |
| C7 | 이벤트 제안 LLM이 지역 UUID와 턴 번호만 본다(`context`를 넘기지 않음) | `event_service.py:130-135`, `event_suggester.py:51,66-72` |
| C8 | `suggest-events?n=`에 상한이 없고 인증도 없다 | `api/routers/session.py:223` |
| C9 | 번역 워밍에 중복 요청 억제·만료가 없고, 삭제된 항목의 행이 남는다 | `translation/service.py:91-94` |
| C10 | 세션 NPC 뷰에서 승격 루머와 비승격 루머를 구분할 수 없다 | `session/query.py:91-102` |
| C11 | 루머 원본(direct+propagated)과 NPC 뷰(direct+inherited+global)의 집합이 다른데, 이유가 문서에 없다 | `rumor_service.py:176`, `query/engine.py:47` |
| C12 | 세션을 연 뒤 추가된 지역은 `region_distortions`에 없어서 "전체 생성"에서 빠진다 | `service.py`, `SessionPanel.tsx` |

### D. 설계 부채

- **역방향 의존·개념 누수**
  - `config` → `session` (`settings.py:12-13,95-110`).
  - 캐노니컬 `SourceKind.SESSION_*`, `KnowledgeView.*_ko`.
  - `init-schema`가 PostgreSQL 테이블을 만든다.
  - `canonical_known`이 세션 전용이다.
  - 조립 루트 하나에 두 제품 축이 섞여 있다.
- **번역이 세션 도메인에 있음**: `Translation`이 `session/models.py`에, 캐시가 `SessionRepository`에 있다. 그래서 캐노니컬 `/api/query`는 번역할 수 없다.
- **비대한 포트**: `SessionRepository`가 약 27 메서드로 6가지 관심사를 한 포트에 담는다.
- **파사드 과잉**: `GameMasterService`는 넘기기만 한다(`_repo` 미사용, `**kwargs`로 타입 소실, docstring 불일치).
- **캐노니컬을 읽는 경로가 둘**: `GraphRepository.find_nodes`와 `WorldLoader`. 지역 확인이 4곳에 중복되어 있고 매번 월드 전체를 로드한다. `set_region_distortion`은 지역을 확인하지 않는다.
- **같은 이름, 다른 뜻**: rumor(캐노니컬 거리 소문 vs LLM 세션 루머), distortion_degree(1 − 경로 가중치 vs 지역 왜곡도), session(보강 vs 게임), `SessionStatus` enum 두 개.
- **조정값 분산**: 세션 조정값 일부만 환경 변수로 바꿀 수 있고, 나머지는 하드코딩이다. 캐노니컬 조정값(합의 0.5/0.15, 가중치 표, dedup 0.86 등)은 전부 하드코딩이다. `ConsensusParams`를 세 곳에서 따로 만든다.
- **orchestrator**: `CommonsenseWiki`를 안에서 직접 만들고, `hasattr`로 덕 타이핑한다(DI 선호와 어긋남).
- **쓰기만 하고 읽지 않는 저장**:
  - 엣지 6종(CONTAINS, ABOUT, DERIVED_FROM, LOCATED_IN, RELATED_TO, PRIOR_RELATED_TO).
  - OpenSearch의 Knowledge·Entity 문서(빌드와 편집마다 임베딩 비용이 든다).
  - `Provenance.refs`는 저장되지 않는다.
- **고증의 순환**: 월드 자기 입력에서 prior를 증류하고, 그 prior로 같은 월드를 "실세계 상식"이라고 보강한다. 프롬프트에 "real-world"가 남아 있다.
- **전체 로드 비용**: 질의마다 월드 전체를 로드하고, 레이블 없는 엣지 스캔을 한다. 쓰기는 노드·엣지마다 트랜잭션 하나씩이다. 캐시가 없다.
- **DB 스키마 관리**: 마이그레이션 도구가 없다(수작업 `ALTER`). 외래 키·cascade가 없고, 세션을 삭제할 수 없다. API가 기동할 때 DDL을 실행한다.
- **프론트**:
  - `SessionPanel.tsx`가 518줄짜리 god component다.
  - 타입을 손으로 써서 백엔드와 이미 어긋났다.
  - UI가 영어와 한국어로 섞여 있다.
  - 지역을 이름이 아니라 UUID로 표시한다.
  - 슬라이더는 `onMouseUp`에서만 저장해서 키보드·터치로 바꾼 값은 저장되지 않는다.
  - CORS가 없어 `VITE_API_URL`은 same-origin에서만 동작한다.

### E. 죽은 코드·미완성

- `augmentation/graph.py` (LangGraph, 호출되지 않음) → `langgraph`는 필수 의존성이다.
- `ingestion/mapping.to_terrain_entity`는 미사용이다 → `EntityType.TERRAIN`이 만들어지지 않고, distiller의 지형 목록은 늘 비어 있다.
- 미사용: `World`, `WikiBuildReport`, `embedding_ref` 필드, `RegionLevel.DISTRICT`, `Settings.debug`, `SessionStore.delete`.
- 저장되지 않는 스코프 타입: `ScopeLink.is_rumor`, `ScopeType.INHERITED/PROPAGATED/GLOBAL`.
- 존재하지 않는 레이블 "Relation"에 대한 Neo4j 제약.
- 미사용 포트 메서드: `traverse`, `get_region_subtree`, `get_region_ancestors`, `delete_world`, `health_check`.
- 세션:
  - `dynamics.merge_add`(`SessionEvent.accumulate`와 중복).
  - `dynamics.SUPPORT_DECAY` 경로(`decay=0.0`으로만 호출됨).
  - `get_translation`·단일 `upsert_translation`(테스트 전용).
  - `app.state.session_repo`(읽는 곳 없음).
- API로 노출되지 않는 파라미터: `generate_rumors(degrees=)`, `advance_turn(promotion_threshold=)`.
- 웹:
  - `EventDraft` 타입.
  - `viz.toPixels`(테스트 전용).
  - Badge `pruned` 톤, Toast `neutral`/`danger` 톤, `Field.label`.
  - i18n `gm.approve/discard/resolve` 키.
  - 읽지 않는 타입 필드 다수.
- 데모 내용이 `locus/demo.py`와 `examples/demo_world/`에 중복되어 있다.

### F. 배포·도구

- **`service` 프로파일이 기동하지 않는다**: 루트 `Dockerfile`이 `api/`를 복사하지 않는다(pyproject도 `locus*`만 패키징한다).
- 루트 `.dockerignore`가 없어서 `.venv/`와 `data/`가 빌드 컨텍스트에 들어간다.
- `requirements.txt`에 sqlalchemy·psycopg가 없다.
- `@vitejs/plugin-react`의 peer 범위(vite 4~7)가 vite 8과 충돌한다. `npm install`로 새로 설치하면 실패할 수 있다(미검증).
- `.venv`가 시스템 python(3.14)에 심볼릭 링크로 걸려 있다. 3.13·3.14 site-packages가 섞여 있어 불안정하다.
- 라이선스가 어긋난다(pyproject `Proprietary` vs `LICENSE` MIT).
- FastAPI `on_event` deprecated. `ThreadPoolExecutor`를 종료하지 않는다. `/health`가 DB를 확인하지 않는다.

## Patterns and Anti-patterns

- **Good Patterns**:
  - 포트·어댑터로 외부 I/O를 격리했다. 덕분에 오프라인 테스트 305개가 10초 안에 돈다.
  - 순수 함수 코어(consensus, weights, dynamics, rumor_dynamics, promotion)와 PBT.
  - 세션 레이어에 인메모리 어댑터와 계약 테스트가 있다.
  - 기능마다 서비스를 하나씩 두는 분리(사용자 선호)와 `SessionEvent` 애그리거트.
  - 번역을 읽기 비차단(캐시만 읽고 백그라운드에서 번역)으로 처리한다.
  - 캐노니컬과 세션 저장소가 물리적으로 분리되어 있다. 세션은 캐노니컬에 쓰지 않는다.
- **Anti-patterns**:
  - 역방향 의존 `config → session`, `translation → session` (`settings.py:12-13`, `translation/service.py:21-22`).
  - 비대한 포트 `SessionRepository` (`session/repository.py`).
  - 넘기기만 하는 파사드 `GameMasterService` (`game_master.py`).
  - 전송용 데이터를 도메인 모델에 싣는다. 연결 힌트를 `Region.attributes`에 담아 Neo4j까지 저장한다 (`structured_map_ingestor.py:131`).
  - 조용한 실패: 끊긴 엣지 MATCH, 버려지는 경고, `ok=True` 고정 (`neo4j_repo.py:86-103`, `reports.py:29-32`).
  - 헬퍼 중복: 이름 정규화 6곳, clamp 5곳 이상, cosine 2곳, `_svc` 2곳.
  - god component `SessionPanel.tsx` (518줄).
  - 테스트 fake가 필터 dict만 확인해서 실환경 결함을 놓친다 (`tests/commonsense_wiki/test_wiki_build.py:251-297`).
