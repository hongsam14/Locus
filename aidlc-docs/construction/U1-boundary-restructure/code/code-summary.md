# U1 경계 재정리 — Code Summary

## 베이스라인 (Step 1.1, 2026-09-29T14:04Z, commit `ee61277` + 미커밋 aidlc-docs)
- `pytest -q --no-cov`: **281 passed**, 3 warnings (FastAPI `on_event`·Starlette TestClient deprecation)
- `mypy locus api`: **16 errors in 10 files** (96 source files) — 10.6 기준선
- `npm test` (vitest): **24 passed** (2 files)
- Python: `.venv` → `/usr/bin/python3` = 3.14.4 (동작함)

## 이동표 (옛 → 새)
다섯 경계(`locus/{shared,knowledge,world,play,localization}`)로 접었다(AD-R1=A). 파일 단위 목록은 `git diff HEAD -M --name-status`로 확인할 수 있다(유사도 50~100%로 모두 rename 추적됨).

| 옛 경로 | 새 경로 | 비고 |
|---|---|---|
| `locus/models/*` | `locus/shared/models/*` | + `util.py`(clamp01·normalize_name) |
| `locus/config/*` | `locus/shared/config/*` | + `tuning.py`(`KnowledgeTuning`·`PlayTuning`) |
| `locus/llm/*` | `locus/shared/llm/*` | 그대로 |
| `locus/storage/{base,neo4j_repo,opensearch_repo,graph_mapping,persistence,schema}.py` | `locus/shared/storage/*` | + `sql.py`(engine·`upsert_stmt`); `schema.py`에 `ensure_world_schema` |
| `locus/consensus/{engine,propagation}.py`, `locus/query/{loader,engine}.py` | `locus/knowledge/{consensus,propagation,loader,query}.py` | + `wiring.py` |
| `locus/ingestion/*` | `locus/world/ingestion/*` | |
| `locus/topology/*`, `locus/ontology/*` | `locus/world/{topology,ontology}/*` | |
| `locus/commonsense_wiki/*` | `locus/world/wiki/*` | |
| `locus/augmentation/*` | `locus/world/augmentation/*` | `session_store.py` → `run_store.py` |
| `locus/services/{orchestrator,editor,exporter}.py` | `locus/world/{build,editor,worldfile/export}.py` | + `wiring.py` |
| `locus/demo.py` | `locus/world/demo/__init__.py` | 지도 경로 `examples/demo_world/map.png` |
| `locus/session/{models,base,service,distortion_service,query}.py` | `locus/play/{models,base,session_service,distortion_service,region_knowledge}.py` | |
| `locus/session/{rumor_service,rumor_generator,rumor_dynamics,promotion,rumor_feedback_service}.py` | `locus/play/rumor/{service,generator,dynamics,promotion,feedback}.py` | |
| `locus/session/{event_service,event_suggester,dynamics}.py` | `locus/play/event/{service,suggester,dynamics}.py` | |
| `locus/session/{turn,turn_changes}.py` | `locus/play/turn/{advancer,changes}.py` | |
| `locus/session/{repository,memory_repo}.py`, `locus/storage/postgres_session_repo.py` | `locus/play/{ports,storage/memory_repo,storage/postgres_repo}.py` | + `storage/schema.py`, `wiring.py`; `gm/`·`npc/`·`player/` 빈 패키지(U4~U6 자리) |
| `locus/translation/{service,translator}.py` | `locus/localization/{service,translator}.py` | + `models.py`·`ports.py`·`storage/*`·`wiring.py` |
| `api/routers/{query,authoring,session}.py` | `api/routers/{knowledge,world,play,gm}.py` | + `api/{deps,errors,schemas}.py` |
| `tests/<옛 패키지>/*` | `tests/<경계>/*` | + `tests/test_boundaries.py`, `tests/api/*`, `tests/play/helpers.py` |
| `web/src/api.ts` | `web/src/api/{index,http,world,knowledge,play,gm}.ts` | + `web/src/routes/{AppNav,EditorPage,GmPage,PlayPage}.tsx` |

