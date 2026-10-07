# U2 World File·캐노니컬 기반 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG.
**이 유닛이 한 것**: 플레이와 에디터가 함께 딛는 캐노니컬 기반 — NPC가 월드의 일부가 되고(`:NPC`+`LIVES_IN`, 검색 색인), 월드를 World File v1로 저장·로드하며(결정적 id 재매핑, 참조 검증, 옛 export 수용), 스냅샷 캐시로 플레이가 즉시 읽고(`WorldCache`, 세대 번호), 빌드가 데이터를 조용히 잃지 않는다(준비/커밋 분리, 백업, 경고 등급, 미해석 지식 노출, 동명이레벨 결정적 해석, 빌드별 LLM 호출 계수). 데모 월드는 패키지 안 World File에서 LLM 0회로 로드된다.

## 베이스라인 (Step 1.1, 2026-09-29T17:15Z) → 결과 (Step 16.1, 2026-09-30)
| 검사 | 베이스라인 | 결과 |
|---|---|---|
| `pytest -q --no-cov` | 306 passed | **373 passed** → 코드 리뷰 수정 뒤 **388** (+67: 모델 4, 저장 8, 로더 4, 캐시 4, 질의 2, 병합 5(PBT 2), 이름 해석 4(PBT 1), 빌드 6, World File 9(PBT 3), 데모 4, 에디터·증강·wiki 무효화 4, API 11, CLI 3, …) |
| `tests/test_boundaries.py` | 4 | 4 passed (world→play 없음, play는 `locus.knowledge.cache`만) |
| `npm test` (vitest) | 30 | 30 → 코드 리뷰 수정 뒤 **31** (데모 교체 확인 다이얼로그) |
| `ruff` / `black --check` | clean | clean |
| `mypy locus api` | 14 errors / 8 files | **12 errors / 7 files** (`edge_to_*`의 `SourceKind` 리터럴 정정으로 −2) |
| `npm run lint` (tsc) / `npm run build` | clean | clean / built |
| `docker build .` | — | OK — 이미지 안 `locus/world/demo/worlds/aldermoor.world.json` 포함(`DemoWorlds(None).list() == ["aldermoor"]`), `import api.main` OK |
| 라이브 Neo4j/PostgreSQL 확인 | — | **operator-run** (아래) |

## 새 파일
- `locus/knowledge/cache.py` (`SnapshotSource`·`SnapshotCache` Protocol, `WorldCache`)
- `locus/shared/models/util.py::index_by_name`, `locus/shared/llm/counting.py` (`LLMCallCounter`)
- `locus/world/topology/naming.py` (`LEVEL_RANK`, `resolve_region`)
- `locus/world/worldfile/{schema,remap,import_}.py`, `worldfile/__init__.py` (재노출)
- `locus/world/demo/worlds/{aldermoor.world.json,manifest.json}` (손으로 옮긴 결정적 데모: 지역 5·연결 1(양방향 2)·엔티티 5·관계 2·지식 10(global 1)·스코프 9·prior 1·NPC 6)
- `tests/shared/storage/fakes.py` (`InMemoryGraphRepository`(유일 제약·순서 섞기 흉내)·`InMemorySearchRepository`), `tests/shared/snapshots.py`, `tests/world/strategies.py` (`region_hints`·`entities_with_refs`·`same_name_regions`·`world_files` — PBT-07)
- `tests/knowledge/{test_loader,test_cache}.py`, `tests/world/ingestion/test_merge.py`, `tests/world/topology/test_naming.py`, `tests/world/services/test_build.py`, `tests/world/worldfile/test_worldfile.py`, `tests/test_cli.py`

