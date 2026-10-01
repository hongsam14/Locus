# API Documentation

> Reverse Engineering — Purpose Restructure Cycle (2026-09-29). 기준 커밋 `ee61277` (main).
> 범위: REST API 전체(34 엔드포인트), 내부 포트/서비스 API, 데이터 모델.
> "Web" 열은 `web/src/api.ts`가 호출하는지 여부.

## REST APIs

**공통 오류 매핑**: `app.state`에 서비스가 없으면 503(`_svc`), `LookupError`→404, `SessionClosedError`→409, `ValueError`→400(approve/discard). **인증 없음.**

### `api/main.py`

| Method | Path | Purpose | Request | Response | Web |
|---|---|---|---|---|---|
| GET | `/health` | 생존 확인. DB 연결은 확인하지 않음 | – | `{"status":"ok"}` | no |

### `api/routers/query.py` — prefix `/api/query` — NPC 서빙 (캐노니컬)

| Method | Path | Purpose | Request | Response | Web |
|---|---|---|---|---|---|
| GET | `/regions/{region_id}/knowledge` | **지역 X의 NPC가 아는 지식** (핵심 서빙 경로) | query `world_id`(필수), `include_rumors=true` | `QueryResult` | yes |
| GET | `/diff` | 두 지역의 공유/고유 지식 비교 | `world_id`, `region_a`, `region_b` | `RegionDiff` | no |

### `api/routers/authoring.py` — prefix `/api/authoring` — 기획자 도구

| Method | Path | Purpose | Request | Response | Web |
|---|---|---|---|---|---|
| POST | `/worlds/{world_id}/build` | 입력으로 월드 빌드 | body `WorldInputs{memos, map_images: bytes[], structured_maps, concept_arts}` | `BuildReport` | no |
| POST | `/worlds/{world_id}/build/demo` | 번들 데모 월드 빌드 | `with_map=true` | `BuildReport` | yes |
| GET | `/worlds/{world_id}/graph` | 노드 수 요약 | – | `GraphSummary` | no |
| GET | `/worlds/{world_id}/export` | 전체 그래프 (UI 지도 오버레이 페이로드) | – | `dict` (타입 없음) | yes |
| POST | `/worlds/{world_id}/priors` | WikiPrior upsert | body `WikiPrior` | `WikiPrior` | no |
| GET | `/worlds/{world_id}/related-priors` | 다른 월드의 prior 검색 | `query?`, `k=10` | `list[WikiPrior]` | no |
| PUT | `/worlds/{world_id}/regions/{region_id}` | Region upsert (경로 id 무시, body 사용) | body `Region` | `Region` | yes |
| PUT | `/worlds/{world_id}/knowledge/{knowledge_id}` | Knowledge upsert (경로 id 무시, scope 링크 생성 안 함) | body `Knowledge` | `Knowledge` | no |
| DELETE | `/worlds/{world_id}/nodes/{node_id}` | 노드 삭제 (Neo4j만; OpenSearch 문서 남음) | – | 204 | yes |
| POST | `/worlds/{world_id}/augment/session` | 보강 Q&A 세션 시작 (메모리 보관; 게임 세션과 다름) | – | `AugmentationSession` | yes |
| POST | `/augment/{session_id}/answer` | 답변 적용 | body `AugmentationAnswer` | `ChangeSet` | yes |
| POST | `/augment/{session_id}/revert` | 변경 되돌리기 | query `change_id` | 204 | yes |

토폴로지(연결·가중치)를 편집하는 엔드포인트는 **없다.**

### `api/routers/session.py` — prefix `/api/session` — 게임 세션 / GameMaster

