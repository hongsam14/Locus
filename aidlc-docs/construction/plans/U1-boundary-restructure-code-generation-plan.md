# U1 경계 재정리 — Code Generation Plan

**원하시는 것**: 월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG로 Locus를 다시 짜는 것. 플레이어의 행적도 소문이 된다.
**지금 하는 것**: U1 — `locus/`를 다섯 경계(shared / knowledge / world / play / localization)로 옮기고, 역방향 의존을 끊고, 포트를 나누고, 조립을 컨테이너로 바꾸고, API 접두어·용어를 정리한다. **코드 동작(의미)은 바꾸지 않는다.** 단 저장 데이터의 호환은 깨진다(아래 '바뀌는 외부 계약'의 저장 데이터 항목, 요구사항 Q4=A). 이 유닛이 끝나면 뒤 유닛(U2 World File, U4 플레이어 …)이 새 자리에 기능을 얹는다. 이 문서가 U1 Code Generation의 단일 진실이다.

> FD·NFR은 SKIP(실행 계획·유닛 정의). 설계 근거: `inception/application-design/purpose-restructure/{application-design,components,component-methods,services,component-dependency}.md`, 유닛 정의 `unit-of-work.md` §U1.

---

## 유닛 컨텍스트

- **스토리**: US-7.1(배치·용어·접두어), US-7.2(의존 방향·조립·포트·스키마 분리), US-7.4(기존 테스트 GREEN) — 주. US-1.1(Docker `api/` 포함), US-8.5(Tuning dataclass 분리), US-9.3(`TranslationStore` 분리) — 부.
- **의존**: 없음(첫 유닛). 뒤 유닛이 이 유닛의 패키지 트리·컨테이너·접두어를 전제한다(조정 지점 "API 계약 동결").
- **인터페이스(결과)**: 패키지 트리(설계 §2), `assemble_shared/knowledge/world/play/localization`, `SharedContainer`·`KnowledgeContainer`·`WorldContainer`·`PlayContainer`·`LocalizationContainer`, `create_app(**containers)`, 라우터 `/api/world`·`/api/knowledge`·`/api/play`·`/api/gm`, play 포트 6개(+`PlayUnitOfWork` Protocol 정의만), `TranslationStore`.
- **DB 엔티티**: 소유 이동만 — play: `game_sessions`·`session_rumors`·`region_distortions`·`timeline_entries`·`session_events`(`locus/play/storage/schema.py`) · localization: `translations`(`locus/localization/storage/schema.py`). 열 변경 없음. 스키마는 `init-schema`로 재생성(마이그레이션 없음, Q4=A).
- **바뀌는 외부 계약(의미는 동일)**: API 접두어·일부 경로 형태, JSON 필드 이름(`is_rumor→is_hearsay`, `distortion_degree(KnowledgeView)→path_decay`, `rumors→hearsay`, `include_rumors→include_hearsay`), `SourceKind` 값(`inferred-wiki→inferred`, `session-rumor→simulation`, `session-event→simulation`), 보강 응답 `AugmentationSession→AugmentationRun`. `*_ko` 필드는 응답 DTO(`api/schemas`)에만 남고 도메인 모델에서 빠진다(와이어 형태는 같음). **저장 데이터**: Neo4j에 저장된 `prov_source`(옛 `SourceKind` 값 `inferred-wiki`·`session-rumor`·`session-event`)는 새 enum(`Provenance.source`, 엄격 검증)이 읽지 못하므로 **기존 캐노니컬 월드는 `locus build-world`로 재빌드**해야 한다(요구사항 Q4=A 호환성 깸 허용에 따라 옛 값 읽기 매핑은 두지 않음; code-summary·`operations.md`에 명시). PostgreSQL 테이블은 `init-schema`로 재생성.
- **바꾸지 않는 것**: 합의 계산, 소문·사건·턴 규칙과 값, 프롬프트, 번역 캐시 규칙, 프론트 화면 기능(재배치만).

## 실행 원칙
- 기존 파일은 `git mv`로 옮기고 그 자리에서 고친다. `_new`·`_v2` 같은 복사본을 만들지 않는다.
- 3~7단계는 import가 깨져 있을 수 있다. 각 단계 끝에 `python -m compileall -q locus api`만 확인하고, **전체 GREEN은 10단계 뒤**에 확인한다.
- 잘라내어 옮기는 코드(번역 모델·테이블·메서드·인메모리)는 **옮긴 뒤에만 원본에서 지운다**: 5단계는 지우지 않고 7단계가 옮긴다.
- 죽은 코드는 "테스트가 없고 호출자가 없는 것"만 지운다(13단계). 설계가 제거를 명시한 것(S4의 미사용 traverse 계열)은 예외로, 그 테스트와 함께 지우고 이름을 나열한다(2.5). 애매하면 남기고 STATUS 주석을 단다.
- 각 단계 완료 즉시 아래 체크박스를 [x]로 바꾼다.

