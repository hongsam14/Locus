# U2 World File·캐노니컬 기반 — Code Generation Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U2 — 플레이와 에디터가 함께 딛는 캐노니컬 기반을 코드로 만든다. NPC가 월드의 일부가 되고, 월드를 World File로 저장·로드하고, 스냅샷 캐시로 플레이가 즉시 읽고, 빌드가 데이터를 조용히 잃지 않게 한다(RE A1·A2·A3·A4·A7·A8·A11·A13). 이 문서가 U2 Code Generation의 단일 진실이다.

> 근거: `construction/U2-worldfile-foundation/functional-design/{domain-entities,business-logic-model,business-rules}.md`(승인 2026-09-29T16:58Z; 리뷰 R-12·R-13은 Accepted risk → 아래 9.3에 조치로 포함), 유닛 정의 `inception/application-design/purpose-restructure/unit-of-work.md` §U2, `component-methods.md` S1·S4·K3·K4·K5·W1·W2·W3·W6·W9·W10·A4·A5, `services.md` §3.1·3.2. NFR·Infra 단계는 U2에서 SKIP(실행 계획).

---

## 유닛 컨텍스트

- **스토리**: US-2.7(빌드를 믿을 수 있다), US-6.2(World File 저장), US-6.3(World File 불러오기) — 주. 백엔드 부분: US-1.3(데모 로드 메커니즘, LLM 0회), US-2.1(이미지 전송·리포트·교체 빌드), US-2.3(미해석 지식 노출), US-2.4(NPC 모델·저장), US-2.6(관계 재독), US-6.4(`list_world_ids`·월드 목록), US-5.2(`region_briefs`).
- **의존**: U1(경계·컨테이너·접두어). 뒤 유닛이 기대는 것: `WorldSnapshot`·`WorldCache.get/invalidate`(U3~U7 읽기 전용), World File v1 스키마(U3 저장 UI, U8 데모 콘텐츠), `region_briefs`(U7), NPC 모델(U3 편집, U5 대화).
- **인터페이스(결과)**: `WorldLoader.load(world_id) -> WorldSnapshot`, `WorldCache.get/invalidate/clear`, `SnapshotSource` Protocol(`get`), `QueryEngine(cache, params)` + `region_briefs`, `WorldBuilder.build(world_id, inputs, *, replace) -> BuildReport`, `WorldFile.parse`, `WorldFileExporter.export -> WorldFile`, `WorldFileImporter.import_(..., replace, force_remap) -> ImportReport`, `DemoWorlds.list/load/build_from_sources`, `GraphRepository.list_world_ids`, API `/api/world/worlds`·`/worlds/{w}/file`·`/worlds/{w}/build[/upload]`·`/demos`·`/worlds/{w}/demo/{name}`, `/api/knowledge/worlds/{w}/briefs`, CLI `locus world build|export|import|demo|list`.
- **DB 엔티티**: Neo4j 라벨 `NPC`(+`LIVES_IN`), `WorldMeta` 신설(유일 제약 `id`; `init-schema --world`가 만든다, 추가만). OpenSearch 문서 `label=NPC` 추가(매핑은 keyword라 변경 없음). PostgreSQL 없음.
- **바뀌는 외부 계약**: `GET /worlds/{w}/export`는 옛 최상위 키(`world_id, regions, connections, entities, knowledge, scopes`)를 **전부 유지**하고 절(`format_version, world, relations, priors, prior_links, npcs, exported_at`)이 더해진다(`web` `WorldExport.world_id`가 계속 맞는다). `GET /worlds/{w}/file`은 World File v1 그대로(`world.id`, 최상위 `world_id` 없음). `POST /worlds/{w}/build`의 `map_images`·`concept_arts`가 base64 문자열 목록이 된다(옛 `list[bytes]`는 JSON으로 보낼 수 없었으므로 실제 사용자 없음). `BuildReport.ok`가 계산값이 된다. `build_world()`는 `build(..., replace=)`로 바뀐다(호출부: `api/routers/world.py:20-31`, `locus/__main__.py:65-70`, `tests/api/test_world_api.py:20`, `tests/world/services/test_services.py:133,224,225,246,264`). `IngestionResult.errors: list[str]` → `warnings: list[BuildWarning]`(호출부: 수집기 4개 + `tests/world/ingestion/test_ingestion.py:110,126,167,176,256,257,278`). `TopologyBuilder.build`·`OntologyBuilder.build`가 경고를 함께 돌려준다(아래 7.2). `WorldContainer.demo`가 `Callable`에서 `DemoWorlds`로, `load_demo_world`는 `DemoWorlds.build_from_sources`의 내부 함수로 남고 `locus/world/__init__.py`·`locus/__main__.py`의 재노출·호출을 바꾼다. `assemble_world`는 LLM 없이도 파일·데모·목록 서비스를 조립한다(R-14). 저장 데이터: 기존 월드는 그대로 읽힌다(WorldMeta 없음 → `name=id`).
- **바꾸지 않는 것**: 합의 계산 규칙과 값, 소문·사건·턴 규칙, 프롬프트, 번역, 프론트 화면(U3). 플레이 서비스는 읽기 소스만 캐시로 바뀐다(동작 동일).

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. `_new`·`_v2` 복사본을 만들지 않는다.
- 각 단계는 **그 단계의 테스트가 GREEN인 상태로** 끝낸다(U1처럼 깨진 채로 넘어가지 않는다). 예외: 4~5단계(로더 반환형 변경)는 4단계 끝에 knowledge 테스트, 5단계 끝에 전체 GREEN.
- 설계의 규칙 번호(BR-U2-n)와 검증 번호(TP-U2-n, EX-n)를 테스트 이름이나 docstring에 적어 추적한다.
- 새 외부 의존은 `python-multipart` 하나(FastAPI multipart 업로드). 그 밖의 라이브러리 추가 없음.
- 각 단계 완료 즉시 체크박스를 [x]로 바꾼다.

