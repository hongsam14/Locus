# Components — Purpose Restructure (2026-09-29)

> 근거: 요구사항 FR-A~I, 스토리 E1~E9, RE `architecture.md`·`code-structure.md`·`code-quality-assessment.md`, 설계 답 AD-R1~R8 (`plans/purpose-restructure-application-design-plan.md`).
> 상세 비즈니스 규칙(이동 비용 공식, 소문 상한 값, 프롬프트 문구 등)은 유닛별 Functional Design에서 정한다. 여기서는 **무엇이 있고, 무엇을 책임지고, 어떤 인터페이스로 만나는지**만 정한다.
> 표기: `(이동)` 기존 코드를 옮김 · `(이동+수정)` 옮기며 결함·규칙 변경 · `(신규)` 새로 만듦 · `(진행 중)` 옮기고 상태 표시만.

## 0. 경계와 패키지 트리 (AD-R1 = A)

```
locus/
├── shared/          공용: 모델·설정·LLM 포트·저장소 포트와 어댑터
├── knowledge/       지역 지식 계산: 합의·로더·캐시·질의 (순수 읽기 코어)
├── world/           월드 구성: 수집·토폴로지·온톨로지·wiki·보강·편집·World File·데모
├── play/            플레이: 세션·플레이어·이동·턴·소문·사건·NPC 대화·GM 도구·PostgreSQL
└── localization/    번역 캐시 (어느 경계에도 속하지 않음)
api/                 조립(컨테이너 넷) + 라우터 넷 (world / knowledge / play / gm)
web/                 화면 셋 (editor / play / gm) — react-router
```

허용 의존 방향(FR-A2): `knowledge → shared` · `world → knowledge → shared` · `play → knowledge → shared` · `localization → shared` · `api → 전부`. **play는 localization을 import하지 않는다**(번역은 API 계층에서 응답에 입힌다). 자세한 행렬은 `component-dependency.md`.

---

## 1. shared — 공용

### S1 `shared/models` (이동+수정)
- **Purpose**: 경계를 넘는 도메인 어휘.
- **Responsibilities**: 캐노니컬 노드·엣지 모델(Region, Entity, Relation, Knowledge, WikiPrior, **NPC**(신규), ConnectionEdge, ScopeLink), 집계(RegionTopology, KnowledgeGraph, **WorldSnapshot**(신규: kg + topo + npcs + 이름 색인)), 뷰(ConsensusView, KnowledgeView, QueryResult, RegionDiff), 리포트(BuildReport, ImportReport), enum.
- **수정**: `ScopeType`에 `HEARSAY` 추가, `ConsensusView.rumors → hearsay`, `KnowledgeView.distortion_degree → path_decay`, `KnowledgeView.*_ko` **제거**, `SourceKind`를 경계 중립 값(`input | inferred | augmentation | simulation | dialogue`)으로 정리(`SESSION_*` 제거). `World`·`WikiBuildReport`·`embedding_ref` 등 미사용 항목 제거.
- **Interfaces**: Pydantic 모델. 모든 경계가 import한다.

### S2 `shared/config` (이동+수정)
- **Purpose**: 환경 변수 → 설정 객체. 조정값 집약(FR-A7).
- **Responsibilities**: `Settings`(LLM·Neo4j·OpenSearch·PostgreSQL·번역), `WorldTuning`(가중치 표, dedup 임계, 고증 수, 저신뢰 기준), `KnowledgeTuning`(propagate_min, hearsay_min), `PlayTuning`(이벤트 델타, 전파 최소 가중치, 승격 기준, 감쇠·가지치기·되먹임, **소문 상한·턴당 LLM 상한**, 이동 비용 파라미터), `LocalizationSettings`.
- **수정**: play 모듈 import 제거(역방향 의존 해소). 조정값 dataclass는 shared에 두고 값만 담는다.
- **Interfaces**: `get_settings()`, `Settings.world_tuning()/knowledge_tuning()/play_tuning()`.

### S3 `shared/llm` (이동)
- **Purpose**: LLM·VLM·임베딩 포트와 OpenAI 어댑터.
- **Responsibilities**: 변경 없음. 새 호출자(NPC 대화, NPC 초안, 사건 제안 컨텍스트)가 `LLMProvider.structured/complete`를 쓴다.