| Method | Path | Service | Request | Response | Web |
|---|---|---|---|---|---|
| POST | `/worlds/{world_id}/sessions` | `session_service.start_session` | – | `GameSession` | yes |
| GET | `/worlds/{world_id}/sessions` | `list_sessions` | – | `list[GameSession]` | yes |
| GET | `/sessions/{session_id}` | `get_session` | – | `GameSession` | no |
| POST | `/sessions/{session_id}/close` | `close_session` | – | `GameSession` | yes |
| GET | `/sessions/{session_id}/timeline` | `get_timeline` | – | `list[TimelineEntry]` | yes |
| GET | `/sessions/{sid}/regions/{rid}/rumors` | `game_master.list_rumors` + `_attach_ko` | – | `list[SessionRumor]` (+`statement_ko`) | yes |
| POST | `/sessions/{sid}/regions/{rid}/rumors` | `generate_rumors` (LLM) | – | `list[SessionRumor]` | yes |
| POST | `/sessions/{sid}/regions/{rid}/rumors/regen` | `regenerate_region` (LLM) | – | `list[SessionRumor]` | yes |
| PUT | `/sessions/{sid}/rumors/{rumor_id}/support` | `adjust_support` | `SupportUpdate{support}` | `SessionRumor` | yes |
| PUT | `/sessions/{sid}/regions/{rid}/distortion` | `set_region_distortion` | `DistortionUpdate{degree}` | `RegionDistortion` (라우터가 조립) | yes |
| POST | `/sessions/{sid}/advance-turn` | `advance_turn` (LLM) | – | `TurnResult` | yes |
| GET | `/sessions/{sid}/regions/{rid}/knowledge` | **`session_query.knowledge_for_region`** | – | `QueryResult` (+`_ko`) | yes |
| GET | `/sessions/{sid}/events` | `list_events` + `_attach_ko` | `status?` (자유 문자열) | `list[SessionEvent]` | yes |
| POST | `/sessions/{sid}/events` | `create_event` | `EventCreate{region_id, category, description, magnitude, lifecycle?}` | `SessionEvent` | yes |
| POST | `/sessions/{sid}/events/{eid}/resolve` | `resolve_event` | – | `SessionEvent` | yes |
| DELETE | `/sessions/{sid}/events/{eid}` | `discard_event` (SUGGESTED만) | – | 204 | yes |
| POST | `/sessions/{sid}/suggest-events` | `suggest_events` (LLM) | `n=1` (상한 없음) | `list[SessionEvent]` | yes |
| POST | `/sessions/{sid}/events/{eid}/approve` | `approve_event` | – | `SessionEvent` | yes |
| GET | `/sessions/{sid}/distortions` | `list_distortions` | – | `list[RegionDistortion]` | yes |

세션 전체의 루머 목록, 수동 승격/강등, 가지치기된 루머 조회 엔드포인트는 없다. 웹의 "전체 생성"은 지역마다 GET/POST를 따로 보낸다(동시 5개).

### 엔드포인트 집계

| Router | 수 | 목적 태그 |
|---|---|---|
| main | 1 | INFRA |
| query | 2 | NPC-SERVE |
| authoring | 12 | DESIGNER (빌드·편집·보강·wiki) |
| session | 19 | SIMULATION (+ NPC-SERVE 1개) |
| **합계** | **34** | NPC 서빙 경로는 캐노니컬 1 + 세션 1 |

## Internal APIs

### 포트 (Protocol)

| Port | 위치 | 주요 메서드 | 운영 구현 | 테스트 대역 |
|---|---|---|---|---|
| `GraphRepository` | `locus/storage/base.py:56-74` | `connect/disconnect/health_check/ensure_schema`, `upsert_nodes`, `upsert_edges`, `get_node`, `find_nodes(world_id, label, filters?)`, `get_edges(world_id, types?)`, `delete_node`, `delete_world`, `traverse`, `get_region_subtree`, `get_region_ancestors` | `Neo4jGraphRepository` (MERGE, 노드/엣지마다 1 트랜잭션) | 테스트 파일마다 따로 만든 fake (공유 in-memory 어댑터 없음) |
| `SearchRepository` | `locus/storage/base.py:77-95` | `ensure_index`, `index(docs)`, `hybrid_search(world_id|None, query_text, query_embedding?, k, filters?)`, `delete_world` | `OpenSearchRepository` | 파일별 fake |
| `LLMProvider` | `locus/llm/base.py:17-27` | `complete(prompt, *, system)`, `structured(prompt, schema, *, system)` | `OpenAILLMProvider` (LangChain) | `_FakeLLM` 등 |
| `VLMProvider` | `locus/llm/base.py` | `analyze_image(image: bytes, prompt, *, system)` | `OpenAIVLMProvider` (MIME `image/png` 고정) | `_FakeVLM` |
| `EmbeddingProvider` | `locus/llm/base.py` | `dimension`, `embed(texts)` | `OpenAIEmbeddingProvider` | `_FakeEmbedding` 등 |
| `SessionRepository` | `locus/session/repository.py` | 약 27개: 세션·루머·왜곡·타임라인·이벤트·**번역 캐시** | `PostgresSessionRepository` (SQLAlchemy Core) | `InMemorySessionRepository` + 계약 테스트 |
| `SessionStore` (보강) | `locus/augmentation/session_store.py` | `save/get/delete` | `InMemorySessionStore` (재시작 시 유실) | 같은 구현 |

쓰이지 않는 포트 메서드: `traverse`, `get_region_subtree`, `get_region_ancestors`, `delete_world`(두 저장소 모두), `health_check`.

### 캐노니컬 서비스