## 이름 매핑
| 옛 | 새 | 근거 |
|---|---|---|
| `ScopeType.RUMOR` / `is_rumor` / `include_rumors` / `ConsensusView.rumors` | `ScopeType.HEARSAY` / `is_hearsay` / `include_hearsay` / `ConsensusView.hearsay` | AD-R7 (캐노니컬 거리 감쇠 = 전언) |
| `KnowledgeView.distortion_degree` | `path_decay`(전언) + `distortion`(세션 소문 뷰, 신설) | AD-R7 |
| `canonical_known` | `region_known` | 용어 |
| `SourceKind.USER_INPUT/LLM_INFERRED/USER_AUGMENT/SESSION_RUMOR` | `input/inferred/augmentation/simulation` + `dialogue`(U5) | 저장 데이터 비호환(Q4=A) |
| `AugmentationSession` / `SessionStore` | `AugmentationRun` / `RunStore` | "세션"은 플레이 전용(FR-A5) |
| `PipelineOrchestrator` / `GraphEditor` / `Exporter` | `WorldBuilder` / `WorldEditor` / `WorldFileExporter` | 경계 이름 |
| `SessionQueryEngine` | `SessionKnowledgeService` | |
| `PostgresSessionRepository` / `InMemorySessionRepository` / `SessionRepository` | `PostgresPlayRepository` / `InMemoryPlayRepository` / `PlayRepository`(+ 분할 Protocol `SessionStore`·`RumorStore`·`DistortionStore`·`TimelineStore`·`EventStore`·`PlayUnitOfWork`) | AD-R3 |
| `RumorDynamicsParams` / `ConsensusParams(rumor_min)` | `PlayTuning` / `ConsensusParams(hearsay_min)` + `KnowledgeTuning` | US-8.5 |
| `TurnService.advance_turn` | `TurnAdvancer.advance` | AD-R5(행동 입력은 U4) |
| `GameMasterService` | 삭제 — 라우터가 `PlayContainer`의 서비스를 직접 받음 | AD-R4 |
| `/api/query/regions/{r}/knowledge?world_id=` | `/api/knowledge/worlds/{w}/regions/{r}?include_hearsay=` | AD-R6 |
| `/api/authoring/...` | `/api/world/...` (`augment/session` → `augmentation/runs`) | AD-R6 |
| `/api/session/...` | 세션 수명·NPC 뷰 → `/api/play/...`, GM 조작 → `/api/gm/...`(`advance-turn` → `advance`, `suggest-events` → `events/suggest`) | AD-R6 |
| `web` `AugSession` / `App` 단일 화면 | `AugRun` / `react-router` 3화면(`/editor/:worldId`, `/gm/:sessionId`, `/play/:sessionId?`) | AD-R8 |

## 삭제 목록
- `GameMasterService`(`locus/session/game_master.py`), `SessionRepository` 단일 Protocol, `PlayRepository`의 traverse 계열(`traverse`·`get_region_subtree`·`get_region_ancestors`·`TraversalSpec`·`Path`), Neo4j `Relation` 라벨 상수.
- 도메인 모델의 표시 전용 `*_ko` 필드(`SessionRumor.statement_ko`, `SessionEvent.description_ko`) — API DTO(`api/schemas.py`)로 이동.
- Step 13 죽은 코드: `World` DTO, `WikiBuildReport`, `Entity/Knowledge/WikiPrior.embedding_ref`, `Settings.debug`(+`LOCUS_DEBUG`), `play.event.dynamics.merge_add`(전용 단위 테스트와 함께), `SUPPORT_DECAY` 상수와 `evolve_support(decay=…)` 경로(감쇠는 `play.rumor.dynamics`가 단독 소유; 테스트는 강화-전용으로 갱신), `RunStore.delete`(테스트의 delete 구간 제거), `to_terrain_entity`.
- 유지(확인 결과): `RegionLevel.DISTRICT`(수집 테스트가 유효 레벨로 사용), `Settings.rumor_support_decay`(`PlayTuning.support_decay`로 이어짐).
- 헬퍼 통일: `clamp`/`_clamp`/`_clamp01` 8곳 → `shared/models/util.clamp01`; `_norm` 5곳 + `mapping.normalize_name` → `shared/models/util.normalize_name`(`mapping`이 재노출하므로 기존 import 경로 유지). 계획은 `mapping.normalize_name`을 단일 정본으로 적었으나, topology/ontology가 ingestion 패키지를 import하지 않도록 `shared`에 두었다(결과 동일, 기존 테스트로 확인).

## 새 파일
- `locus/shared/{__init__,wiring}.py`, `shared/config/tuning.py`, `shared/models/util.py`, `shared/storage/sql.py`
- `locus/knowledge/{__init__,wiring}.py`
- `locus/world/{__init__,wiring}.py`, `world/worldfile/__init__.py`, `world/augmentation/{run_store,service}.py`(개명 재작성), `world/build.py`
- `locus/play/{__init__,ports,wiring}.py`, `play/storage/{__init__,schema}.py`, `play/{rumor,event,turn,gm,npc,player}/__init__.py`, `play/region_knowledge.py`
- `locus/localization/{__init__,models,ports,wiring}.py`, `localization/storage/{__init__,schema,memory_repo,postgres_repo}.py`
- `api/{deps,errors,schemas}.py`, `api/routers/{world,knowledge,play,gm}.py`
- `tests/test_boundaries.py`, `tests/api/{__init__,play_fixtures,test_augment_api,test_localization_api,test_play_gm_api}.py`, `tests/play/{helpers,test_upsert_idempotent}.py`, `tests/world/test_demo.py`, `tests/localization/*`
- `web/src/api/{http,world,knowledge,play,gm}.ts`, `web/src/routes/{AppNav,EditorPage,GmPage,PlayPage}.tsx`
- `.dockerignore`

