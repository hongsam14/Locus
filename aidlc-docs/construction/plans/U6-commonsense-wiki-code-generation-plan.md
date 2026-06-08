# U6 Commonsense Wiki (build) — Code Generation Plan

Code 위치 = `locus/commonsense_wiki/` (+ 공유 `locus/storage/graph_mapping.py`, `examples/`). Stories US-1.5, US-5.1~5.3.

## Steps  (ALL DONE — 67 tests pass, ruff/black clean)
- [x] **Step 1 — graph_mapping** (`locus/storage/graph_mapping.py`, 공유·순수): domain → Node/Edge/SearchDoc 변환 (region/entity/knowledge/rumor/wikiprior nodes; CONTAINS/CONNECTED_TO/SCOPED_TO/ABOUT/DERIVED_FROM/RELATED_TO edges; to_search_docs).
- [ ] **Step 2 — WikiBuildReport** (`locus/models/reports.py` 추가): counts + warnings.
- [ ] **Step 3 — schemas** (`locus/commonsense_wiki/schemas.py`): PriorSuggestion, PriorBatch.
- [ ] **Step 4 — PriorDistiller** (`locus/commonsense_wiki/distiller.py`): context 요약 → llm.structured(PriorBatch) → WikiPrior(inferred-wiki). graceful.
- [ ] **Step 5 — WikiBuilder** (`locus/commonsense_wiki/builder.py`): build_wiki(inputs) — IngestionService→TopologyBuilder→OntologyBuilder→PriorDistiller → persist(graph_mapping → graph_repo/search_repo, embed) → WikiBuildReport. append.
- [ ] **Step 6 — WikiAdmin** (`locus/commonsense_wiki/admin.py`): upsert_prior/list_priors (graph+search).
- [ ] **Step 7 — bundled sample** (`examples/realworld_sample/` + `locus/commonsense_wiki/bundled.py` loader → WorldInputs).
- [ ] **Step 8 — `__init__.py`** 갱신(재노출).
- [ ] **Step 9 — Tests** (`tests/commonsense_wiki/`): graph_mapping(노드/엣지/검색문서, 순수), distiller(mock llm), builder(mock 파이프라인/repos → persist 호출·counts), admin upsert, bundled 로더. + 기존 U1 wiki lookup 테스트 회귀.
- [ ] **Step 10 — Docs**: `construction/U6-commonsense-wiki/code/code-gen-summary.md`.

## Story Coverage
US-1.5→Step5(재사용 ingest) · US-5.1→Step1,5(저장) · US-5.2→Step6(편집) · US-5.3→Step4,5(근거).

## Notes
- 모든 외부(LLM/Embedding/Neo4j/OpenSearch) 주입·mock. 순수 graph_mapping 직접 테스트. 생성 후 전체 pytest 회귀.
