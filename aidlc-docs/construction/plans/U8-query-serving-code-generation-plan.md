# U8 Query & Serving — Code Generation Plan

Code 위치 = `locus/query/` + `api/`. Stories US-8.1~8.3.

## Steps  (ALL DONE — 84 tests pass, ruff/black clean)
- [x] **Step 1 — get_edges**: `GraphRepository.get_edges(world_id, types=None)` 포트 추가 + `Neo4jGraphRepository` 구현(Cypher MATCH 관계 → Edge). 기존 storage 테스트 회귀.
- [ ] **Step 2 — reverse graph_mapping** (`locus/storage/graph_mapping.py` 확장): `node_to_region/entity/knowledge/rumor/wikiprior`(prov_*/json attributes 복원) + `apply_edges`(CONTAINS→parent_id, SCOPED_TO→ScopeLink, CONNECTED_TO→ConnectionEdge, ABOUT/DERIVED_FROM→knowledge 필드). 순수.
- [ ] **Step 3 — WorldLoader** (`locus/query/loader.py`): `load(world_id) -> (KnowledgeGraph, RegionTopology)` (find_nodes + get_edges + 역매핑).
- [ ] **Step 4 — QueryEngine** (`locus/query/engine.py`): 순수 `split_shared_unique(view, include_rumors)`, `diff_sets(items_a, items_b)`; `QueryEngine(loader)` `knowledge_for_region`/`diff_regions` (ConsensusEngine 사용).
- [ ] **Step 5 — `locus/query/__init__.py`**.
- [ ] **Step 6 — API** (`api/main.py` app factory + `api/routers/query.py` serving router + `api/__init__.py`): region knowledge / diff / health 엔드포인트, 예외→HTTP.
- [ ] **Step 7 — Tests** (`tests/query/`): reverse mapping round-trip(graph_mapping 정/역), get_edges(mock driver), WorldLoader(mock repo), split/diff(순수), QueryEngine(mock loader→consensus), API(FastAPI TestClient, mock QueryEngine: 200/404).
- [ ] **Step 8 — Docs**: `construction/U8-query-serving/code/code-gen-summary.md`.

## Story Coverage
US-8.1→Step3,4,6 · US-8.2→Step4,6(diff) · US-8.3→Step4(metadata).

## Notes
- FastAPI TestClient로 API 테스트(오프라인, QueryEngine mock). 역매핑 round-trip 테스트로 정/역 정합 보장. 생성 후 전체 pytest 회귀.
