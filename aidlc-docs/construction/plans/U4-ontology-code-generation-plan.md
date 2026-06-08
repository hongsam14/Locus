# U4 Ontology — Code Generation Plan

Code 위치 = `locus/ontology/` (+ U1/U2 additive 변경). Stories US-3.1~3.3.

## Steps  (ALL DONE — 58 tests pass, ruff/black clean)
- [x] **Step 1 — Model additions** (additive): `locus/models/enums.py` `ScopeType.GLOBAL`; `locus/models/graph.py` `Knowledge.is_global: bool=False`; `locus/ingestion/schemas.py` `ExtractedKnowledge.is_global`; `locus/ingestion/mapping.to_knowledge` carries is_global.
- [ ] **Step 2 — schemas** (`locus/ontology/schemas.py`): `CorroborationSuggestion`, `CorroborationBatch`, `DuplicateVerdict`.
- [ ] **Step 3 — similarity** (`locus/ontology/similarity.py`): 결정론적 유사도 측정의 자리. 현재 `cosine(a,b)`, `candidate_pairs(vectors, threshold)`; 향후 구조/지형 관계 유사도 확장 지점. 순수·외부 의존 없음.
- [ ] **Step 4 — dedup** (`locus/ontology/dedup.py`): `Deduplicator(embedding, llm, threshold)` — embed statements → similarity로 candidate pairs → LLM verdict → `merge_duplicates`. exact fallback. merge 순수 분리. (측정=similarity / 병합 정책=dedup.)
- [ ] **Step 5 — corroboration** (`locus/ontology/corroboration.py`): `CorroborationGenerator(llm, wiki, max_per_region)` → region context (+wiki grounding) → CorroborationBatch → Knowledge(inferred-wiki, ×0.8) + direct scope.
- [ ] **Step 6 — OntologyBuilder** (`locus/ontology/builder.py`): `build(ingestion, topology, world_id)` — graphize + ABOUT(`resolve_about`) + scope(`scope_knowledge`: direct/global/unscoped) + corroboration + dedup → KnowledgeGraph. 순수 helper 분리.
- [ ] **Step 7 — `__init__.py`** 재노출.
- [ ] **Step 8 — Tests** (`tests/ontology/`): cosine/candidate_pairs(+PBT), dedup(mock embed+llm verdict, merge), corroboration(mock llm+wiki, ×0.8, scope), scope_knowledge(direct/global/unscoped), about 해소, build end-to-end(mock providers). + U1/U2 additive 변경 회귀.
- [ ] **Step 9 — Docs**: `construction/U4-ontology/code/code-gen-summary.md`.

## Story Coverage
US-3.1→Step6 · US-3.2→Step6(scope/about)+Step1(global) · US-3.3→Step5 · dedup(CL2)→Step3,4.

## Notes
- LLM/Embedding/Wiki 주입(mock). 순수 로직 비의존. 생성 후 pytest 전체 회귀(오프라인).