### S4 `shared/storage` (이동+수정)
- **Purpose**: 캐노니컬 저장 포트·어댑터·매핑.
- **Responsibilities**: `GraphRepository`·`SearchRepository` 포트, Neo4j·OpenSearch 어댑터, `graph_mapping`(+ `npc_to_node`, `lives_in_edges`, `node_to_npc`, 관계 역매핑), `persist_graph`, 캐노니컬 `SchemaInitializer`.
- **수정**: `postgres_session_repo.py`는 play로 이동. 미사용 포트 메서드(`traverse`, `get_region_subtree`, `get_region_ancestors`) 제거, `delete_world`는 유지하고 실제로 쓴다(재빌드·import). `Relation` 레이블 제약 제거.

### S5 `shared/storage/sql.py` (신규)
- **Purpose**: SQLAlchemy 엔진 팩토리. play와 localization이 같은 PostgreSQL을 쓰되 각자 테이블·스키마 초기화를 가진다.
- **Interfaces**: `make_engine(url) -> Engine`.

---

## 2. knowledge — 지역 지식 계산

### K1 `knowledge/consensus.py` (이동+수정)
- **Purpose**: **핵심 산출물 2** — 지역별 "아는 것" 계산(순수).
- **Responsibilities**: direct / inherited / global / propagated / **hearsay** 분류, `ConsensusParams`(KnowledgeTuning에서 생성). A10 특이점(가장 강한 경로 우선, unknown_count 정확화)은 FD에서 규칙 확정.
- **Interfaces**: `compute_consensus(region_id, *, snapshot, params) -> ConsensusView`, `ConsensusEngine(snapshot, params).resolve(region_id)`.

### K2 `knowledge/propagation.py` (이동)
- **Purpose**: 최대 곱 경로 가중치. `best_path_weights(start, connections)`. play의 이벤트 전파와 이동 비용이 재사용한다.

### K3 `knowledge/loader.py` (이동+수정)
- **Purpose**: Neo4j에서 월드 스냅샷을 읽는다.
- **Responsibilities**: Region·Entity·Knowledge·**NPC** 노드 + `CONNECTED_TO`·`SCOPED_TO`·**`RELATED_TO`**·`LIVES_IN` 엣지 → `WorldSnapshot`. 지역 이름 색인 포함(UUID → 이름).
- **Interfaces**: `WorldLoader(graph).load(world_id) -> WorldSnapshot`.

### K4 `knowledge/cache.py` (신규)
- **Purpose**: 월드 스냅샷 캐시(NFR-3). 플레이 중 행동마다 전체 로드를 막는다.
- **Responsibilities**: `world_id` 키 캐시, `invalidate(world_id)`(편집·import·재빌드 시 world가 호출), 프로세스 메모리, 스레드 안전.
- **Interfaces**: `WorldCache(loader).get(world_id) -> WorldSnapshot`, `.invalidate(world_id)`.

### K5 `knowledge/query.py` (이동+수정)
- **Purpose**: 캐노니컬 지역 지식 서빙과 읽기 API.
- **Responsibilities**: `knowledge_for_region`, `diff_regions`, **`region_known(view)`**(옛 `canonical_known`을 일반 API로), **`region_briefs(world_id)`**(사건 제안 컨텍스트용: 이름·설명·주요 지식), `KnowledgeView.title` 채움(A8).
- **Interfaces**: `QueryEngine(cache, params)`.

### K6 `knowledge/wiring.py` (신규)
- **Purpose**: 조립. `assemble_knowledge(shared: SharedContainer) -> KnowledgeContainer(loader, cache, query, params)`.

---

## 3. world — 월드 구성

### W1 `world/ingestion/` (이동+수정)
- **Purpose**: 자료 → 후보 구조.
- **수정**: `WorldInputs`의 이미지를 base64 문자열로 받고 디코드(A7); `merge_regions`가 연결 힌트·parent_name을 보존(A1); `merge_entities`가 id 재매핑을 반환하고 관계·ABOUT을 다시 잇는다(A2); 이름 정규화 헬퍼를 `mapping.normalize_name` 하나로 통일. 컨셉아트 수집은 **(진행 중)** 표시.
- **Interfaces**: `IngestionService.ingest_all(world_id, inputs) -> IngestionResult`(errors 포함).