---

## Steps

### Step 1 — 베이스라인과 뼈대
- [x] 1.1 `pytest -q --no-cov` / `cd web && npm test` / `mypy locus api` 실측(기대 306 / 30 / 14)을 `construction/U2-worldfile-foundation/code/code-summary.md` 초안에 기준선으로 기록. 16.1이 이 수를 쓴다.
- [x] 1.2 새 모듈 자리: `locus/knowledge/cache.py`, `locus/world/topology/naming.py`, `locus/world/worldfile/{schema,remap,import_}.py`, `locus/world/demo/worlds/`(+`manifest.json`), `locus/shared/llm/counting.py`, `tests/world/strategies.py`(PBT-07 생성기), `tests/shared/storage/fakes.py`(인메모리 `GraphRepository`·`SearchRepository`: upsert/find/get_node/get_edges/delete_node/delete_world/list_world_ids, index/delete_world/hybrid_search 최소; 이후 유닛이 재사용).
- [x] 1.3 `pyproject.toml`: `dependencies += "python-multipart>=0.0.9"`; `[tool.setuptools.package-data] locus = ["world/demo/worlds/*.json"]`. `pip install -e ".[dev]"`로 확인.

### Step 2 — shared 모델·리포트 (S1; domain-entities §1~2)
- [x] 2.1 `shared/models/graph.py`: `WorldMeta`(id, name, description, format_version=1, updated_at, last_writer), `NPC`(id, world_id, name, role, description, home_region_id, traits=[], provenance). `shared/models/io.py`(`KnowledgeGraph`·`RegionTopology`가 여기 있으므로 순환 import 없음): `KnowledgeGraph += priors, prior_links, unscoped_knowledge_ids: list[str]`(온톨로지가 채움, R-01), `WorldSnapshot`(world_id, meta, kg, topo, npcs, load_warnings + `model_validator`로 `regions_by_id`·`regions_by_name`·`npcs_by_region`; `unscoped_knowledge_ids`는 `kg`에서 파생), `RegionBrief`. `SearchDoc.label` 주석에 `NPC`.
- [x] 2.2 `shared/models/reports.py`: `BuildWarning.severity: Literal["warning","error"]="warning"`; `BuildReport += unscoped_knowledge_ids, llm_calls, embedding_calls, replaced`; `ok`를 계산 필드(`computed_field`)로 = error 없음; `errors` property; `ImportReport`(world_id, format_version, source_world_id, remapped, forced, replaced, backup_path, closed_session_ids, counts, warnings, ok 계산). `__init__` 재노출.
- [x] 2.3 `shared/models/util.py`: `index_by_name(regions) -> dict[str, list[Region]]`. `shared/config/settings.py`: `data_dir: Path`(`LOCUS_DATA_DIR`, 기본 `data`) + `backup_dir` property(`data_dir/"backups"`); `env.example`에 한 줄.
- [x] 2.4 테스트: `tests/shared/models/test_models.py`에 NPC·WorldMeta·WorldSnapshot(색인 계산) 왕복(hypothesis 생성기 확장), `BuildReport.ok`가 severity로 정해짐(EX-14의 모델 부분).
### Step 3 — shared 저장 (S4; domain-entities §4)
- [x] 3.1 `shared/storage/graph_mapping.py`: `worldmeta_to_node/node_to_worldmeta`, `npc_to_node/node_to_npc`, `lives_in_edges(npcs)`, `edge_to_relation(edge)`, `npc_doc(npc)`(label="NPC"). `node_to_*`의 실패는 호출자(로더)가 잡는다(BR-U2-16).
- [x] 3.2 `shared/storage/base.py`: `GraphRepository.list_world_ids() -> list[str]`; **`ConstraintViolation(RuntimeError)`** 포트 예외(유일 제약 위반; 어댑터가 드라이버 예외를 이것으로 바꾼다 — world 경계는 neo4j 드라이버를 import하지 않는다, R-04). `neo4j_repo.py`: `list_world_ids`(`MATCH (n) WHERE n.world_id IS NOT NULL RETURN DISTINCT n.world_id ORDER BY 1`), `upsert_nodes`가 `neo4j.exceptions.ConstraintError`를 `ConstraintViolation`으로 감쌈, `NODE_LABELS += ("NPC", "WorldMeta")`. `shared/storage/persistence.py` `persist_graph(..., npcs=None, meta=None)`: NPC 노드·`LIVES_IN`·`npc_doc`, WorldMeta 노드; **저장 실패는 `severity="error"`**(persist-graph/persist-search), `ConstraintViolation`은 error `id collision with another world; retry with remap=true`; 임베딩 실패는 warning(BR-U2-13).
- [x] 3.3 테스트 가짜: `tests/shared/storage/fakes.py`의 `InMemoryGraphRepository`는 `id`가 다른 `world_id`에 이미 있으면 `ConstraintViolation`을 던진다(유일 제약 흉내, EX-4). 기존 그래프 가짜 9개 클래스를 갱신(`list_world_ids`·`get_edges` 기본 구현 또는 `fakes` 상속): `tests/api/play_fixtures.py::GraphRepo`, `tests/api/test_world_api.py::_GraphRepo`, `tests/knowledge/test_query.py::_FakeGraphRepo`, `tests/play/helpers.py::_NullGraph`, `tests/play/test_service.py::FakeGraph`, `tests/world/services/test_services.py::_GraphRepo`, `tests/world/wiki/test_wiki_build.py::_GraphWithPriors`·`_RecordingGraphRepo`, `tests/world/augmentation/test_augmentation.py::_GraphRepo`. `tests/shared/storage/test_storage.py`: 매핑 왕복(NPC·WorldMeta·relation), `persist_graph(npcs=, meta=)`가 노드·엣지·문서를 만든다, persist 실패가 error 경고가 된다, `delete_world` Cypher가 라벨 필터 없이 `world_id`만으로 지운다(EX-22의 저장소 부분; 라이브 확인은 16.2).
### Step 4 — knowledge: 로더·캐시·질의 (K3·K4·K5; BLM §1~3)
- [x] 4.1 `knowledge/loader.py` `load(world_id) -> WorldSnapshot`: 노드 6종·엣지 4종 재독, `LIVES_IN`로 `home_region_id` 보강, 매핑 실패는 건너뛰고 `load_warnings`(BR-U2-16), `unscoped_knowledge_ids` 계산, 노드 0개·meta 없음이면 `LookupError`.
- [x] 4.2 `knowledge/cache.py`: `SnapshotSource` Protocol(`get(world_id) -> WorldSnapshot`), `WorldCache(loader)` — 세대 번호·RLock·락 밖 로드(BLM §2, BR-U2-17), `clear()`.
- [x] 4.3 `knowledge/consensus.py`: `compute_consensus(region_id, *, snapshot, params) -> ConsensusView`(기존 `ConsensusEngine`은 내부 유지, `kg.knowledge`의 `title`로 `KnowledgeView.title` 채움 — BR-U2-19). `knowledge/query.py` `QueryEngine(cache: SnapshotSource, params)`: `knowledge_for_region`·`diff_regions`는 `cache.get`, `region_briefs(world_id, *, top_k=3)`(BR-U2-20). `knowledge/wiring.py` `KnowledgeContainer(loader, cache, query, params)`; `assemble_knowledge`가 `WorldCache(loader)`를 만든다.
- [x] 4.4 테스트: `tests/knowledge/test_loader.py`(fakes 위: NPC·관계·meta 재독, 깨진 노드 하나 건너뜀 EX-17, 빈 월드 LookupError), `test_cache.py`(EX-18 무효화 뒤 재로드, EX-19 로드 중 무효화 → 캐시 안 됨, `get`이 다른 월드 로드를 막지 않음), `test_query.py`에 EX-20(title)·EX-21(briefs) 추가; 기존 query/consensus 테스트는 스냅샷 기반으로 갱신. 이 단계 끝에 `pytest tests/knowledge tests/shared` GREEN.