---

## Steps

### Step 1 — 베이스라인과 뼈대
- [x] 1.1 `pytest -q` / `cd web && npm test` 실행, 결과(281 / 24)를 code-summary 초안에 기록. `mypy locus api` 오류 수도 실측해 **기준선**으로 기록한다(10.6이 이 수를 쓴다; 계획의 "16"은 추정이었음). → 281 / 24 / mypy 16 (실측 일치)
- [x] 1.2 패키지 뼈대 생성: `locus/{shared,knowledge,world,play,localization}/__init__.py`, `locus/shared/{models,config,llm,storage}/`, `locus/world/{ingestion,topology,ontology,wiki,augmentation,worldfile,demo}/`, `locus/play/{storage,player,turn,rumor,event,npc,gm}/`(player·npc·gm은 빈 `__init__`만; 뒤 유닛용), `locus/localization/storage/`, `api/routers/`(기존), `tests/{shared,knowledge,world,play,localization,api}/__init__.py`.
- [x] 1.3 `pyproject.toml` `[tool.setuptools.packages.find] include = ["locus*"]` 확인(하위 패키지 포함되는지), `pytest` `--cov=locus` 유지. (사전 작업: `locus/` 내부 상대 import 276개를 절대 import로 변환 — 이동 전 281 GREEN 확인)

### Step 2 — shared 경계 (S1·S2·S3·S4·S5)
- [x] 2.1 `git mv locus/models locus/shared/models`, `locus/config → locus/shared/config`, `locus/llm → locus/shared/llm`, `locus/storage/{base,neo4j_repo,opensearch_repo,graph_mapping,persistence,schema,__init__}.py → locus/shared/storage/`. (`postgres_session_repo.py`는 5단계에서 play로.)
- [x] 2.2 `shared/models` 이름 정리(S1): `ScopeType`에 `HEARSAY = "hearsay"` 추가 · `ConsensusView.rumors → hearsay` · `KnowledgeView`: `is_rumor → is_hearsay`, `distortion_degree → path_decay`(캐노니컬 전언 감쇠), 세션 소문 뷰용 `distortion: float | None` 추가, `statement_ko`·`title_ko` **제거** · `SourceKind` = `INPUT="input" | INFERRED="inferred" | AUGMENTATION="augmentation" | SIMULATION="simulation" | DIALOGUE="dialogue"`(저장된 월드 재빌드 필요 — 위 '바뀌는 외부 계약' 저장 데이터 항목; `graph_mapping._provenance`는 그대로 두고 매핑을 넣지 않는다) · `__init__` 재노출 갱신. `World`·`WikiBuildReport`는 13단계에서 판단.
- [x] 2.3 `shared/config/tuning.py`(S2): `@dataclass(frozen=True) PlayTuning`(옛 `RumorDynamicsParams` 필드 6개 그대로: support_decay, prune_floor, min_source_support, feedback_weight, high_support_threshold, birth_support), `KnowledgeTuning(propagate_min=0.5, hearsay_min=0.15)`. `settings.py`: `rumor_dynamics_params()` → `play_tuning() -> PlayTuning`, `knowledge_tuning()` 추가; **`..session` import 제거**(역방향 의존 해소 ①). 환경 변수 이름은 유지(`RUMOR_*`).
- [x] 2.4 `shared/storage/sql.py`(S5): `make_engine(url, *, echo=False) -> Engine` — 옛 `PostgresSessionRepository`의 엔진 생성 코드를 옮김.
- [x] 2.5 `shared/storage/base.py`: `GraphRepository`에서 `traverse`·`get_region_subtree`·`get_region_ancestors`와 `TraversalSpec`·`Path` DTO 제거(서비스 호출자 없음; 설계 S4 "미사용 메서드 제거"가 근거). 함께 지우는 테스트: `tests/storage/test_storage.py::test_traverse_respects_min_weight_param`(1개) — 13.1 규칙의 설계 명시 예외. 10.6 기대치는 이 1개만큼 줄어든다. `neo4j_repo.py`의 존재하지 않는 `Relation` 레이블 제약 제거. docstring의 "Rumor 레이블/DISTORTED_FROM" 낡은 문구 제거.
- [x] 2.6 `shared/wiring.py`(A1의 공유 부분 — **`api/`가 아니라 `locus/shared`에 둔다**: 3.3·4.7·6.4·7.4의 `assemble_*`가 이 타입을 import하므로 `api/`에 두면 경계 행렬(모든 경계 → api ✗)을 어긴다): `@dataclass SharedContainer(settings, graph, search, llm, vlm, embedding, sql_engine)`(연결하지 않은 자원은 `None`) + `assemble_shared(settings, *, graph=True, search=True, llm=True, sql=True) -> SharedContainer` — **켠 자원만** 연결·생성하고 **스키마 초기화는 하지 않는다**(각 경계의 `ensure_*_schema`가 맡음; 옛 Neo4j·OpenSearch 스키마 초기화는 `shared/storage/schema.py::ensure_world_schema(graph, search)`로 이름만 정리) + `SharedContainer.close()`(연결·엔진 정리). 이로써 `init-schema --play`는 SQL만, `--world`는 Neo4j·OpenSearch만 연결한다(9.1).
- [x] 2.7 `compileall` 확인.