## 변경 파일 (핵심)
| 파일 | 변경 |
|---|---|
| `locus/shared/models/{graph,io,reports,__init__}.py` | `WorldMeta`, `NPC`, `WorldSnapshot`(파생 색인·`load_warnings`), `RegionBrief`, `KnowledgeGraph.priors/prior_links/unscoped_knowledge_ids`, `BuildWarning.severity`, `BuildReport`(계산 `ok`, `unscoped_knowledge_ids`, `llm_calls`, `embedding_calls`, `replaced`, `closed_session_ids`), `ImportReport`, `IngestionResult.warnings/entity_id_map`(옛 `errors: list[str]` 대체) |
| `locus/shared/config/settings.py` | `data_dir`(`LOCUS_DATA_DIR`)·`backup_dir` |
| `locus/shared/storage/{base,neo4j_repo,graph_mapping,persistence}.py` | `ConstraintViolation`, `list_world_ids`, `NODE_LABELS += NPC, WorldMeta`, NPC/WorldMeta/관계 매핑(+`prov_refs`, 연결·prior_link의 provenance 왕복), `persist_graph(npcs=, meta=)`, 저장 실패 = error, `touch_world_meta` |
| `locus/knowledge/{loader,consensus,query,wiring,__init__}.py` | 로더 → `WorldSnapshot`(노드 6종·엣지 5종, 깨진 노드 건너뜀, 빈 월드 LookupError), `compute_consensus(snapshot=)` + `title` 채움, `QueryEngine(cache)` + `region_briefs`, `KnowledgeContainer.cache` |
| `locus/play/{base,region_knowledge,rumor/service,turn/advancer,event/service,wiring}.py` | `loader` → `snapshots: SnapshotSource`(캐시를 통해 읽음, NFR-3) |
| `locus/world/ingestion/{service,mapping,text_ingestor,map_image_ingestor,structured_map_ingestor,concept_art_ingestor}.py` | base64 이미지 입력·디코드 실패 error(A7), `merge_regions` 속성 보존 + 충돌 경고(A1), `merge_entities → (entities, id_map)` + `remap_entity_refs`(A2), 경고를 `BuildWarning`으로 |
| `locus/world/topology/{hierarchy,builder}.py`, `locus/world/ontology/builder.py` | `resolve_region` 사용(A11), `TopologyBuild`/`OntologyBuild` 반환(경고 동반, A13), 미해석 지식 id를 kg에 실어 dedup 뒤에도 정본 id(A4) |
| `locus/world/build.py` | `WorldBuilder.build(world_id, inputs, *, replace)`: 준비/커밋 분리, 백업 export, `delete_world`, `finally` 무효화, 빌드별 `LLMCallCounter` 래핑을 팩토리로 주입, `WorldExistsError`, `BuildProviders` |
| `locus/world/worldfile/export.py` | `export() -> WorldFile`(정렬 키 표), `export_world()` 호환 dict(최상위 `world_id` 유지) |
| `locus/world/{editor,wiring,demo/__init__}.py`, `locus/world/augmentation/engine.py`, `locus/world/wiki/admin.py` | 쓰기 뒤 캐시 무효화·`WorldMeta` touch; LLM 없이도 파일·데모·목록 조립(`WorldContainer`의 LLM 의존 서비스 Optional); `DemoWorlds` |
| `api/{deps,errors,schemas}.py`, `api/routers/{world,knowledge}.py` | `get_play_optional`, `UnsupportedWorldFile → 422`(ValueError→400보다 먼저), `WorldInfo`, world 라우터 재작성(build JSON/multipart, `file` GET/POST/upload, `worlds`, `demos`, `demo/{name}`, `demo/{name}/build`, 열린 세션 409/confirm, LLM 의존 라우트 503), `briefs` |
| `locus/__main__.py` | `locus world build|export|import|demo|list`, `--replace/--no-replace`, `--force`, `--remap`, 종료 코드, 별칭 `build-world`·`export` |
| `web/src/{types.ts,api/world.ts,api/knowledge.ts,api/http.ts,routes/EditorPage.tsx,Toolbar.tsx}` | World File·리포트·월드 목록·데모·브리프 타입과 호출 함수; "Load demo world"가 LLM 0회 경로 |
| `pyproject.toml`, `docker-compose.yml`, `env.example`, `aidlc-docs/operations/operations.md`, `CLAUDE.md`, `examples/demo_world/README.md` | `python-multipart`, package-data, `--workers 1`·`locus_data` 볼륨·`LOCUS_DATA_DIR`, 운영 절차, CLI 줄 |