### Step 5 — 호출부 이행: 튜플 → 스냅샷, 로더 → 캐시 (NFR-3)
- [x] 5.1 play: `base.require_region(snapshots, world_id, region_id)`, `region_knowledge.SessionKnowledgeService`, `rumor/service.RumorService`, `turn/advancer.TurnAdvancer`, `event/service.EventService`의 `loader: WorldLoader` → `snapshots: SnapshotSource`; 본문의 `kg, topo = loader.load(w)` → `snap = snapshots.get(w)`(`snap.kg`, `snap.topo`). `play/wiring.assemble_play`가 `knowledge.cache`를 넘긴다. play 경계는 `locus.knowledge.cache`만 import(행렬 준수).
- [x] 5.2 world: `augmentation/engine.py`가 `snapshots.get`; `worldfile/export.py`는 9단계에서 재작성하므로 여기서는 `snap` 접근만. `world/wiring`·`__main__`의 `WorldLoader` 직접 사용을 `KnowledgeContainer.cache`로.
- [x] 5.3 테스트 가짜: `tests/play/**`·`tests/api/play_fixtures.py`·`tests/world/augmentation`·`tests/knowledge`의 `Loader.load` 가짜에 `get(world_id) -> WorldSnapshot` 제공(공용 헬퍼 `tests/shared/snapshots.py::snapshot_of(kg, topo, npcs=[])`). 이 단계 끝에 **전체 pytest GREEN**(기대 = 306 + 2~4단계 신규).