### Step 3 — knowledge 경계 (K1·K2·K3·K5·K6)
- [x] 3.1 `git mv locus/consensus/engine.py locus/knowledge/consensus.py`, `locus/consensus/propagation.py → locus/knowledge/propagation.py`, `locus/query/loader.py → locus/knowledge/loader.py`, `locus/query/engine.py → locus/knowledge/query.py`. 옛 `locus/consensus`, `locus/query` 패키지 삭제.
- [x] 3.2 이름 정리: `ConsensusView.rumors` 생성부 → `hearsay`; `KnowledgeView(is_hearsay=…, path_decay=…)`; `QueryEngine.knowledge_for_region(..., include_hearsay=True)`; `canonical_known → region_known`; `ConsensusParams`는 `KnowledgeTuning`에서 만들 수 있게 `ConsensusParams.from_tuning()` 추가(기본값 동일).
- [x] 3.3 `knowledge/wiring.py`: `@dataclass KnowledgeContainer(loader, query, params)` + `assemble_knowledge(shared: SharedContainer) -> KnowledgeContainer`. (`WorldCache`는 U2.)
- [x] 3.4 `knowledge/__init__.py` 재노출. `compileall`.

### Step 4 — world 경계 (W1~W7·W9·W10·W11·W12)
- [x] 4.1 `git mv locus/ingestion → locus/world/ingestion`, `locus/topology → locus/world/topology`, `locus/ontology → locus/world/ontology`, `locus/commonsense_wiki → locus/world/wiki`, `locus/augmentation → locus/world/augmentation`.
- [x] 4.2 보강 용어 분리(W5): `AugmentationSession → AugmentationRun`, `SessionStatus(보강) → RunStatus`, `session_store.py → run_store.py`(`SessionStore → RunStore`, `InMemorySessionStore → InMemoryRunStore`), `AugmentationService.start_session/submit_answer/revert/get_session → start_run/answer/revert/get_run`. 동작 동일.
- [x] 4.3 `git mv locus/services/orchestrator.py locus/world/build.py` → `PipelineOrchestrator → WorldBuilder`(+ `from_factory` 유지). `CommonsenseWiki`를 **생성자 인자(wiki_factory: Callable[[str], CommonsenseWiki])**로 받고 `hasattr` 덕 타이핑 제거; 빌드마다 `TopologyBuilder`/`OntologyBuilder`를 새로 만들어 공유 상태 경합(RE A12) 제거. `replace` 인자는 U2.
- [x] 4.4 `git mv locus/services/editor.py locus/world/editor.py`(`GraphEditor → WorldEditor`), `locus/services/exporter.py → locus/world/worldfile/export.py`(`Exporter → WorldFileExporter`, 출력 dict 동일). `locus/services` 패키지 삭제.
- [x] 4.5 `git mv locus/demo.py locus/world/demo/__init__.py`(`load_demo_world` 유지). `_MAP_IMAGE`의 `Path(__file__).resolve().parents[1]`은 이동 뒤 `locus/world`를 가리켜 지도가 조용히 빠지므로 **`parents[3]`**(저장소 루트)로 고친다; 신규 `tests/world/test_demo.py::test_demo_map_image_path_exists`로 경로 실존을 검증(10.2). World File 동봉은 U2.
- [x] 4.6 진행 중 표시(W12): `ingestion/concept_art_ingestor.py`, `wiki/cross_world.py`, `augmentation/graph.py` 모듈 docstring 첫 줄에 `STATUS: in-progress — <이유 한 줄>`.
- [x] 4.7 `world/wiring.py`: `@dataclass WorldContainer(builder, editor, augmentation, wiki_admin, cross_world, exporter, demo)` + `assemble_world(shared, knowledge)`. `world/__init__.py` 재노출. `compileall`.