| Class / Function | 위치 | 시그니처 (요약) |
|---|---|---|
| `PipelineOrchestrator` | `locus/services/orchestrator.py` | `.from_factory(factory, graph, search)`, `.build_world(world_id, inputs: WorldInputs) -> BuildReport` |
| `IngestionService` | `locus/ingestion/service.py` | `.ingest_all(world_id, inputs) -> IngestionResult` |
| `TopologyBuilder` | `locus/topology/builder.py` | `.set_wiki(wiki)`, `.build(ingestion, *, world_id) -> RegionTopology` |
| `OntologyBuilder` | `locus/ontology/builder.py` | `.build(ingestion, topology, *, world_id) -> KnowledgeGraph` |
| `compute_consensus` / `ConsensusEngine` | `locus/consensus/engine.py` | `ConsensusEngine(kg, topo, params).resolve(region_id) -> ConsensusView` |
| `best_path_weights` | `locus/consensus/propagation.py` | `(start_id, connections) -> dict[str, float]` (최대 곱 경로) |
| `WorldLoader` | `locus/query/loader.py` | `.load(world_id) -> (KnowledgeGraph, RegionTopology)` — 캐시 없음, 월드 전체 로드 |
| `QueryEngine` | `locus/query/engine.py` | `.knowledge_for_region(world_id, region_id, *, include_rumors=True) -> QueryResult`, `.diff_regions(...) -> RegionDiff` |
| `canonical_known` | `locus/query/engine.py:17-23` | 세션 쿼리 전용 (direct + inherited + global) |
| `GraphEditor` | `locus/services/editor.py` | `.upsert_region`, `.upsert_knowledge`, `.delete_node` |
| `Exporter` | `locus/services/exporter.py` | `.export_world(world_id) -> dict` (원시 그래프; 지역별 합의 결과 아님) |
| `CommonsenseWiki` | `locus/commonsense_wiki/base.py` | `.lookup_terrain_rule(feature)`, `.lookup_similar(query, k=5)` — 검색 실패 시 LLM 폴백 |
| `PriorDistiller` / `WikiPriorLinker` | `locus/commonsense_wiki/{distiller,linker}.py` | `.distill(ingestion, topology, *, world_id)`, `.link(priors, *, world_id)` |
| `WikiAdmin` / `CrossWorldWikiExplorer` | `locus/commonsense_wiki/{admin,cross_world}.py` | `.upsert_prior`, `.list_priors`, `.search_related_priors(world_id, query, k)` |
| `AugmentationService` | `locus/augmentation/service.py` | `.start_session(world_id)`, `.submit_answer(sid, answer)`, `.revert(sid, change_id)` |

### 세션 서비스

| Class / Function | 위치 | 시그니처 (요약) |
|---|---|---|
| `SessionService` | `locus/session/service.py` | `start_session(world_id)`, `close_session`, `get_session`, `list_sessions`, `get_timeline` |
| `GameMasterService` | `locus/session/game_master.py` | 하위 서비스 5개(rumors/events/distortions/feedback/turns)에 넘기기만 하는 파사드 |
| `RumorService` | `locus/session/rumor_service.py` | `list_rumors`, `generate_rumors(sid, rid, *, degrees=None)`, `regenerate_region`, `adjust_support`, `append_for_region(session, rid, *, min_source_support)` |
| `RumorGenerator` | `locus/session/rumor_generator.py` | `generate_chain(*, source_text, source_id, source_kind, source_confidence, region_id, session_id, degrees, birth_support) -> list[SessionRumor]` |
| `EventService` | `locus/session/event_service.py` | `list_events`, `create_event`, `resolve_event`, `discard_event`, `suggest_events(sid, *, n)`, `approve_event` |
| `EventSuggester` | `locus/session/event_suggester.py` | `suggest(*, world_id, region_ids, turn, context="", n=1) -> list[EventDraft]` |
| `DistortionService` | `locus/session/distortion_service.py` | `list_distortions`, `set_region_distortion` |
| `TurnAdvancer` | `locus/session/turn.py` | `advance_turn(sid, *, promotion_threshold=0.6) -> TurnResult` |
| `RumorFeedbackService` | `locus/session/rumor_feedback_service.py` | `apply_feedback(session, active_rumors) -> dict[region, delta]` |
| 순수 함수 | `dynamics.py`, `rumor_dynamics.py`, `promotion.py`, `turn_changes.py` | 이벤트 델타·전파·복원, 지지도 감쇠·가지치기·피드백, 승격 판정, 지역별 변동 정리 |
| `SessionQueryEngine` | `locus/session/query.py` | `knowledge_for_region(sid, rid) -> QueryResult` |
| `TranslationService` | `locus/translation/service.py` | `enrich(items, *, kind, fields, id_attr, world_id, session_id, lang)` — 캐시만 읽고, 없는 것은 백그라운드 번역 |
| `Translator` | `locus/translation/translator.py` | `try_translate(text, target_lang="ko") -> str | None` |

## Data Models

### 캐노니컬 노드 (`locus/models/graph.py`) — Neo4j

