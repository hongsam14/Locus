# U9 Orchestration & Authoring — Code Generation Plan

Code 위치 = `locus/services/`, `locus/storage/`, `api/`, `locus/__main__.py`, `examples/demo_world/`. Stories US-9.3 + 빌드/오케스트레이션 경로, end-to-end(SC-1/2/4).

## Steps  (ALL DONE — 93 tests pass, ruff/black clean, CLI+app verified)
- [x] **Step 1 — delete_node + shared persist**: `GraphRepository.delete_node(world_id, node_id)` 포트+Neo4j; `locus/storage/persistence.py` `persist_graph(graph_repo, search_repo, embedding, world_id, *, regions, entities, knowledge, rumors, priors, connections, scopes, relations, warnings)` (graph_mapping 사용). WikiBuilder._persist를 이 헬퍼로 리팩터(테스트 회귀).
- [ ] **Step 2 — PipelineOrchestrator** (`locus/services/orchestrator.py`): build_world(world_id, inputs) — Ingestion→Topology(+wiki)→Ontology→persist_graph → BuildReport. `from_factory`(ProviderFactory+repos) 구성.
- [ ] **Step 3 — GraphEditor** (`locus/services/editor.py`): upsert_region/upsert_knowledge/delete_node (+재색인).
- [ ] **Step 4 — Exporter** (`locus/services/exporter.py`): export_world(world_id) -> dict (WorldLoader 직렬화).
- [ ] **Step 5 — services `__init__.py`**.
- [ ] **Step 6 — demo** (`examples/demo_world/` + `locus/demo.py` `load_demo_world()`).
- [ ] **Step 7 — authoring router** (`api/routers/authoring.py`): build world / build wiki / graph summary / wiki prior upsert / region·knowledge upsert / node delete. 예외→HTTP.
- [ ] **Step 8 — app factory** (`api/main.py` 확장): repos/providers/services DI(주입 가능), serving+authoring 등록.
- [ ] **Step 9 — CLI** (`locus/__main__.py` 확장): build-world/build-wiki/export(+init-schema). 데모 플래그.
- [ ] **Step 10 — Tests** (`tests/services/`, `tests/query/test_authoring_api.py`): persist_graph(mock repos), orchestrator end-to-end(mock 파이프라인/repos → BuildReport counts), editor upsert/delete, exporter 직렬화, authoring API(TestClient, mock services: build 200/ edit/ delete 204/ 404). + WikiBuilder 회귀.
- [ ] **Step 11 — Docs**: `construction/U9-orchestration-authoring/code/code-gen-summary.md`.

## Story Coverage
build_world/오케스트레이션 → Step2 · 편집 → Step3,7 · CLI/export → Step4,9 · US-9.3(앱 통합) → Step8 · 데모 → Step6.

## Notes
- 모든 외부 주입·mock. persist_graph 공유로 U6/U9 DRY. 생성 후 전체 pytest 회귀(API는 TestClient).