### Step 5 — play 모델·포트·저장 (P1·P2·P3)
- [x] 5.1 `git mv locus/session/models.py locus/play/models.py`: `Translation`은 **7.1이 잘라내어 옮길 때까지 그대로 둔다**(5단계에서 삭제하지 않음), `SessionRumor.statement_ko`·`SessionEvent.description_ko` **제거**. 나머지 동일. `SourceKind` 사용부는 새 값(`SIMULATION`)으로.
- [x] 5.2 `locus/play/ports.py`(P2): `SessionStore`(create/get/list_by_world/close/bump_turn), `RumorStore`(upsert/upsert_many/get/list_by_region(include_pruned)/delete), `DistortionStore`(set/get/list), `TimelineStore`(append/list), `EventStore`(create/get/list/update/delete) — 옛 `SessionRepository` 메서드를 그대로 나눔(이름 유지, 시그니처 동일). `PlayUnitOfWork` **Protocol 정의만**(구현은 U4). `connect/disconnect/health_check/ensure_schema`는 어댑터 클래스에 남기고 `PlayStorage` Protocol로 묶음. 옛 `repository.py` 삭제.
- [x] 5.3 `git mv locus/storage/postgres_session_repo.py locus/play/storage/postgres_repo.py` → `PostgresSessionRepository → PostgresPlayRepository`; 번역 테이블·메서드는 **7.2가 잘라내어 옮길 때까지 그대로 둔다**; 엔진은 `shared.storage.sql.make_engine`; 5개 Store Protocol을 모두 구현. `git mv locus/session/memory_repo.py locus/play/storage/memory_repo.py`(`InMemorySessionRepository → InMemoryPlayRepository`; 인메모리 번역 메서드도 7.2가 옮김). `locus/play/storage/schema.py`: 자체 **`play_metadata = MetaData()`**에 play 테이블 5개(`game_sessions`·`session_rumors`·`region_distortions`·`timeline_entries`·`session_events`) 정의를 옮기고, `ensure_play_schema(engine)` = `play_metadata.create_all(checkfirst=True)` + 옛 `ensure_schema`의 `ALTER TABLE session_rumors ADD COLUMN IF NOT EXISTS active`(비 SQLite 분기). 옛 모듈 전역 `_metadata`는 이렇게 둘로 갈라진다(`translations`는 7.2의 `localization_metadata`로; 두 테이블군 사이에 FK 없음 확인됨).
- [x] 5.4 P3 **`ON CONFLICT` upsert**(승인된 U1 책임: `unit-of-work.md` U1 P3, `components.md` P3): `_upsert_rumor_conn`과 `set_region_distortion`의 select-후-update/insert를 `shared/storage/sql.py::upsert_stmt(table, values, *, index_elements, set_)` 헬퍼(엔진 방언에 따라 `sqlalchemy.dialects.postgresql.insert` / `sqlalchemy.dialects.sqlite.insert`의 `on_conflict_do_update`)로 바꾼다. 결과 행은 동일하고 경합만 사라진다; 계약 테스트에 "같은 키로 두 번 upsert → 한 행·마지막 값" 케이스를 추가(10.5).
- [x] 5.5 `compileall`.

### Step 6 — play 서비스 (P4·P7~P11·P14·P15)
- [x] 6.1 `git mv`: `session/base.py → play/base.py`(`SessionAppService`가 `SessionStore`+`TimelineStore`를 받도록; `require_region`은 유지, `WorldLoader` 주입), `session/service.py → play/session_service.py`, `session/distortion_service.py → play/distortion_service.py`, `session/{rumor_service,rumor_generator,rumor_dynamics,promotion,rumor_feedback_service}.py → play/rumor/{service,generator,dynamics,promotion,feedback}.py`, `session/{event_service,event_suggester,dynamics}.py → play/event/{service,suggester,dynamics}.py`, `session/turn.py → play/turn/advancer.py`, `session/turn_changes.py → play/turn/changes.py`, `session/query.py → play/region_knowledge.py`.
- [x] 6.2 이름·시그니처 정리: `TurnAdvancer.advance_turn → advance(session_id, *, promotion_threshold=…)`(행동 인자는 U4) · `SessionQueryEngine → SessionKnowledgeService`: **번역 인자·`_localize` 제거**, 소문 뷰는 `KnowledgeView(scope_type=direct, is_hearsay=False, source="rumor" | "rumor:promoted", distortion=r.distortion_degree)` · `RumorDynamicsParams` → `shared.config.tuning.PlayTuning` 사용(`play/rumor/dynamics.py`의 dataclass 정의 제거, `DEFAULT_RUMOR_DYNAMICS = PlayTuning()`) · 각 서비스 생성자는 필요한 Store Protocol만 받음(기존에 `repo` 하나를 받던 자리에 같은 객체를 넘겨도 되도록 타입만 좁힘).
- [x] 6.3 `locus/session/game_master.py` **삭제**(AD-R4). `SessionClosedError`·`TurnResult`는 `play/base.py`·`play/turn/advancer.py`에서 직접 import.
- [x] 6.4 `play/wiring.py`: `@dataclass PlayContainer(repo, sessions, rumors, events, distortions, feedback, turns, region_knowledge)` + `assemble_play(shared, knowledge)`(옛 `_wire_default`의 세션 조립을 옮김; `PlayTuning`은 `settings.play_tuning()`). `play/__init__.py` 재노출(옛 `session/__init__` 목록에서 `GameMasterService`·`Translation`·`SessionRepository`·`InMemorySessionRepository` 제거, 새 이름 추가). 옛 `locus/session` 패키지 삭제. `compileall`.