### W2 `world/topology/` (이동+수정)
- **Purpose**: **핵심 산출물 1** — 지역 계층 + 가중치 연결.
- **수정**: 경고를 버리지 않고 `BuildReport`로 올림(A13); 이름 같고 레벨 다른 지역의 결정적 해석 규칙(A11, FD); `WorldTuning`에서 가중치 표를 받음.

### W3 `world/ontology/` (이동+수정)
- **Purpose**: 스코핑·고증·중복 제거·정합.
- **수정**: 스코프 못 한 지식 id를 `BuildReport.unscoped_knowledge_ids`로 노출(A4); 헬퍼 중복 제거.

### W4 `world/wiki/` (이동, 일부 진행 중)
- **Purpose**: 월드별 상식 prior. 조회·증류·연결·관리.
- **Responsibilities**: 기존 동작 유지. `cross_world.py`는 **(진행 중)**(A6 필터 결함은 P2). 에디터가 prior 목록과 근거 참조를 읽을 수 있게 `WikiAdmin.list_priors`·`prior_refs_for(edge|knowledge)`를 노출(FR-B7).

### W5 `world/augmentation/` (이동+수정)
- **Purpose**: 기획자 보강 Q&A — 에디터에 통합(FR-B6).
- **수정**: `AugmentationSession → AugmentationRun`(용어 분리), 질문에 `target_ids`·`region_id` 포함(B1), 답 적용 시 대상 필수·빈 노드 생성 금지, 되돌리기는 같은 run 안에서(B2), Entity confirm/edit 안전(B3), 선택지 고정 enum(B4), 탐지기가 `terrain_kind`를 읽음(B5), 끊긴 관계 탐지가 `RELATED_TO` 재독으로 실제 동작(FR-B10). `graph.py`(LangGraph)는 **(진행 중)**.
- **Interfaces**: `AugmentationService.start_run(world_id) -> AugmentationRun`, `.answer(run_id, answer) -> ChangeSet`, `.revert(run_id, change_id)`, `.get_run(run_id)`.

### W6 `world/build.py` — `WorldBuilder` (이동+수정, 옛 `PipelineOrchestrator`)
- **Purpose**: 빌드 파이프라인 조립: 수집 → 토폴로지 → wiki 증류·연결 → 온톨로지 → 저장.
- **수정**: `replace=True`면 `delete_world` 뒤 저장(A3); `CommonsenseWiki`를 생성자 주입(덕 타이핑 제거); 빌드마다 새 빌더 인스턴스(공유 상태 경합 A12 해소); 리포트에 경고·미해석 지식·LLM 호출 수(NFR-5); 빌드 뒤 `WorldCache.invalidate`.
- **Interfaces**: `WorldBuilder.build(world_id, inputs, *, replace: bool) -> BuildReport`.

### W7 `world/editor.py` — `WorldEditor` (이동+수정, 옛 `GraphEditor`)
- **Purpose**: UI 직접 편집(FR-B2). 지역·연결·지식·스코프·NPC.
- **Responsibilities**: 지역 upsert/삭제(붙은 연결·스코프·NPC 처리 규칙 FD), 연결 upsert/삭제(양방향 `CONNECTED_TO`, 가중치), 지식 upsert + 스코프 설정, 스코프 없음 목록, NPC upsert/삭제, 노드 삭제 시 OpenSearch 문서도 삭제, 편집 뒤 캐시 무효화, 월드 목록(`list_worlds`).
- **Interfaces**: `component-methods.md` 참조.

### W8 `world/npc_drafts.py` — `NpcDraftService` (신규)
- **Purpose**: 지역 지식에 맞는 NPC 초안 제안(FR-F3, P1).
- **Interfaces**: `suggest(world_id, region_id, *, n=3) -> list[NpcDraft]` (LLM 실패 시 빈 목록).

### W9 `world/worldfile/` (신규; `export.py`는 옛 `Exporter` 이동)
- **Purpose**: World File v1 저장·로드(FR-B8).
- **Responsibilities**: `schema.py`(`WorldFile{format_version, world: {id,name,description}, regions, connections, entities, relations, knowledge, scopes, priors, prior_links, npcs}`), `export.py`(`WorldFileExporter.export(world_id) -> WorldFile`), `import_.py`(`WorldFileImporter.import_(world_id, file, *, replace=True) -> ImportReport`: 버전 검사 → (열린 세션 경고는 API 계층) → `delete_world` → `persist_graph` → 캐시 무효화). 저장 → 로드 → 저장 동일(PBT-02).

