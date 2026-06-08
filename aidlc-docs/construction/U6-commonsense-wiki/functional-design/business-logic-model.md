# U6 Commonsense Wiki (build) — Business Logic Model

## WikiBuilder.build_wiki(inputs) -> WikiBuildReport  (US-1.5/5.1, FR-A6/E1)
의존 주입: IngestionService, TopologyBuilder, OntologyBuilder, PriorDistiller, GraphRepository, SearchRepository.

흐름(world_id = `__realworld__`):
1. `ingestion = ingestion_service.ingest_all(__realworld__, inputs)`.
2. `topology = topology_builder.build(ingestion, world_id=__realworld__)` (wiki 미주입).
3. `kg = ontology_builder.build(ingestion, topology, world_id=__realworld__)` (디지털 트윈).
4. `priors = prior_distiller.distill(ingestion, topology, world_id=__realworld__)` (LLM).
5. **persist**(append, Q5=B):
   - graph_mapping → nodes/edges → `graph_repo.upsert_nodes/edges`.
   - 색인 대상(knowledge/entity/wikiprior) → `to_search_docs` → embedding → `search_repo.index`.
6. WikiBuildReport(counts + warnings) 반환.
- graceful: distill 실패 → priors 생략(경고), KG는 유지. embed 실패 → 색인 일부 생략(경고).

## PriorDistiller.distill(ingestion, topology, world_id) -> list[WikiPrior]  (Q3=A)
- context = 지형 entity/지역/대표 knowledge 요약.
- `llm.structured(prompt(context), PriorBatch)` → 각 item → `WikiPrior(source=inferred-wiki, generated_by=llm, provenance)`.
- 실패 → [] (graceful).

## WikiAdmin (편집·조회, US-5.2/5.3)
- `upsert_prior(prior: WikiPrior)` → graph_repo.upsert + search_repo.index (provenance 유지).
- `list_priors()` / `get_prior(id)` (그래프/검색 조회).

## Bundled dataset (Q2=C)
- `examples/realworld_sample/`(작은 실세계 메모+간단 맵) + 로더 `load_bundled_realworld() -> WorldInputs`.
- `build_wiki`는 번들 또는 사용자 제공 inputs 모두 수용.

## graph_mapping (공유, 순수)
- domain → Node/Edge/SearchDoc 변환 함수 모음. U9가 가상 세계 영속화에 재사용.
- 순수 → 단위 테스트.

## U1 lookup과의 관계
- U6가 WikiPrior를 `__realworld__`에 저장·색인 → U1 `CommonsenseWiki.lookup_*`(SearchRepository 검색)가 즉시 활용. (U3/U4가 실제 prior로 가중·고증.)