### Step 7 — localization 경계 (L1~L5)
- [x] 7.1 `locus/localization/models.py`: `Translation` — 5단계에서 옮겨진 `play/models.py`에서 **잘라내어** 옮김(복사 후 원본에서 삭제). `locus/localization/ports.py`: `TranslationStore` Protocol은 **설계 L2의 이름**을 따른다 — `get_many(keys) -> dict[key, Translation]`, `upsert_many(items) -> None`(옛 `get_translation`/`get_translations_many`/`upsert_translation`/`upsert_translations` 넷을 둘로 합침; 단건은 길이 1 호출). 설계와의 차이는 `purge`가 U5라는 것뿐.
- [x] 7.2 `locus/localization/storage/postgres_repo.py`: `PostgresTranslationRepository(engine)` — 5단계에서 옮겨진 `play/storage/postgres_repo.py`에서 `translations` 테이블·메서드를 **잘라내어** 옮김(복사 후 원본에서 삭제); upsert의 SAVEPOINT+IntegrityError 경합 처리는 5.4와 같은 `upsert_stmt`(`ON CONFLICT`)로 대체(결과 동일). `schema.py`: 자체 **`localization_metadata = MetaData()`** + `ensure_localization_schema(engine)`. `memory_repo.py`: `InMemoryTranslationRepository`(옛 인메모리 번역 메서드를 잘라내어 옮김).
- [x] 7.3 `git mv locus/translation/{translator,service}.py locus/localization/`. `TranslationService(store: TranslationStore, translator, *, default_lang, warm_scheduler)`; `enrich(items, *, kind, fields: list[str], id_attr="id", world_id, session_id, lang) -> dict[str, dict[str, str]]` — **도메인 객체를 변경하지 않고 매핑을 반환**(옛 `(text_attr, ko_attr)` 쌍 → 원문 필드 이름 목록). 캐시·해시·워밍 규칙 동일. 호출부는 **`api/routers` 넷뿐**(6.2가 `SessionKnowledgeService`에서 번역을 뺐고 8.5가 라우터에서 `enrich`를 부른다; play → localization import는 10.4 위반)과 테스트(`tests/localization/test_translation_service.py`·`tests/localization/test_translation_repo.py`·`tests/api/test_localization_api.py`, 10.1 이동 뒤 경로)를 새 시그니처·Store 이름에 맞춘다(10.2). 옛 `locus/translation` 삭제.
- [x] 7.4 `localization/wiring.py`: `LocalizationContainer(translations: TranslationService | None, executor)` + `assemble_localization(shared)`(설정 `translation_enabled`가 false면 `translations=None`). `compileall`.