### W10 `world/demo/` (이동+수정, 옛 `demo.py` + `examples/demo_world`)
- **Purpose**: 원클릭 데모 월드(FR-B3). LLM 없이 로드되는 World File을 **패키지 안에** 둔다(Docker에서도 동작).
- **Interfaces**: `DemoWorlds.list() -> list[DemoInfo]`, `DemoWorlds.load(name, world_id, *, replace=True) -> ImportReport`(내부적으로 W9 importer). 옛 `--demo` 원자료 빌드 경로는 `DemoWorlds.build_from_sources`로 남긴다(개발용).

### W11 `world/wiring.py` (신규)
- `assemble_world(shared, knowledge) -> WorldContainer(builder, editor, augmentation, wiki_admin, cross_world, exporter, importer, demo, npc_drafts)`.

### W12 진행 중 모듈 표시 (FR-I, FR-H3)
- `ingestion/concept_art_ingestor.py`, `wiki/cross_world.py`, `augmentation/graph.py` — 모듈 docstring 첫 줄에 `STATUS: in-progress — <이유>`. README "진행 중 기능" 절과 일치.

---

## 4. play — 플레이

### P1 `play/models.py` (이동+수정)
- **Purpose**: 플레이 도메인.
- **Responsibilities**: `GameSession`, **`Player`**(id, session_id, name, region_id, turn_spent), `SessionRumor`, `RegionDistortion`, `TimelineEntry`(kind에 `SESSION_STARTED/CLOSED`, `EVENT_APPROVED/DISCARDED`, `PLAYER_MOVED`, `NPC_TALKED` 추가), `SessionEvent`(애그리거트 유지, `resolve`는 ACTIVE에서만), **`Conversation`/`Message`**, **`PlayerAction`**(`Move(to_region_id)`, `Wait`, `EndTalk(npc_id)`), **`ActionResult`**(turns: list[TurnResult], player, summary: list[RegionTurnChange], llm_calls), `RegionTurnChange`(region_name 포함).
- **수정**: `Translation` 제거(localization로), `statement_ko`·`description_ko` 제거.

### P2 `play/ports.py` (신규, 옛 `SessionRepository` 분할 — AD-R3 = A)
- **Purpose**: 관심사별 저장 포트.
- **Interfaces**: `SessionStore`, `PlayerStore`, `RumorStore`, `EventStore`, `DistortionStore`, `TimelineStore`, `ConversationStore` (각 Protocol) + `PlayUnitOfWork`(`with uow: ...` — 한 트랜잭션으로 여러 store 쓰기).

### P3 `play/storage/` (이동+수정)
- **Purpose**: 어댑터.
- **Responsibilities**: `postgres_repo.py` — `PostgresPlayRepository`가 P2 포트 전부 + `PlayUnitOfWork` 구현(엔진 공유, upsert는 `ON CONFLICT`로 경합 제거), `memory_repo.py` — 인메모리 동등 구현(계약 테스트 공유), `schema.py` — play 테이블 초기화(`players`, `conversations`, `messages` 추가; `translations`는 제외).

### P4 `play/session_service.py` (이동+수정)
- **Purpose**: 세션 생애주기 + 플레이어 생성(FR-C1).
- **수정**: `start(world_id, player: PlayerCreate)`가 세션·플레이어·지역 왜곡도 초기화를 **하나의 UoW**로(C4), 시작·종료를 타임라인에 기록(E4), 지역 확인은 `WorldCache` 스냅샷으로(전체 로드 반복 제거). 월드 스냅샷에 새 지역이 있으면 왜곡도 기본값을 채우는 `sync_regions`(C12).

### P5 `play/player/movement.py` (신규, 순수)
- **Purpose**: 이동 규칙(FR-C2). 공식은 FD.
- **Interfaces**: `move_options(snapshot, from_region_id, tuning) -> list[MoveOption(region_id, name, kind, weight, cost_turns, passable)]`, `move_cost(edge, tuning) -> int`. 불변식: 가중치 낮을수록 cost 크거나 같음, `blocked`는 `passable=False`(A-2).