## 테스트 결과 (Step 15, 2026-09-29)
| 검사 | 베이스라인 | 결과 |
|---|---|---|
| `pytest -q --no-cov` | 281 passed | **292 passed** (−1 traverse, −1 merge_add, +503/enrich/ko-필드/경계 3/데모 2/upsert 3/… 신규) → 코드 리뷰 수정 뒤 **306** |
| `npm test` (vitest) | 24 passed | **28 passed** (+배지 1, +라우팅 3) → 코드 리뷰 수정 뒤 **30** |
| `ruff check locus api tests` / `black --check` | clean | clean |
| `mypy locus api` | 16 errors / 10 files | **15 errors / 9 files** → 코드 리뷰 수정 뒤 **14** |
| `npm run lint` (tsc) / `npm run build` | clean | clean / built |
| `tests/test_boundaries.py` | — | 3 passed (의존 행렬·상대 import 금지·최상위 패키지 = 5 경계) |
| `docker build .` | — | OK — `api/` 포함, `import api.main` OK |
| `docker compose --profile service up` + `/health` | — | **operator-run**(포트 7474/7687 충돌); 대체: 단독 이미지 `/health` 200, 경계 503 확인 |

### 15.1 배포 검증 기록 (2026-09-29T14:50Z)
- `docker build -t locus-u1-check .` → OK. 이미지 안에 `/app/api/{deps,errors,schemas,main}.py` + `routers/{gm,knowledge,play,world}.py` 존재, `python -c "import api.main"` OK.
- **`docker compose --profile service up -d` + `/health`는 이 환경에서 실행하지 않음(operator-run)**: 호스트 포트 7474/7687을 다른 프로젝트의 컨테이너 `sigraph-neo4j-1`이 이미 쓰고 있어 이 스택의 `neo4j` 서비스가 뜨지 못한다. 다른 프로젝트의 컨테이너를 내리거나 포트를 바꾸는 것은 운영자 결정이다. 실행 방법: `docker compose --profile service up -d --build && curl -sf localhost:8000/health`.
- 대체 검증(비침습): 빌드한 이미지를 단독으로 `uvicorn api.main:app`으로 띄우고(의존 서비스는 닫힌 포트로 지정) `127.0.0.1:18000/health` → **200 `{"status":"ok"}`**; `/api/knowledge/worlds/demo/regions/r1` → **503 `knowledge boundary unavailable`**(경계별 503 degrade가 이미지에서 동작). Neo4j 연결 실패 로그가 startup에 찍히고 앱은 계속 뜬다(첫 응답까지 약 30~60초: neo4j 드라이버의 연결 재시도 → U8 운영 TODO: startup에서 드라이버 연결 타임아웃 단축).
- 라이브 Neo4j 재빌드(`locus build-world --world demo --demo`)는 operator-run(이 환경의 7687은 다른 프로젝트 DB).

## 남긴 TODO (U2~)
- **저장 데이터**: 코드 리뷰(#1·#2)에서 옛 `SourceKind` 값(`inferred-wiki`·`session-rumor`·`session-event`)이 저장된 Neo4j 노드·PostgreSQL 세션 행을 읽지 못하는 것이 확인되어 `SourceKind._missing_`로 읽기 시 매핑한다. 따라서 기존 월드·세션은 재빌드 없이 읽힌다. 재빌드 시 월드가 두 벌이 되는 A3(`delete_world` 미호출)는 U2 `WorldBuilder.build(replace=)`에서 고친다. `init-schema`는 테이블을 다시 만들지 않는다(CREATE IF NOT EXISTS + 추가 컬럼).
- `web/package.json`: `@vitejs/plugin-react` ^4.3 → ^5.2(vite 8 peer 충돌로 `npm install`이 실패하던 것을 고침; 계획 밖 최소 수정).
- U2: `WorldCache`, NPC 모델, World File import, 수집 결함. U4: `PlayUnitOfWork` 구현, `advance(action)`, 가드·예산. U5: 대화·번역 확장·UI 라벨. U6: 행적. U7: GM 화면 분할. U8: 데모 콘텐츠·README·CI·compose 프로파일 정리.
- `locus/play/{gm,npc,player}/`는 빈 패키지(자리표시)다.
- mypy 잔여 15건은 모두 베이스라인에서 이월된 것(외부 라이브러리 타입·Optional 드라이버)이다.

## 코드 리뷰 (승인 뒤, U2 전)
`reviews/code-review-01.md` — `/code-review` 15건, 전부 수정(#2의 재빌드 중복은 U2 `build(replace=)`로 이관). 회귀 테스트 +16(pytest 14, vitest 2).