### Step 8 — api 조립·라우터 (A1~A7)
- [x] 8.1 `SharedContainer`·`assemble_shared`는 2.6(`locus/shared/wiring.py`)에서 이미 만들었다. **`api/containers.py`는 만들지 않는다.** 8단계는 그것을 쓰기만 한다(lifespan에서 `assemble_shared(settings)` 전체 연결 → 각 경계 `ensure_*_schema` → `assemble_knowledge/world/play/localization`).
- [x] 8.2 `api/main.py`: `create_app(*, shared=None, knowledge=None, world=None, play=None, localization=None)`; lifespan(`@asynccontextmanager`)에서 넘겨받지 않은 컨테이너를 `assemble_*`로 만들고, 실패한 경계는 `None`으로 두고 로그; 종료 시 executor·연결 정리. `app.state.containers` 하나에 담음. `_STATE_KEYS`·`on_event` 제거. `/health` 유지.
- [x] 8.3 `api/deps.py`: `get_shared/get_knowledge/get_world/get_play/get_localization` — 없으면 `HTTPException(503, "<boundary> boundary unavailable")`.
- [x] 8.4 `api/schemas.py`: `LocalizedKnowledgeView(KnowledgeView) + statement_ko/title_ko`, `QueryResultOut(items: list[LocalizedKnowledgeView], …)`, `RumorOut(SessionRumor) + statement_ko`, `EventOut(SessionEvent) + description_ko`, 요청 DTO(`SupportUpdate`, `DistortionUpdate`, `EventCreate`) 이동. 헬퍼 `localize(items, mapping, out_cls, fields)`.
- [x] 8.5 라우터 넷(기존 엔드포인트를 **새 접두어·이름**으로 옮김; DTO·의미 동일. 옛→새 경로표는 아래, code-summary에도 실음):
  - `api/routers/world.py` `/api/world`: `POST /worlds/{w}/build`, `POST /worlds/{w}/build/demo`, `GET /worlds/{w}/graph`, `GET /worlds/{w}/export`, `POST /worlds/{w}/priors`, `GET /worlds/{w}/related-priors`, `PUT /worlds/{w}/regions/{r}`, `PUT /worlds/{w}/knowledge/{k}`, `DELETE /worlds/{w}/nodes/{n}`, `POST /worlds/{w}/augmentation/runs`, `POST /augmentation/runs/{run}/answer`, `POST /augmentation/runs/{run}/revert`.
  - `api/routers/knowledge.py` `/api/knowledge`: `GET /worlds/{w}/regions/{r}?include_hearsay=`, `GET /worlds/{w}/diff?region_a&region_b`. 응답에 `enrich`(knowledge, statement·title)로 `_ko` 부여 — **캐노니컬 질의도 번역**(옛 미번역 상태에서 한 걸음; 규칙 동일).
  - `api/routers/play.py` `/api/play`: `POST/GET /worlds/{w}/sessions`, `GET /sessions/{s}`, `POST /sessions/{s}/close`, `GET /sessions/{s}/regions/{r}/knowledge`(`SessionKnowledgeService` + `enrich` rumor/knowledge → `QueryResultOut`).
  - `api/routers/gm.py` `/api/gm`: `GET /sessions/{s}/timeline`, `GET/POST /sessions/{s}/regions/{r}/rumors`, `POST .../rumors/regen`, `PUT /sessions/{s}/rumors/{id}/support`, `PUT /sessions/{s}/regions/{r}/distortion`(저장된 행 반환), `GET /sessions/{s}/distortions`, `POST /sessions/{s}/advance`, `GET/POST /sessions/{s}/events`, `POST .../events/{e}/resolve|approve`, `DELETE .../events/{e}`, `POST /sessions/{s}/events/suggest?n=`.
  - **옛→새 경로표**(프론트 11.2와 API 테스트 10.3이 이 표를 따른다):

    | 옛 (현재 코드) | 새 |
    |---|---|
    | `GET /api/query/regions/{r}/knowledge?world_id=&include_rumors=` | `GET /api/knowledge/worlds/{w}/regions/{r}?include_hearsay=` |
    | `GET /api/query/diff?world_id=&region_a=&region_b=` | `GET /api/knowledge/worlds/{w}/diff?region_a=&region_b=` |
    | `/api/authoring/worlds/{w}/{build \| build/demo \| graph \| export \| priors \| related-priors \| regions/{r} \| knowledge/{k} \| nodes/{n}}` | `/api/world/worlds/{w}/…` (같은 꼬리·메서드) |
    | `POST /api/authoring/worlds/{w}/augment/session` | `POST /api/world/worlds/{w}/augmentation/runs` |
    | `POST /api/authoring/augment/{s}/answer` · `/revert` | `POST /api/world/augmentation/runs/{run}/answer` · `/revert` |
    | `POST\|GET /api/session/worlds/{w}/sessions`, `GET /api/session/sessions/{s}`, `POST …/close`, `GET …/regions/{r}/knowledge` | `/api/play/…` (같은 꼬리) |
    | `GET /api/session/sessions/{s}/timeline`, `GET\|POST …/regions/{r}/rumors`, `POST …/rumors/regen`, `PUT …/rumors/{id}/support`, `PUT …/regions/{r}/distortion`, `GET …/distortions`, `GET\|POST …/events`, `POST …/events/{e}/resolve` · `/approve`, `DELETE …/events/{e}` | `/api/gm/…` (같은 꼬리) |
    | `POST /api/session/sessions/{s}/advance-turn` | `POST /api/gm/sessions/{s}/advance` |
    | `POST /api/session/sessions/{s}/suggest-events?n=` | `POST /api/gm/sessions/{s}/events/suggest?n=` |

  - 오류 매핑(`LookupError→404`, `SessionClosedError→409`, `ValueError→400`, 경계 없음→503) 공통 헬퍼 `api/errors.py`. 옛 `query.py`·`authoring.py`·`session.py` 삭제.
- [x] 8.6 `compileall`.

### Step 9 — CLI
- [x] 9.1 `locus/__main__.py`: `assemble_shared`를 **플래그별로 부분 조립**해 씀 — `--world`: `graph=True, search=True, sql=False, llm=False`로 연결 뒤 `ensure_world_schema`; `--play` / `--localization`: `sql=True`만 연결 뒤 `ensure_play_schema` / `ensure_localization_schema`; 플래그 없으면 전부(각 경계 스키마 순서대로). PostgreSQL 없이 `--world`만, Neo4j·OpenSearch 없이 `--play`·`--localization`만 가능; `build-world`·`export`는 새 이름(`WorldBuilder`, `WorldFileExporter`)으로 동작 동일. `world import`·`demo` 서브커맨드는 U2.