### P6 `play/player/play_service.py` — `PlayService` (신규)
- **Purpose**: 플레이어 시점 유스케이스(FR-C3·C5).
- **Responsibilities**: 현재 지역 화면 데이터(`RegionView`: 지역 이름·설명·계층 경로·NPC 목록·들리는 이야기(K5 `region_known` + 활성 소문, hearsay 표시)·이동 옵션), 행동 검증(도달 가능·통과 가능) 뒤 `TurnAdvancer.advance(session_id, action)`에 위임(AD-R5 = B), 플레이 로그(플레이어 시점 필터).
- **Interfaces**: `current_region(session_id) -> RegionView`, `act(session_id, action: PlayerAction) -> ActionResult`, `log(session_id) -> list[TimelineEntry]`.

### P7 `play/turn/advancer.py` — `TurnAdvancer` (이동+수정)
- **Purpose**: play의 **유일한 시간 진행 진입점**(AD-R4·R5).
- **Responsibilities**: `advance(session_id, action: PlayerAction | None) -> ActionResult`: 행동 → 턴 비용(P5) → 비용만큼 한 턴 처리 반복(이벤트 적용·전파 → 소문 추가(상한) → 되먹임 → 지지도 → 가지치기 → 승격 → 저장) → 플레이어 상태 갱신(이동이면 위치) → 지역별 변동 요약. `action=None`은 GM 수동 1턴. **동시성 가드**(`turn/guard.py`: 세션별 in-process 락 + 진행 중 플래그 → 두 번째 요청 409)(C3). LLM 호출은 UoW 밖에서, 저장은 UoW 하나로. 턴당 LLM 호출·새 소문 상한(FR-E1) 적용, `llm_calls` 집계(NFR-5).
- **Interfaces**: 위 하나. 반환의 `turns`에 기존 `TurnResult`가 턴 수만큼 들어간다(기존 테스트 보존).

### P8 `play/rumor/` (이동+수정)
- **Purpose**: 소문 생성·왜곡 체인·지지도·승격·되먹임.
- **수정**: `rumor_service.py` — 원본 수집 시 "이미 파생 소문을 낳은 캐노니컬 지식 제외" + 지역당 활성 소문 상한(E1); 재생성은 부모를 `active=False`로(E5, 삭제 방식 통일). `rumor_dynamics.py` — 강화 지역 판정에서 "승격 소문 존재"를 제외하고 되먹임 왜곡을 복원 가능한 기여로 기록(E2). `promotion.py`, `rumor_generator.py`, `feedback_service.py`는 이동.

### P9 `play/event/` (이동+수정)
- **Purpose**: 사건 생성·제안·승인·해결·전파.
- **수정**: `event_suggester.suggest(*, briefs: list[RegionBrief], recent_events, turn, n)` — K5 `region_briefs`와 최근 사건을 컨텍스트로(D2); `n` 상한은 API 계층(NFR-6); 승인은 `EVENT_APPROVED`, 폐기는 `EVENT_DISCARDED` 기록(E4); SUGGESTED 해결 거부(C5). `dynamics.py`의 죽은 경로(`merge_add`, `SUPPORT_DECAY`) 제거.

### P10 `play/distortion_service.py` (이동+수정)
- 지역 확인을 스냅샷으로; 응답은 저장된 행을 그대로 반환.

### P11 `play/turn/changes.py` (이동+수정)
- `shape_region_changes`에 지역 이름 주입(D3), 되먹임 지역도 변동에 포함(RE 미완성 항목).

### P12 `play/npc/scope.py` — `NpcScope` (신규, 순수)
- **Purpose**: "NPC가 아는 범위"(FR-F4). Locus의 핵심 불변식.
- **Interfaces**: `build_context(*, npc: NPC, known: list[KnowledgeView], rumors: list[SessionRumor], recent: list[Message], limits) -> NpcContext(facts, hearsay, rumors, persona, allowed_ids)`. 불변식(PBT-03): `context`에 든 지식 id ⊆ `known` ∪ 그 지역 활성 소문 id.

### P13 `play/npc/dialogue_service.py` — `NpcDialogueService` (신규)
- **Purpose**: LLM NPC 대화(FR-C4, G3).
- **Responsibilities**: 대화 시작·이력, 컨텍스트(P12 ← K5 `region_known` + P8 활성 소문), 프롬프트 가드("모르면 모른다, 소문은 들은 대로, 승격 소문은 확신"), 표시 언어로 직접 생성(A-1), 대화 1턴 = LLM 1회, 메시지 저장(`ConversationStore`), `EndTalk` 행동은 P6/P7 경로.
- **Interfaces**: `start(session_id, npc_id) -> Conversation`, `say(session_id, npc_id, text) -> NpcReply`, `history(session_id, npc_id) -> Conversation`.

