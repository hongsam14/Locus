# U5 Consensus — Code Generation Plan

Code 위치 = `locus/consensus/`. U1 모델 사용, in-memory. Stories US-4.1~4.3.

## Steps  (ALL DONE — 73 tests pass, ruff/black clean)
- [x] **Step 1 — propagation** (`locus/consensus/propagation.py`): `best_path_weights(start_id, regions, connections) -> dict[region_id,float]` (max-product Dijkstra). 순수.
- [ ] **Step 2 — engine** (`locus/consensus/engine.py`): `ConsensusParams`(PROPAGATE_MIN=0.5, RUMOR_MIN=0.15); 순수 `compute_consensus(region_id, *, regions, connections, scopes, knowledge_by_id, params)`; `ConsensusEngine(knowledge_graph, topology, params)` (precompute 인덱스, `resolve(region_id)`).
- [ ] **Step 3 — `__init__.py`** 재노출.
- [ ] **Step 4 — Tests** (`tests/consensus/`): best_path_weights(도로>산맥, max-product, +PBT ≤1), compute_consensus(direct/inherited/global/propagated/rumor/unknown 분류, distortion=1−pw, 우선순위 중복제거), ConsensusEngine.resolve.
- [ ] **Step 5 — Docs**: `construction/U5-consensus/code/code-gen-summary.md`.

## Story Coverage
US-4.1→Step1,2(분류·전파) · US-4.2→Step2(하이브리드 정적+쿼리) · US-4.3→Step2(감쇠+소문 distortion).

## Notes
- 전부 순수(IO/LLM 무관). 생성 후 전체 pytest 회귀.