### Step 6 — 수집 결함 수정 (W1; BR-U2-6/7/10, A7)
- [x] 6.1 `world/ingestion/service.py`: `WorldInputs.map_images: list[str]`·`concept_arts: list[str]`(base64) + `name/description: str|None`(WorldMeta용); `ingest_all`이 `base64.b64decode(validate=True)`로 풀고 실패는 `BuildWarning(stage="ingestion", severity="error")`(BR-U2-10). `IngestionResult.errors: list[str]` → `warnings: list[BuildWarning]` + `entity_id_map`. 경고를 만드는 호출부 4곳(`text_ingestor.py`, `map_image_ingestor.py`, `structured_map_ingestor.py`, `concept_art_ingestor.py`)과 `merge_results`(`service.py:27-44`)를 바꾼다.
- [x] 6.2 `world/ingestion/mapping.py`: `merge_regions` 속성 병합(리스트 합집합·스칼라 첫 값 + 충돌 경고 반환 `-> tuple[list[Region], list[BuildWarning]]`; BR-U2-6), `merge_entities -> tuple[list[Entity], EntityIdMap]`. 호출부 전부 갱신: `text_ingestor.py:39-40`, `concept_art_ingestor.py:41`, `map_image_ingestor.py:90`, `service.py:29-30`. `merge_results`가 관계·`about_entity_ids`·`located_in`을 `id_map`으로 재작성하고 끊긴 관계는 제거 + 경고(BR-U2-7). **설계 이탈 기록**: 설계(BR-U2-6)는 연결 후보 키를 `connections`라 적었으나 코드의 실제 키는 `attributes["connection_hints"]`(구조화 지도 수집기가 붙이고 토폴로지 빌더가 읽음)이다 — 키 이름은 그대로 두고 code-summary에 이탈로 적는다(R-12).
- [x] 6.3 테스트: `tests/world/strategies.py`에 `region_hints()`·`entities_with_refs()` 생성기; `tests/world/ingestion/test_merge.py` TP-U2-3·TP-U2-4(hypothesis) + EX-6·EX-7·EX-9; `tests/world/ingestion/test_ingestion.py`의 `.errors` 단언 7곳(110, 126, 167, 176, 256, 257, 278)과 `merge_entities` 호출부를 갱신. `locus/world/demo/__init__.py`의 `map_images: list[bytes]`를 base64 문자열로(6.1과 함께; `tests/world/test_demo.py:14-18` 갱신은 10.3).
### Step 7 — 이름 해석·경고 경로·미해석 지식 (W2·W3; BR-U2-8/9/14, RE A11·A4·A13)
- [x] 7.1 `world/topology/naming.py`: `LEVEL_RANK`(continent 0, province 1, town 2, district 3; terrain 제외), `resolve_region(name, by_name, *, role, child_level=None, level=None) -> tuple[Region|None, BuildWarning|None]`(BLM §4.1 그대로, 단일 후보 부모 순위 검사 포함).
- [x] 7.2 경고가 빌더까지 닿는 경로(R-01): `world/topology/builder.py` `TopologyBuilder.build(ingestion, *, world_id) -> TopologyBuild`(`@dataclass TopologyBuild(topology: RegionTopology, warnings: list[BuildWarning])`); `assign_hierarchy`(문자열 경고 → `BuildWarning`)·`collect_connection_candidates`의 경고를 모아 싣는다. `world/ontology/builder.py` `OntologyBuilder.build(...) -> OntologyBuild(kg, warnings)`; `scope_knowledge`가 `resolve_region`을 쓰고 미해석 id를 `kg.unscoped_knowledge_ids`에 싣는다(지식은 저장). dedup 뒤 `remap_scopes`와 같은 `remap`으로 `unscoped_knowledge_ids`도 정본 id로 바꾼다(고아 id 없음). `world/build.py`의 `TopologyBuilderLike`·`OntologyBuilderLike` Protocol을 새 반환형으로. 호출부: `build.py`, `tests/world/topology/test_topology.py`, `tests/world/ontology/test_ontology.py`, `tests/world/services/test_services.py`(가짜 빌더가 `.build`로 모델을 돌려주는 곳을 `TopologyBuild`/`OntologyBuild`로).
- [x] 7.3 테스트: `tests/world/topology/test_naming.py` TP-U2-5(hypothesis, `same_name_regions()` 생성기) + EX-8(`test_level_rank_covers_every_hierarchy_level`: `set(RegionLevel) - {TERRAIN} == set(LEVEL_RANK)`); topology/ontology 테스트에 "경고가 결과에 실린다"·"미해석 id가 kg에 실리고 dedup 뒤에도 정본 id다"를 추가.
### Step 8 — 빌드 (W6; BR-U2-11/13/15, RE A3·A13, NFR-5)
- [x] 8.1 `shared/llm/counting.py` `LLMCallCounter`: `wrap_llm(llm)`, `wrap_vlm(vlm)`, `wrap_embedding(emb)`가 같은 카운터를 공유하는 래퍼를 돌려준다(`complete/structured/analyze_image` → `llm_calls`, `embed` → `embedding_calls`).
- [x] 8.2 빌드별 주입(R-02): `WorldBuilder.__init__(graph, search, cache, *, providers: BuildProviders(llm, vlm, embedding), ingestion_factory: Callable[[LLMProvider, VLMProvider], IngestionService], topology_factory: Callable[[CommonsenseWiki|None], TopologyBuilderLike], ontology_factory: Callable[[LLMProvider, EmbeddingProvider|None, CommonsenseWiki|None], OntologyBuilderLike], wiki_factory: Callable[[str, LLMProvider, EmbeddingProvider|None], CommonsenseWiki] | None, distiller_factory, linker_factory, exporter: WorldFileExporter | None, backup_dir: Path)`. `build()`는 매번 `counter = LLMCallCounter()`로 감싼 제공자를 만들어 **모든 팩토리에 넘긴다**(수집·위키·증류·연결·온톨로지·임베딩 전부). `from_factory(factory, graph, search, *, cache, exporter, backup_dir)`가 팩토리들을 만든다. 순서: 준비 단계(수집·토폴로지·prior 증류·연결) → 커밋 단계(백업 export → `delete_world` → priors 저장 → 온톨로지 → 저장 → WorldMeta) → `finally: cache.invalidate`. `WorldExistsError`; 존재 판정 `world_id in graph.list_world_ids()`; 리포트에 severity 경고(3.2의 error 규칙)·`unscoped_knowledge_ids`(7.2의 kg)·`llm_calls`·`embedding_calls`·`replaced`. 옛 `build_world` 제거(호출부는 '외부 계약'에 나열).
- [x] 8.3 테스트 `tests/world/services/test_build.py`(fakes + 가짜 수집기/제공자): EX-10(준비 단계 실패 → 옛 월드 그대로·`replaced=False`), EX-11(`InMemoryGraphRepository`를 persist에서 예외로 만들어 → `ok=False, replaced=True`, 백업 파일 존재(tmp_path), 캐시 세대 증가), EX-12(`replace=False` + 존재 → `WorldExistsError`), EX-14(세 error 경로·warning만이면 ok), EX-15(미해석 지식 저장 + 리포트·스냅샷), EX-16(가짜 제공자를 팩토리에 넘겨 `llm_calls`·`embedding_calls`가 실제 호출 수와 같다). `tests/world/services/test_services.py`의 `build_world` 호출 5곳(133, 224, 225, 246, 264)과 `WorldBuilder` 생성자 사용을 새 시그니처로.
### Step 9 — World File (W9; BR-U2-1~5, TP-U2-1/2/6)
- [x] 9.1 `world/worldfile/schema.py`: `WorldFileMeta`, `WorldFile`(`extra="ignore"`, 절 9개, `exported_at`), `NAMESPACE_LOCUS`(BLM §7.1의 고정 UUID), `UnsupportedWorldFile(ValueError)`, `WorldFile.parse(raw)`: v0 = 최상위 `world_id`에서 `world.id`(없으면 거절), 버전 ≠ 1 거절; **항목 모델은 `LocusModel(extra="forbid")`이므로 `parse`가 절마다 항목 dict를 `model_fields`로 걸러 알 수 없는 키를 버린 뒤 검증한다**(BR-U2-2의 "알 수 없는 필드 무시"를 항목 수준까지); pydantic `ValidationError`는 `UnsupportedWorldFile(str(err))`로 감싼다(라우터 422, R-09).
- [x] 9.2 `world/worldfile/export.py` `WorldFileExporter(cache).export(world_id) -> WorldFile`(정렬 키 표 BLM §6), `to_json_bytes(file)`(`sort_keys=True, indent=2, ensure_ascii=False`), `export_world(world_id) -> dict` 호환 래퍼 = `export().model_dump(mode="json")` + 최상위 `world_id`(R-08). 호출부: `api/routers/world.py:50-53`, `locus/__main__.py:77-85`, `tests/world/services/test_services.py:303`.
- [x] 9.3 `world/worldfile/remap.py` `remap_ids(file, target_world_id) -> WorldFile`: **항등 단락 없음**(FD R-12 조치 — 호출부 `import_`가 `remapped = force_remap or source != target`으로만 판정), **파일 안에 존재하는 id만** 재매핑하고 `provenance.refs`의 외부 id는 그대로(FD R-13 조치), 모든 `world_id`·`world.id`를 대상으로. `validate_references(file) -> tuple[WorldFile, list[BuildWarning]]`(BR-U2-5).
- [x] 9.4 `world/worldfile/import_.py` `WorldFileImporter(graph, search, embedding, cache, exporter, backup_dir).import_(world_id, file, *, replace=True, force_remap=False) -> ImportReport`(BLM §7: 백업 → 삭제 → `persist_graph` 전 절 → WorldMeta → `finally` invalidate; `ConstraintViolation`은 3.2의 error 경고로 리포트).
- [x] 9.5 테스트 `tests/world/worldfile/`: `strategies.world_files()`(참조 일관 생성기, PBT-07) 위에 TP-U2-1(fakes가 반환 순서를 섞어도 export 바이트 동일; `exported_at` 제외), **TP-U2-2를 다음으로 확정**(R-05; 설계 문구의 "재적용 항등"은 `remap_ids` 함수가 아니라 import 분기의 성질이므로 code-summary에 이탈로 적는다): (a) `remap_ids`는 결정적(같은 입력 → 같은 출력), (b) 결과의 `world.id == T`이고 모든 참조가 해석된다, (c) `import_(T, remap_ids(f, T))`(비강제)는 `remapped=False`로 id를 보존한다 — 즉 "한 번 재매핑 뒤 안정"은 임포터 수준에서 성립; TP-U2-6(v0 dict: 대상 B → `remapped=True`·id 전부 변경, 대상 A → 보존·절별 개수 동일); EX-1(버전 2·`world_id` 없는 dict → `UnsupportedWorldFile`), EX-2(모르는 필드(최상위·항목) 무시·필수 필드 누락 거절), EX-3(`world.id == T` + `force_remap=True` → 모든 id 변경, `forced=True`), EX-4(`InMemoryGraphRepository`의 제약 흉내 → error·`ok=False`), EX-5(끊긴 스코프·NPC 제거 + error), EX-13(없는 `home_region_id`), EX-23(import 뒤 WorldMeta `updated_at`·`last_writer="import"`).
### Step 10 — 데모 World File (W10; BR-U2-28/29, US-1.3 메커니즘)
- [x] 10.1 `locus/world/demo/worlds/aldermoor.world.json`(v1, 손으로 작성: 지역 5(Aldermoor·Greenvale·Frostreach·Riverton·Highcrag, 계층·위치), 연결 1(Riverton–Highcrag blocked), 엔티티 3~4(Mayor Tomas, Aldwen River, Spine Mountains, Sunday Market), 관계 1~2, 지식 8~10(`sun rises in the east` global 포함, 메모 `examples/demo_world/memo.txt`의 사실을 그대로), 스코프, prior 0~2, NPC 지역당 1~2명(town 2곳 × 2, province·continent 1)) + `manifest.json`(`[{name:"aldermoor", title, description, file}]`). id는 읽기 쉬운 고정 문자열(예 `region-riverton`)로 두어 diff가 읽힌다.
- [x] 10.2 `world/demo/__init__.py` `DemoWorlds(importer, builder|None)`: `list() -> list[DemoInfo]`, `load(name, world_id, *, replace=True) -> ImportReport`(`WorldFile.parse` → `import_`), `build_from_sources(name, world_id, *, replace=True) -> BuildReport`(옛 메모+지도 경로, `examples/demo_world` 원자료, 개발용). `DemoInfo` 모델은 `world/demo`에.
- [x] 10.3 테스트 `tests/world/test_demo.py` 재작성: EX-26(fakes + 카운팅 제공자: `llm_calls == 0`, 지역 5·연결 1·NPC ≥ 5, `embedding=None`이어도 성공, 두 번 로드해도 노드 수 동일), 매니페스트의 파일이 전부 존재·`parse` 통과, 원자료 경로 테스트는 `build_from_sources`용으로 유지.