### P14 `play/region_knowledge.py` — `SessionKnowledgeService` (이동+수정, 옛 `SessionQueryEngine`)
- **Purpose**: 세션 지역 지식(캐노니컬 known + 활성 소문) — 외부 소비자 계약 유지(FR-F5)이자 P6·P13의 입력.
- **수정**: 번역 호출 제거(API 계층으로), 승격 여부를 `KnowledgeView.source`로 구분(`rumor:promoted` / `rumor`), 캐시 스냅샷 사용.

### P15 `play/wiring.py` (신규)
- `assemble_play(shared, knowledge) -> PlayContainer(sessions, play, turns, rumors, events, distortions, dialogue, region_knowledge, uow)`.

---

## 5. localization — 번역

### L1 `localization/models.py` (이동) — `Translation`.
### L2 `localization/ports.py` + `storage/` (이동+수정) — `TranslationStore` Protocol, `PostgresTranslationRepository`, 인메모리, 자체 `schema.py`(`translations` 테이블). play 모델 import 없음(FR-G1).
### L3 `localization/translator.py` (이동) — `Translator.try_translate`.
### L4 `localization/service.py` (이동+수정) — `TranslationService.enrich(items, *, kind, fields, lang, world_id, session_id=None) -> dict[item_id, dict[field, str]]`: 캐시 읽기 + 백그라운드 워밍, **중복 요청 억제**(in-flight 집합), 고아 행 정리 `purge(kind, ids)`(G4). 반환은 매핑이며 도메인 모델을 바꾸지 않는다.
### L5 `localization/wiring.py` (신규) — `assemble_localization(shared) -> LocalizationContainer(translations)`.

---

## 6. api — 조립과 라우터

### A1 `api/main.py` (수정)
- **Purpose**: 앱 생성. `create_app(*, shared=None, knowledge=None, world=None, play=None, localization=None)`. 넘기지 않은 컨테이너는 lifespan에서 `assemble_*`로 만든다(`on_event` 대신 lifespan). 한 경계 조립이 실패하면 그 경계만 `None` → 해당 라우터 503, 나머지 정상(FR-A3). `ThreadPoolExecutor`는 lifespan 종료 시 닫는다.
### A2 `api/deps.py` (신규) — `Depends` 제공자: `get_world() -> WorldContainer` 등(없으면 503).
### A3 `api/schemas.py` (신규) — 응답 DTO. 번역 필드(`*_ko`)와 지역 이름 등 표시용 필드는 여기서만 붙인다(도메인 모델 청결).
### A4 `api/routers/world.py` `/api/world` — 빌드(multipart/base64), 편집, 스코프, NPC, 보강 run, wiki 목록·근거, World File export/import, 데모 로드, 월드 목록.
### A5 `api/routers/knowledge.py` `/api/knowledge` — 캐노니컬 지역 지식, 비교, region briefs.
### A6 `api/routers/play.py` `/api/play` — 세션 시작(플레이어 포함)·종료·목록, 현재 지역, 이동 옵션, 행동(`act`), 대화(start/say/history), 플레이 로그, 세션 지역 지식(FR-F5), 응답에 번역 입힘.
### A7 `api/routers/gm.py` `/api/gm` — 사건(생성·제안·승인·해결·폐기, `n` 상한), 소문(목록·생성·재생성·지지도), 왜곡도, 수동 턴(`advance(action=None)`), 타임라인, 세계 상태(지역별 왜곡도·소문 수·승격 수).

---

## 7. web — 화면 (AD-R8 = A)

### F1 `App.tsx` + `routes/` (신규) — react-router: `/`(월드 목록·데모 로드), `/editor/:worldId`, `/play/:sessionId`, `/gm/:sessionId`.
### F2 `features/editor/` (신규, 일부 이동) — MapCanvas(편집 모드: 지역 추가·드래그·연결 긋기), RegionInspector(지식·스코프·NPC), UploadPanel(자료), AugmentPanel(run 기반, 대상 표시), WikiPanel, BuildReportPanel, WorldFileBar(저장·불러오기).
### F3 `features/play/` (신규) — RegionScene(현재 지역), MovePanel, NpcList + DialoguePanel, PlayLog, ActionBar(기다리기), TurnSummaryToast.
### F4 `features/gm/` (이동+분할, 옛 `SessionPanel` 518줄) — EventPanel, RumorPanel, DistortionPanel, TimelinePanel, WorldStateOverlay, ManualTurnButton.
### F5 `api/{world,knowledge,play,gm}.ts` (수정) — 라우터별 클라이언트. 타입은 백엔드 OpenAPI에서 생성(`openapi-typescript`, P1)하거나 손으로 쓰되 계약 테스트를 둔다.
### F6 `i18n/` (수정) — 전 화면 라벨, en·ko 사전.
### F7 `ui/` (유지) — Doodly 프리미티브. 미사용 톤·prop 정리.