## 설계 이탈 기록 (승인된 FD 문서는 그대로 두었다)
| 항목 | 설계 | 구현 | 까닭 |
|---|---|---|---|
| 연결 후보 키 | `attributes.connections` | `attributes.connection_hints`(기존 키) | 코드의 실제 키; 이름만의 차이 |
| TP-U2-2 재적용 항등 | `remap_ids(remap_ids(f,T),T) == remap_ids(f,T)` | `remap_ids`는 결정성·`world.id==T`·참조 해석만; "한 번 재매핑 뒤 안정"은 임포터 분기(비강제·`world.id==T` → 보존)에서 성립 | FD R-12 조치(항등 단락 제거)와 양립 |
| BR-U2-17 무효화 호출점 | 빌드·import·데모·에디터·증강 | + `augmentation/apply.py` 직접 쓰기(엔진이 apply/revert 뒤 무효화), `WikiAdmin.upsert_prior` | 캐노니컬을 쓰는 곳 전부 |
| 빌더 반환형 | `RegionTopology` / `KnowledgeGraph` | `TopologyBuild(topology, warnings)` / `OntologyBuild(kg, warnings)` + `kg.unscoped_knowledge_ids` | 경고·미해석 id가 리포트까지 닿게(RE A13) |
| `WorldContainer` | 모든 서비스 필수 | LLM 의존 서비스 Optional; 게이트는 `shared.llm is not None`(R-14) | API 키 없이 파일·데모·목록 동작(NFR-4) |
| 관계 id 왕복 | — | `RELATED_TO` 엣지에 `id`·provenance 저장; 그래프는 관계를 (source, target)당 하나로 유지(MERGE) | 왕복 동일성; 같은 두 엔티티 사이 관계는 하나 |
| import의 world_id 통일 | 재매핑 안 할 때 파일 그대로 | 재매핑하지 않을 때도 모든 `world_id`를 대상으로 찍는다(`set_world_id`) | 노드가 대상 파티션에 들어가게(id 충돌 감지도 이 위에서) |

## 규칙 → 테스트 매핑
| 규칙 | 테스트 |
|---|---|
| BR-U2-1/2 (파싱·v0·알 수 없는 키) | `test_worldfile.py::test_legacy_export_is_read_and_remapped_across_worlds`(TP-U2-6), `test_parse_rejects_unsupported_and_non_world_files`(EX-1), `test_parse_ignores_unknown_keys_but_rejects_missing_required`(EX-2); API `test_world_file_import_rejects_unsupported_with_422` |
| BR-U2-3 (정렬·바이트 동일) | `test_export_import_export_is_stable`(TP-U2-1, 저장소 순서 섞기) |
| BR-U2-4 (재매핑·강제·충돌) | `test_remap_is_deterministic_and_stable_at_import_level`(TP-U2-2), `test_forced_remap_changes_every_id_even_for_the_same_world`(EX-3), `test_id_collision_with_another_world_is_reported_and_recoverable`(EX-4), `test_storage.py::test_id_collision_with_another_world_is_reported` |
| BR-U2-5 / 12 (끊긴 참조·NPC home) | `test_broken_references_are_dropped_with_errors`(EX-5/13) |
| BR-U2-6 / 7 (병합) | `test_merge.py`: TP-U2-3, TP-U2-4, EX-6, EX-7 |
| BR-U2-8 / 9 (이름 해석) | `test_naming.py`: TP-U2-5, EX-8, 단일 후보 부모 순위, 모호성 경고; `test_topology_build_carries_hierarchy_and_hint_warnings` |
| BR-U2-10 (base64) | `test_merge.py::test_bad_base64_is_an_error_but_other_inputs_proceed`(EX-9) |
| BR-U2-11 (교체·준비/커밋·백업) | `test_build.py`: EX-10, EX-11, EX-12; `test_worldfile.py::test_import_stamps_world_meta_and_backs_up_on_replace` |
| BR-U2-13 (ok 판정) | `test_build.py::test_ok_follows_error_paths_only`(EX-14), `test_storage.py::test_persist_failures_are_errors_not_warnings`, `test_models.py::test_build_report_ok_follows_severity` |
| BR-U2-14 (미해석 지식) | `test_build.py::test_build_persists_and_reports_unscoped`(EX-15), `test_ontology.py::test_unscoped_ids_are_canonical_after_dedup`, `test_loader.py` |
| BR-U2-15 (호출 계수) | `test_build.py::test_llm_and_embedding_calls_are_counted_per_build`(EX-16); 데모 LLM 0 = `test_demo.py`(임포터에 LLM 없음) |
| BR-U2-16 (깨진 노드) | `test_loader.py::test_loader_skips_a_broken_node_and_reports_it`(EX-17) |
| BR-U2-17 / 18 (캐시) | `test_cache.py`(EX-18, EX-19, 다른 월드 비차단), `test_services.py::test_editor_writes_invalidate_cache_and_touch_meta`, `test_augmentation.py::test_engine_apply_and_revert_invalidate_cache`, `test_wiki_build.py::test_wiki_admin_upsert_invalidates_cache` |
| BR-U2-19 / 20 (title·briefs) | `test_query.py`: EX-20, EX-21; API `test_region_briefs_endpoint` |
| BR-U2-21~24 (NPC·메타·목록) | `test_storage.py`(EX-22 저장소 부분), `test_loader.py`, `test_services.py`(EX-23 편집), API `test_list_worlds_reports_meta_and_open_sessions` |
| BR-U2-25 / 26 (열린 세션) | API `test_replace_with_open_sessions_needs_confirm_and_closes_only_open`(EX-24), `test_replace_without_play_boundary_proceeds`; CLI `test_open_sessions_need_force`(EX-25) |
| BR-U2-27 (경계) | `tests/test_boundaries.py` |
| BR-U2-28 / 29 (데모) | `test_demo.py`(EX-26), CLI `test_demo_export_import_roundtrip_and_list` |
| R-14 (LLM 없는 조립) | API `test_llm_free_container_serves_files_and_demo_but_not_build` |