### Step 11 — world 조립·캐시 무효화 호출점 (W7 일부·W11; BR-U2-17)
- [x] 11.1 `world/wiring.py` `WorldContainer(cache, editor, exporter, importer, demo: DemoWorlds, builder: WorldBuilder | None, augmentation: AugmentationService | None, wiki_admin: WikiAdmin | None, cross_world: CrossWorldWikiExplorer | None)`. `assemble_world(shared, knowledge)`: graph·search만 있으면 **LLM 없이도** cache·editor·exporter·importer·demo를 조립하고(NFR-4: API 키 없이 파일·데모·목록·export 동작, R-14), `shared.llm`/`factory`가 있을 때만 builder·augmentation·wiki_admin·cross_world를 채운다. `Callable demo` 제거; `locus/world/__init__.py` 재노출을 `DemoWorlds`로.
- [x] 11.2 무효화 호출점을 코드가 캐노니컬을 쓰는 모든 곳에 둔다(R-03; 설계 BR-U2-17의 목록을 보완 — code-summary에 적는다): `world/editor.py`(`upsert_region`·`upsert_knowledge`·`delete_node`; 생성자에 `cache`; 끝에 `cache.invalidate(world_id)` + WorldMeta `touch(last_writer="edit")`, 메타가 없으면 만들지 않음), `world/augmentation/apply.py`(ADD 경로와 `revert`의 직접 `graph_repo` 쓰기 뒤 — `AugmentationEngine`이 `cache`를 받아 `apply`/`revert` 끝에 무효화), `world/wiki/admin.py::WikiAdmin.upsert_prior`(생성자에 `cache`, 쓰기 뒤 무효화). NPC 편집 메서드는 U3.
- [x] 11.3 테스트: `tests/world/services/test_services.py`에 에디터 쓰기 뒤 캐시 세대가 오른다 + **EX-23 편집 부분**(가짜 그래프에 WorldMeta 노드가 있을 때 `updated_at`·`last_writer="edit"` 갱신, 없으면 만들지 않음); `tests/world/augmentation/test_augmentation.py`에 apply/revert 뒤 무효화; `tests/world/wiki/test_wiki_build.py`(또는 admin 테스트)에 prior upsert 뒤 무효화; `tests/api/test_augment_api.py:30`·`tests/api/test_world_api.py:46`의 `WorldContainer(...)` 생성을 새 필드로; `tests/api/test_knowledge_api.py:41`의 `KnowledgeContainer(...)`에 `cache=`(4.3 이후 5.3에서 함께).
### Step 12 — API (A4·A5; BR-U2-25, EX-24)
- [x] 12.1 `api/errors.py`: `WorldExistsError → 409`, `UnsupportedWorldFile → 422`(`http_error`의 `ValueError→400`보다 **먼저** 검사한다, R-09). `api/deps.py`: `get_play_optional()`(play 없으면 None). `api/schemas.py`: `WorldInfo(id, name, description, region_count, updated_at, open_sessions)`, `DemoInfo` 재노출, `BuildRequest`(WorldInputs + `name/description`).
- [x] 12.2 `api/routers/world.py`: `POST /worlds/{w}/build?replace=true&confirm=false`(JSON base64; `w.builder is None`이면 503 "world build needs an LLM provider"), `POST /worlds/{w}/build/upload`(multipart `memos[]`·`maps[]`·`images[]`·`name`·`description`), `GET /worlds/{w}/file`(`Content-Disposition`), `POST /worlds/{w}/file?replace=&confirm=&remap=`(JSON 본문 또는 multipart 파일 → `WorldFile.parse`), `GET /worlds`, `GET /demos`, `POST /worlds/{w}/demo/{name}?confirm=`, `POST /worlds/{w}/demo/{name}/build`(옛 원자료 빌드, builder 필요); 헬퍼 `_confirm_replace(world_id, confirm, play) -> list[str]`: `play.sessions.list_sessions(world_id)`에서 **`status == "open"`만** 센다(R-10) → 1개 이상이고 `confirm`이 아니면 409 `{detail, open_sessions}` / confirm이면 `play.sessions.close_session(id)` 각각, 닫은 id 반환 → 리포트 `closed_session_ids`. `GET /worlds/{w}/export` 유지(9.2 호환 dict).
- [x] 12.3 `api/routers/knowledge.py`: `GET /worlds/{w}/briefs?top_k=`.
- [x] 12.4 테스트 `tests/api/test_world_api.py`(fakes 기반 `WorldContainer` 주입): 파일 GET/POST 왕복, v2 파일·비월드 dict 422(400 아님), `remap=true`, 월드 목록, 데모 목록·로드, LLM 없는 컨테이너(builder None)에서 파일·데모·목록은 200이고 build는 503, EX-24(열린 세션 1 + 닫힌 세션 1 → 409 `open_sessions: 1` → confirm → 열린 것만 닫힘), play 없음 → 확인 없이 진행; `tests/api/test_knowledge_api.py` briefs. `web/src/__tests__`는 14.2에서.
### Step 13 — CLI (BR-U2-26, EX-25)
- [x] 13.1 `locus/__main__.py`: `locus world build --world W (--inputs f.json | --demo-sources NAME) [--replace/--no-replace] [--force]`, `locus world export --world W --out f.json`, `locus world import --world W --file f.json [--replace/--no-replace] [--remap] [--force]`, `locus world demo --list | --name aldermoor --world W [--force]`, `locus world list`. `--force` 없이 열린 세션(`list_sessions`에서 `status == "open"`)이 있으면 종료 1 + 안내, `--force`면 `close_session`으로 닫고 진행(play 경계는 SQL이 설정된 경우에만 조립). `ok`가 아니면 종료 1. 옛 `build-world`·`export`는 별칭(한 사이클).
- [x] 13.2 테스트 `tests/test_cli.py`(`assemble_shared` 몽키패치 + fakes): export→import 왕복 파일, 종료 코드(ok=False → 1, `--force` 없는 열린 세션 → 1).