---

## 8. 스토리·요구사항 커버리지 (요약)
- FR-A1~A7 → §0, S2, K6·W11·P15·L5, A1·A2, P2·P3, 용어 매핑(`application-design.md` §5).
- FR-B → W1·W2·W3·W5·W6·W7·W8·W9·W10 + A4 + F2. FR-C → P4·P5·P6·P7·P13 + A6 + F3. FR-D → P7·P9·P10·P11 + A7 + F4. FR-E → P7·P8·P9. FR-F → S1(NPC)·W7·W8·P12·P13·P14. FR-G → L1~L5 + A3(응답에서만). FR-H → W10·A1·(U7 문서). FR-I → W12.
- 자세한 행렬은 `application-design.md` §8.

---

## 9. 변경 (2026-09-29): 플레이어 행적과 세션 기원 소문 — AD-R9 = B(+NPC 판단), AD-R10 = A

> 근거: 요구사항 부록 A(FR-C8·C9·C10·E7·D6, 가정 A-6·A-7), 스토리 US-4.4·4.5·5.6·6.5·8.6. 레거시 Locus와 갈라지는 지점: 플레이어가 세계에 흔적을 남긴다.

### 신규 컴포넌트

#### P16 `play/deeds/` — `Deed`, `DeedAppraisal`, `DeedService` (신규)
- **Purpose**: 플레이어 행적을 기록하고, NPC 판단을 붙이고, 소문 씨앗 후보를 내놓는다(FR-C8·C10).
- **Responsibilities**: `Deed{id, session_id, player_id, region_id, turn, kind: arrival|statement|declared_action, text, witnessed_npc_ids, voided}`, `DeedAppraisal{deed_id, npc_id, noteworthy, salience(0..1), slant, retelling, turn}`. 기록 지점 — `Move`(arrival), `EndTalk`(statement 요약), `Declare`(declared_action). 판단은 **대화한 NPC**가 `EndTalk` 때 그 지역의 미판단 행적에 대해 내린다(P13이 LLM 1회로 수행, P16이 저장). 미판단·`noteworthy=false` 행적은 씨앗이 아니다(A-6). `void(deed_id)`는 그 행적에서 난 소문을 모두 비활성화한다(FR-D6).
- **Interfaces**: `DeedService.record(...)`, `.pending_for(session_id, region_id)`, `.attach_appraisals(...)`, `.seeds_for_turn(session_id)`, `.void(session_id, deed_id)`, `.list(session_id)`; `DeedStore` 포트(P2에 8번째 포트로 추가).

#### P17 `play/gm/narrator.py` — `GmNarrator` (신규)
- **Purpose**: 선언 행동의 결과를 짧게 서술한다(FR-C9, A-7). 판정 없음.
- **Interfaces**: `narrate(*, declaration: str, region_view: RegionView, npcs: list[NPC], lang) -> Narration(text, llm_calls=1)`. 결과는 P16이 `declared_action` 행적으로 기록한다.

#### P19 `play/rumor/spread.py` — 세션 기원 소문 전파 (신규, 순수)
- **Purpose**: 행적 기원 소문이 토폴로지를 따라 퍼질 대상을 계산한다(FR-E7).
- **Interfaces**: `plan_spread(snapshot, rumor: SessionRumor, reached: set[region_id], tuning) -> list[SpreadTarget(region_id, degree, support)]` — `w = best_path_weights(origin)[target] ≥ tuning.spread_min_weight`, `degree = max(rumor.distortion_degree, 1 − w)`, `support = rumor.support × w`, 이미 도달한 지역과 원점 제외. 불변식(PBT-03): 대상 가중치 ≥ 기준, 왜곡도 단조, `(origin_deed_id, region_id)` 중복 없음. 텍스트 왜곡은 P8 `RumorGenerator`가 맡는다(LLM 1회/대상). **캐노니컬 기원 소문은 전파하지 않는다.**