## 운영자 확인 (operator-run — 이 호스트의 7474/7687은 다른 프로젝트 컨테이너가 사용)
1. `docker compose up -d neo4j opensearch postgres && locus init-schema` (WorldMeta·NPC 제약 추가는 idempotent).
2. `locus world demo --name aldermoor --world demo` → 리포트 `ok=true`, `llm_calls` 없음(import 경로).
3. `locus world export --world demo --out demo.world.json` → `locus world import --world demo2 --file demo.world.json` → `locus world list`에 두 월드.
4. `curl -sf localhost:8000/api/world/worlds`, `GET /api/world/worlds/demo/file`, `GET /api/knowledge/worlds/demo/briefs`.
5. 기존(U1 이전) 월드는 재빌드 없이 읽힌다(`SourceKind` 매핑, `WorldMeta` 없으면 `name=id`).

## 남긴 TODO
- **U3**: NPC 편집 API·UI, 스코프 지정 UI, 저장/불러오기·409 확인 다이얼로그, 월드 목록 화면. **U4**: 플레이 서비스가 캐시를 읽는 것을 전제로 이동·턴. **U7**: `region_briefs`를 사건 제안 프롬프트에. **U8**: TRPG 규모 데모 콘텐츠(World File 확장), README 전면.
- `WorldCache`는 단일 워커 전제(compose `--workers 1`); 다중 워커는 지원하지 않는다고 운영 문서에 적었다.
- `RELATED_TO`는 (source, target)당 하나(MERGE) — 같은 두 엔티티 사이에 여러 관계 종류가 필요하면 엣지 키에 `relation_type`을 넣어야 한다(U3 이후 판단).
- 데모 World File은 `examples/demo_world`의 사실을 옮긴 5지역 판이다; TRPG 규모(지역 10~15, 사건 씨앗)는 U8.
- mypy 잔여 12건은 U1 이전부터 이월된 외부 라이브러리 타입 문제다.

## 코드 리뷰 (승인 뒤, U4 전)
`reviews/code-review-01.md` — `/code-review` 15건 전부 수정 + tail 대부분 수정(기록 항목은 파일에). 회귀 테스트 +16. 이 리뷰로 바뀐 설계 사항: 엣지 identity(관계 `id`, 연결 `kind`), 레벨 없는 지도의 레벨 추론, 캐시의 WorldMeta 버전 확인, LLM 없는 play 조립(세션·왜곡도·지역 뷰), 교체 게이트의 '확인 먼저·닫기는 성공 뒤'.