### Step 14 — 프론트 API 함수 (F5 일부; 화면은 U3)
- [x] 14.1 `web/src/types.ts`: `WorldFile`(WorldExport 확장), `ImportReport`, `WorldInfo`, `DemoInfo`, `RegionBrief`, `BuildReport`(+`unscoped_knowledge_ids`, `llm_calls`, `ok`, `warnings[].severity`). `web/src/api/world.ts`: `buildWorld(w, inputs, {replace, confirm})`, `uploadBuild(w, formData, ...)`, `getWorldFile(w)`, `importWorldFile(w, file, {replace, confirm, remap})`, `listWorlds()`, `listDemos()`, `loadDemo(w, name, {confirm})`; `buildWorldDemo`는 새 경로(`/demo/{name}/build`)로. `web/src/api/knowledge.ts`: `regionBriefs(w, topK)`.
- [x] 14.2 `EditorPage`의 `buildDemo`는 `loadDemo(worldId, "aldermoor")`(LLM 0회)로 바꾸고 버튼 문구 "Load demo world"(US-1.3 백엔드 부분의 최소 연결; 확인 409 처리는 U3). `npm test` 30 GREEN 유지(mock 목록에 `loadDemo` 추가), `npm run lint`, `npm run build`.

### Step 15 — 문서·운영
- [x] 15.1 `construction/U2-worldfile-foundation/code/code-summary.md`: 새 파일·변경 파일, 규칙→테스트 매핑(EX/TP 커버 표), 결과, 남긴 TODO.
- [x] 15.2 `aidlc-docs/operations/operations.md`: World File 저장·로드·데모 CLI/API, 백업 위치(`LOCUS_DATA_DIR/backups`)와 복구 절차(`locus world import --file <backup>`), **단일 워커 전제**(캐시), `--workers 1` 명시; `docker-compose.yml`: app 커맨드에 `--workers 1`, **명명 볼륨 `locus_data:/app/data`**와 `LOCUS_DATA_DIR=/app/data`(백업이 컨테이너 재생성에도 남는다, R-11); `env.example` `LOCUS_DATA_DIR`; `CLAUDE.md` CLI 줄; `examples/demo_world/README.md`에 "데모 로드는 패키지 World File, 원자료 빌드는 `--demo-sources`".