### 기존 컴포넌트 변경
- **P1 models**: `PlayerAction`에 `Declare(text)` 추가. `SessionRumor`에 `origin_kind: canonical|deed`, `origin_deed_id: str | None`, `spread_from_region_id: str | None` 추가. `TimelineKind`에 `DEED_RECORDED`, `DEED_APPRAISED`, `DEED_VOIDED`, `RUMOR_SPREAD`, `ACTION_DECLARED` 추가. `ActionResult.narration`에 GM 서술이 들어간다.
- **P2 ports**: `DeedStore`(record/get/list_by_session/list_pending_by_region/save_appraisals/void) 추가 → play 포트 8개. `RumorStore`에 `list_session_origin(session_id)`, `deactivate_by_deed(deed_id)` 추가.
- **P3 storage**: `deeds`, `deed_appraisals` 테이블, `session_rumors`에 `origin_kind`·`origin_deed_id`·`spread_from_region_id` 열. 인메모리 동등 구현.
- **P6 PlayService**: `act`에서 `Move` → 도착 행적 기록(P16), `Declare` → P17 서술 → 행적 기록 → 1턴, `EndTalk` → P13 판단 트리거 → 1턴. `current_region`의 `rumors`에 행적 기원 소문도 포함(이미 활성 소문이므로 자연히 포함).
- **P7 TurnAdvancer**: 한 턴 처리에 두 단계 추가 — (2b) **행적 씨앗**: `DeedService.seeds_for_turn`의 판단(`noteworthy`, `salience ≥ tuning.deed_seed_min_salience`)마다 그 NPC의 지역에 `retelling`을 원문으로 소문 체인 1개 생성(탄생 지지도 = f(salience)), 출처 `deed`. (2c) **소문 전파**: 활성 세션 기원 소문마다 `plan_spread` → 대상 지역에 왜곡 소문 생성(P8 generator), `RUMOR_SPREAD` 타임라인. 두 단계 모두 지역당 상한·`LlmBudget`을 따른다(FR-E1). 순서: 사건 적용 → 캐노니컬 소문 추가 → **행적 씨앗 → 전파** → 되먹임 → 지지도 → 가지치기 → 승격 → 저장.
- **P8 RumorService**: `seed_from_appraisal(session, appraisal, *, budget)`, `spread(session, rumor, targets, *, budget)` 추가. 재생성(regenerate)은 캐노니컬 기원 소문만 새로 만들고 세션 기원 소문은 유지한다(플레이어의 흔적을 지우지 않는다).
- **P9 EventSuggester**: 컨텍스트에 최근 행적(요약)을 넣는다(FR-D2 보강).
- **P12 NpcScope**: 컨텍스트에 "이 NPC가 판단한 행적"을 넣는다(자기가 본 일은 안다). 불변식은 그대로: 컨텍스트 지식 id ⊆ known ∪ 지역 활성 소문 ∪ 자기 판단 행적.
- **P13 NpcDialogueService**: `appraise(session_id, npc_id, deeds: list[Deed]) -> list[DeedAppraisal]` 추가 — NPC 페르소나로 LLM 1회, 여러 행적을 한 번에 판단. `EndTalk` 흐름에서 P6이 호출한다.
- **A6 play router**: `act`가 `{type:"declare", text}` 수용(길이 상한, NFR-6). 응답 `ActionResult.narration`.
- **A7 gm router**: `GET /sessions/{s}/deeds`(행적 + 판단 + 도달 지역), `POST /sessions/{s}/deeds/{d}/void`.
- **F3 play feature**: `ActionBar`에 자유 텍스트 선언 입력과 서술 표시(`NarrationCard`). `RegionScene`의 소문 항목에 "행적 기원" 표시.
- **F4 gm feature**: `DeedPanel`(행적·판단·전파 경로·취소) 추가. `WorldStateOverlay`에 행적 소문 도달 지역 하이라이트(P1).
- **S1 models**: `SourceKind`에 `PLAYER` 추가(행적 provenance). `S2 PlayTuning`에 `spread_min_weight`, `deed_seed_min_salience`, `max_spread_per_region_turn`, `declare_max_chars` 추가.