### Step 10 — 테스트 재배치·갱신 (US-7.4)
- [x] 10.1 `git mv`: `tests/models → tests/shared/models`, `tests/llm → tests/shared/llm`, `tests/storage/test_storage.py → tests/shared/storage/`, `tests/consensus + tests/query/test_query.py → tests/knowledge/`, `tests/{ingestion,topology,ontology,commonsense_wiki→wiki,augmentation(test_augmentation.py),services} → tests/world/`, `tests/session/* + tests/storage/test_postgres_session_repo.py → tests/play/`, `tests/translation/* + tests/storage/test_translation_repo.py → tests/localization/`, API 테스트(`tests/query/test_api.py`, `test_authoring_api.py`, `tests/augmentation/test_augment_api.py`, `tests/session/test_session_api.py`, `test_localization_api.py`) → `tests/api/`.
- [x] 10.2 import 경로·이름 갱신(`is_hearsay`, `path_decay`, `hearsay`, `include_hearsay`, `region_known`, `AugmentationRun`, `WorldBuilder`, `WorldEditor`, `WorldFileExporter`, `PostgresPlayRepository`, `InMemoryPlayRepository`, `SessionKnowledgeService`, `advance`, `SourceKind` 값). `test_game_master.py`는 파사드 없이 서비스 조합(`assemble_play`에 fake를 넣거나 직접 구성)으로 같은 시나리오를 검증하도록 고침. 번역 테스트 셋(`tests/localization/test_translation_service.py`·`test_translation_repo.py`, `tests/api/test_localization_api.py`)은 `TranslationStore` 새 이름(`get_many`/`upsert_many`)과 `enrich` 새 시그니처(매핑 반환)에 맞춰 갱신. 신규 `tests/world/test_demo.py`(4.5 지도 경로).
- [x] 10.3 API 테스트: `create_app(knowledge=…, world=…, play=…, localization=…)`에 fake 컨테이너를 넘기는 방식으로 전환; 새 접두어·DTO(`_ko` 필드 위치 동일)·503 경계 없음 케이스 1개 추가(US-7.2). 경로는 8.5의 옛→새 경로표를 따른다.
- [x] 10.4 `tests/test_boundaries.py`(US-7.2): `locus/` 아래 모듈의 `import`/`from … import`를 AST로 걷어 경계 행렬 위반(예: `shared → *`, `knowledge → world|play|localization`, `play → world|localization`, `world → play|localization`, `localization → knowledge|world|play`)을 실패로 만든다. `api/`는 **import하는 쪽으로만** 검사 밖(api → locus 허용)이고, **`locus/** → api` import는 위반으로 검사한다**(`SharedContainer`가 `locus/shared/wiring.py`에 있어야 하는 이유).
- [x] 10.5 포트 계약 테스트: 기존 `test_repository_contract.py`를 Store Protocol 묶음별 케이스로 나누고 인메모리·PostgreSQL(SQLite) 두 어댑터에 같은 케이스 실행(기존 방식 유지). `TranslationStore` 계약도 두 어댑터에. `ON CONFLICT` 멱등 케이스(같은 키로 두 번 upsert → 한 행·마지막 값)를 Rumor·Distortion·Translation 계약에 추가(5.4·7.2).
- [x] 10.6 `pytest -q` **전체 GREEN**(기대 = 281 − 1(2.5의 traverse 테스트) + 신규: `test_boundaries`·503 케이스·upsert 멱등 3·`test_demo`), `ruff check locus api tests`, `black --check`, `mypy locus api` 오류 수가 1.1의 기준선을 넘지 않음.

### Step 11 — 프론트 재배치 (F1·F5, 기능 동일)
- [x] 11.1 `web/package.json`: `react-router-dom@^6` 추가. `npm install`.
- [x] 11.2 **`git mv web/src/api.ts web/src/api/index.ts`**(파일과 디렉터리가 공존하지 않게) 뒤 넷으로 쪼갬: `web/src/api/{world,knowledge,play,gm}.ts` + `index.ts`(네 모듈을 합친 `api` 객체를 기존 이름으로 재노출 — 컴포넌트 import 경로 `../api` 유지). 옛 `/api/query|authoring|session` 경로를 부르는 파일은 `api.ts` 하나뿐임을 `grep -rn "/api/" web/src`로 확인하고, 경로를 8.5의 옛→새 경로표대로 바꾼다. `types.ts`: `KnowledgeView{is_hearsay, path_decay, distortion, source}`, `QueryResult`, `AugRun`(옛 `AugSession`), `WorldExport`에 `entities` 추가(타입 정합).
- [x] 11.3 라우팅(F1): `main.tsx`에 `BrowserRouter`; `routes/EditorPage.tsx`(옛 `App` 본문: Toolbar·Map·RegionPanel·AugmentPanel + `SessionBar`는 세션 선택 시 `/gm/:sessionId`로 이동), `routes/GmPage.tsx`(SessionBar·Map·RegionPanel(세션 뷰)·SessionPanel), `routes/PlayPage.tsx`(자리표시 "플레이어 모드는 U4"), `/` → `/editor/aldermoor` 리다이렉트. 기존 컴포넌트 파일 위치는 유지(features 분할은 U3·U4·U7).
- [x] 11.4 `RegionPanel` 배지: `is_hearsay ? "hearsay" : source?.startsWith("rumor") ? "rumor" : scope_type`. `LocalizedText`는 DTO `_ko` 그대로 사용.
- [x] 11.5 `web/src/__tests__` 갱신(경로·타입·배지 텍스트), `npm test` 24 GREEN, `npm run lint`(tsc) clean, `npm run build` OK. `vite.config.ts` 프록시(`/api`) 유지.