기본 클래스 `LocusModel`은 `extra="forbid"`, `use_enum_values=True`이고, `new_id()`는 uuid4를 반환한다.

| Model | Fields | Neo4j |
|---|---|---|
| `Region` | id, world_id, name, level(continent/province/town/district/terrain), parent_id?, description?, attributes(dict), position(Coord)?, provenance | `:Region`, attributes/position은 JSON 문자열 |
| `Entity` | id, world_id, name, entity_type(place/person/event/object/custom/terrain), description?, confidence, located_in?, provenance | `:Entity` |
| `Relation` | id, world_id, source_id, target_id, relation_type, confidence, provenance | `RELATED_TO` 엣지 (id/provenance 유실, **다시 읽지 않음**) |
| `Knowledge` | id, world_id, statement, title, topic?, confidence, is_global, region_hint?, about_entity_ids[], derived_from_prior_ids[], provenance | `:Knowledge` |
| `WikiPrior` | id, world_id, prior_type, condition, effect, domains[], description?, confidence, provenance | `:WikiPrior` |
| `ConnectionEdge` | world_id, source/target_region_id, kind(adjacent/route/river/blocked), weight, rationale?, wiki_prior_ref? | `CONNECTED_TO` (양방향) — **다시 읽음** |
| `ScopeLink` | world_id, knowledge_id, region_id, is_rumor, scope_type, confidence | `SCOPED_TO` — **다시 읽음**, DIRECT만 저장 |
| `WikiPriorLink` | source/target, relation, weight, cross_domain | `PRIOR_RELATED_TO` (쓰기만 함) |
| `Provenance` | source(SourceKind), generated_by?, refs[], note? | `prov_*` 속성 (`refs`는 저장 안 됨) |

쓰기만 하고 읽지 않는 엣지는 `CONTAINS`, `ABOUT`, `DERIVED_FROM`, `LOCATED_IN`, `RELATED_TO`, `PRIOR_RELATED_TO`이다. 로더는 `CONNECTED_TO`와 `SCOPED_TO`만 읽는다.

### 캐노니컬 집계·뷰 (`locus/models/io.py`)

| Model | Fields | 용도 |
|---|---|---|
| `IngestionResult` | entities, relations, region_hints, knowledge, low_confidence_item_ids, errors | 수집 결과 |
| `RegionTopology` | regions, connections | **핵심 산출물 1** |
| `KnowledgeGraph` | entities, relations, knowledge, scopes, unconnected_entity_ids | **핵심 산출물 2의 원재료** |
| `ConsensusView` | direct, inherited, global_knowledge, propagated, rumors, unknown_count | 질의 때마다 계산하는 지역별 지식 (저장 안 함) |
| `KnowledgeView` | knowledge_id, statement, title?(채워지지 않음), scope_type, is_rumor, confidence, distortion_degree?, source?, region_id?, statement_ko?, title_ko? | NPC 응답 항목 |
| `QueryResult` | world_id, region_id, items, shared_ids, unique_ids | **NPC 서빙 계약** |
| `BuildReport` | regions/connections/entities/knowledge/corroborations_created, warnings, ok(항상 True) | 빌드 결과 |

### 세션 모델 (`locus/session/models.py`) — PostgreSQL

| Table | Columns | Model |
|---|---|---|
| `game_sessions` | id PK, world_id(idx), status, turn, created_at, closed_at | `GameSession` |
| `session_rumors` | id PK, session_id, region_id, distorted_from_id, distorted_from_kind, statement, distortion_degree, support, confidence, promoted, active, provenance JSONB | `SessionRumor` |
| `region_distortions` | (session_id, region_id) PK, distortion_degree | `RegionDistortion` |
| `timeline_entries` | id PK, session_id, turn, kind, summary, payload JSONB, created_at | `TimelineEntry` |
| `session_events` | id PK, session_id, region_id, category, description, magnitude, lifecycle, status, created_turn, resolved_turn, contributions JSONB, provenance JSONB | `SessionEvent` |
| `translations` | id PK, source_kind, source_id, source_field, target_lang, text, source_hash, world_id, session_id, created_at; UNIQUE(kind,id,field,lang) | `Translation` |

- 외래 키와 cascade는 없다. Neo4j id는 문자열로만 들고 있어서 저장소 사이의 무결성을 보장하지 않는다.
- 저장하지 않는 모델: `TurnResult`, `RegionTurnChange`, `PromotionResult`, `RumorDraft`, `EventDraft(List)`.
- Enum: `SessionStatus`, `TimelineKind`(11종), `EventCategory`(war/plague/politics/disaster/festival/discovery), `EventLifecycle`(one_shot/persistent), `EventStatus`(suggested/active/resolved).
- 증강 모듈에도 이름이 같은 `SessionStatus`가 따로 있다(`augmentation/types.py:27`).
