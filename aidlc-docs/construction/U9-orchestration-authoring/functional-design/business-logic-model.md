# U9 Orchestration & Authoring — Business Logic Model

## PipelineOrchestrator.build_world(world_id, inputs) -> BuildReport (FD9-Q1=A)
의존 주입: IngestionService, TopologyBuilder, OntologyBuilder, GraphRepository, SearchRepository, EmbeddingProvider, CommonsenseWiki.
흐름:
1. `ingestion = ingestion_service.ingest_all(world_id, inputs)`.
2. `topology = topology_builder.build(ingestion, world_id=world_id)` (TopologyBuilder에 CommonsenseWiki 주입 — 실세계 prior로 가중).
3. `kg = ontology_builder.build(ingestion, topology, world_id=world_id)` (llm/embedding/wiki 주입 — 스코핑/고증/dedup).
4. persist: graph_mapping → nodes/edges → graph_repo.upsert; search docs(knowledge/entity) → embed → search_repo.index. (U6 _persist 패턴 재사용/공유 헬퍼 `persist_world(...)`.)
5. BuildReport(counts + warnings) 반환. **컨센서스 영속 안 함**(쿼리 시점 U5/U8).
- graceful: 각 단계 실패 → warnings, 가능한 부분 진행.

> **컨센서스 실시간**: direct/inherited/global은 저장 스코프에서, 전파/소문은 쿼리마다 U5가 계산(캐시 없음, ND1-Q3=B).

## GraphEditor (Q2=C 편집)
- `upsert_region(region)` / `upsert_knowledge(knowledge)` → graph_repo.upsert_nodes([node]) (+ knowledge면 search 재색인).
- `delete_node(world_id, node_id)` → graph_repo로 DETACH DELETE (port에 `delete_node` 추가) + search 삭제(가능 시).

## Exporter (Q4=A)
- `export_world(world_id) -> dict`: WorldLoader.load → 도메인 모델을 dict로 직렬화(model_dump) → {regions, entities, knowledge, scopes, connections}. CLI가 JSON 파일로 기록.

## Authoring Router (`api/routers/authoring.py`)
- DI: app.state.{orchestrator, wiki_builder, wiki_admin, graph_editor, exporter, graph_repo}.
- 엔드포인트: build world / build wiki / graph summary / wiki prior upsert / region·knowledge upsert / node delete. 예외→HTTP.

## App factory 확장 (`api/main.py`)
- 설정으로 repos/providers 생성·connect, 모든 서비스(orchestrator/wiki/editor/exporter/query) 구성, serving+authoring 라우터 등록, 시작 시 init-schema.

## CLI 확장 (`locus/__main__.py`)
- build-world / build-wiki / export 명령(+기존 init-schema). 데모 플래그.

## Demo (Q5=A)
- `examples/demo_world/`(가상 세계) + `load_demo_world()`.

## 순수/통합
- persist_world(graph/search 호출)는 얇은 통합부 → mock 테스트. Exporter 직렬화·GraphSummary 집계는 순수 가능 부분 분리.