### Step 12 — 배포 파일 (US-1.1 일부)
- [x] 12.1 `Dockerfile`: `COPY api ./api` 추가, CMD 주석 갱신. 루트 `.dockerignore`(`.venv`, `data`, `web/node_modules`, `aidlc-docs`, `.git`, `*.pyc`).
- [x] 12.2 `docker-compose.yml` 앱 커맨드가 `uvicorn api.main:app`인지 확인만(프로파일 정리는 U8).

### Step 13 — 죽은 코드 정리 (테스트 없고 호출자 없는 것만)
- [x] 13.1 후보 확인 후 제거: `World`, `WikiBuildReport`, `*.embedding_ref`, `RegionLevel.DISTRICT`(수집이 만들지 않음 — enum 값은 남길지 확인), `Settings.debug`, `play/event/dynamics.merge_add`, `SUPPORT_DECAY` 상수·`evolve_support(decay=…)` 경로, `RunStore.delete`(미사용이면), `to_terrain_entity`(수집 미사용). 테스트가 참조하면 테스트와 함께 제거하되, 동작을 검증하는 테스트면 코드도 남긴다.
- [x] 13.2 헬퍼 통일(부분): `clamp` 5곳 → `shared/models/util.py::clamp01` 하나; 이름 정규화 6곳 → `world/ingestion/mapping.normalize_name` 하나. 결과 동일(기존 테스트로 확인).

### Step 14 — 문서
- [x] 14.1 `aidlc-docs/construction/U1-boundary-restructure/code/code-summary.md`: 이동표(옛 경로 → 새 경로), 이름 매핑, 삭제 목록, 새 파일 목록, 테스트 결과(베이스라인 대비), 남긴 TODO(U2~).
- [x] 14.2 `CLAUDE.md` "Tech Stack & Layout"·"Code" 줄을 새 트리로 갱신(README 전면 갱신은 U8). `aidlc-docs/operations/operations.md`에 `init-schema` 플래그 한 줄.

### Step 15 — 최종 검증
- [x] 15.1 `pytest -q`(전체), `npm test`, `ruff`, `black --check`, `tsc`, `vite build`, `test_boundaries` 통과. `docker build .` → 이미지에 `api/` 포함 확인. **`docker compose --profile service up -d` 뒤 `curl -sf localhost:8000/health`**(유닛 완료 기준 그대로, US-1.1 일부; 이 환경은 Docker 사용 가능). 의존 컨테이너를 띄우지 못하면 code-summary에 operator-run으로 적고 게이트에서 낮춘 기준으로 드러낸다. 라이브 Neo4j가 있으면 `locus build-world --world demo --demo`로 데모 월드를 재빌드(2.2 `SourceKind` 값 변경 때문; operator-run).
- [x] 15.2 결과를 code-summary에 기록하고 2-옵션 완료 메시지 제시.

---

## 스토리 추적
| 스토리 | 단계 |
|---|---|
| US-7.1 배치·용어·접두어 | 2~9, 11 |
| US-7.2 의존 방향·조립·포트·스키마 분리 | 2.3, 3.3, 4.7, 5.2, 6.4, 7, 8, 9, 10.4 |
| US-7.4 기존 테스트 GREEN | 1.1, 10, 15 |
| US-1.1 (일부) Docker `api/` | 12 |
| US-8.5 (일부) Tuning 분리 | 2.3, 6.2 |
| US-9.3 (구조) `TranslationStore` 분리 | 7 |
| US-5.1 (일부) `/gm/:sessionId` 스켈레톤 | 11.3 |
| US-7.3 (일부) 진행 중 STATUS docstring | 4.6 |

## 범위 밖(뒤 유닛)
`WorldCache`·NPC 모델·World File import·수집 결함(U2) · `PlayUnitOfWork` 구현·`advance(action)`·가드·예산(U4) · 대화·번역 동작 확장·UI 라벨(U5) · 행적(U6) · GM 화면 분할·E2/E4~E6(U7) · 데모 콘텐츠·README·CI(U8).

## PBT Compliance (Partial)
- PBT-02/03: 기존 hypothesis 테스트(models 왕복, consensus, weights, dynamics, mapping)를 이동만 한다 — compliant(변경 없음).
- PBT-07: 생성기는 기존 위치에서 `tests/<boundary>/strategies.py`로 옮겨 재사용 가능하게 한다.
- PBT-08: hypothesis 기본 설정 유지(seed 출력). CI 연동은 U8.
- PBT-09: hypothesis 유지 — compliant.