### Step 16 — 최종 검증
- [x] 16.1 `pytest -q --no-cov` 전체 GREEN(기대 = 306 + 신규 ≈ 40~50), `tests/test_boundaries.py`, `cd web && npm test`(30), `ruff check locus api tests`, `black --check`, `mypy locus api` ≤ 14, `npm run lint`, `npm run build`. `docker build .` 성공(패키지 데이터 포함: 컨테이너에서 `python -c "from locus.world.demo import DemoWorlds; ..."`로 매니페스트 확인).
- [x] 16.2 라이브 확인은 operator-run(이 호스트의 7474/7687 충돌 — `host-neo4j-port-conflict`): `locus world demo --name aldermoor --world demo` → `locus world export` → `import` 왕복, `GET /api/world/worlds`. 결과를 code-summary에 기록하고 2-옵션 완료 메시지 제시.

---

## 설계 이탈 기록 (승인된 FD 문서는 고치지 않고 code-summary에 함께 적는다)
| 항목 | 설계 | 이 플랜 | 까닭 |
|---|---|---|---|
| 연결 후보 키 | `attributes.connections` | `attributes.connection_hints`(기존 키 유지) | 코드의 실제 키; 이름만의 차이(6.2) |
| TP-U2-2 재적용 항등 | `remap_ids(remap_ids(f,T),T) == remap_ids(f,T)` | 함수는 결정성만; 항등은 `import_` 분기(비강제·`world.id==T`) 수준 | FD R-12 조치(항등 단락 제거)와 양립(9.5) |
| BR-U2-17 무효화 호출점 | 빌드·import·데모·에디터·증강 | + `augmentation/apply.py` 직접 쓰기, `WikiAdmin.upsert_prior` | 코드가 캐노니컬을 쓰는 곳 전부(11.2) |
| 빌더 반환형 | `TopologyBuilder.build -> RegionTopology`, `OntologyBuilder.build -> KnowledgeGraph` | `TopologyBuild(topology, warnings)`, `OntologyBuild(kg, warnings)` + `kg.unscoped_knowledge_ids` | 경고·미해석 id가 리포트까지 닿게(7.2, RE A13) |
| `WorldContainer` | 모든 서비스 필수 | LLM 의존 서비스는 Optional | API 키 없이 파일·데모·목록 동작(NFR-4, 11.1) |

## 스토리 추적
| 스토리 | 단계 |
|---|---|
| US-2.7 빌드를 믿을 수 있다 (A1·A2·A3·A11) | 6, 7, 8 |
| US-6.2 World File 저장 | 9.1~9.2, 12.2, 13.1, 14 |
| US-6.3 World File 불러오기 (왕복 PBT, 확인, 버전) | 9.3~9.5, 12.2, 13.1 |
| US-1.3 (백엔드) 데모 로드 LLM 0회 | 10, 12.2, 14.2 |
| US-2.1 (백엔드) 이미지 전송·리포트·교체 빌드 | 6.1, 8, 12.2 |
| US-2.3 (백엔드) 미해석 지식 노출 | 7.2, 4.1 |
| US-2.4 (백엔드) NPC 모델·저장 | 2.1, 3, 9 |
| US-2.6 (백엔드) 관계 재독 | 4.1 |
| US-6.4 (백엔드) 월드 목록 | 3.2, 12.2, 13.1 |
| US-5.2 (백엔드) `region_briefs` | 4.3, 12.3 |

## 범위 밖(뒤 유닛)
에디터 화면·NPC 편집 UI·저장/불러오기 UI·409 확인 다이얼로그(U3) · 플레이 서비스의 캐시 이상 사용(U4) · NPC 대화(U5) · 데모 TRPG 콘텐츠 확장·README 전면(U8) · 상식 wiki 진행 중 모듈(FR-I).

## PBT Compliance (Partial)
- PBT-02: TP-U2-1(World File 왕복), TP-U2-2(재매핑), TP-U2-6(v0) — hypothesis, `tests/world/strategies.py::world_files()`.
- PBT-03: TP-U2-3(병합 힌트 보존), TP-U2-4(참조 보존), TP-U2-5(해석 결정성) — hypothesis.
- PBT-07: 생성기는 `tests/world/strategies.py`(월드·지역·엔티티·NPC), `tests/shared/snapshots.py`(스냅샷 헬퍼)로 두어 U3·U4·U8이 재사용.
- PBT-08/09: hypothesis 기본 설정(seed 출력) 유지, 라이브러리 유지.
