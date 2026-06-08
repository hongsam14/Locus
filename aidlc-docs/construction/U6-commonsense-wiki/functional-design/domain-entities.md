# U6 Commonsense Wiki (build) — Domain Entities & Schemas

결정: **Q1=B**(디지털 트윈 KG + 파생 WikiPrior), Q2=C(번들+사용자), Q3=A(LLM distillation), Q4=A(Neo4j+OpenSearch+편집+근거), **Q5=B**(append).

## Input / Output
- Input: `WorldInputs`(U2) — 실세계 메모·지도·구조화맵 (+ 번들 샘플). world_id = `__realworld__`(예약).
- Output: `WikiBuildReport { world_id, regions, entities, knowledge, priors, warnings }`.

## 재사용 파이프라인 (Q1=B)
- `IngestionService.ingest_all(__realworld__, inputs)` → IngestionResult.
- `TopologyBuilder(wiki=None).build(... __realworld__)` → RegionTopology. (Wiki 구축 자신이므로 wiki 미주입.)
- `OntologyBuilder(llm, embedding, wiki=None).build(...)` → KnowledgeGraph(디지털 트윈).
- → `__realworld__` 파티션에 regions/entities/knowledge/scopes 영속·색인.

## Distillation 스키마 (Q3=A, LLM)
```text
PriorSuggestion { prior_type(terrain_rule|climate|logistics|fact), condition, effect, description?, confidence }
PriorBatch { items: [PriorSuggestion] }
```
- 입력 컨텍스트: 실세계 IngestionResult/Topology 요약(지형·지역·knowledge). → `WikiPrior`(source=inferred-wiki, generated_by=llm) 변환·저장·색인.

## 공유 영속화 매퍼 (U6 도입, U9 재사용) — `locus/storage/graph_mapping.py`
순수 변환(domain → storage DTO):
- nodes: `region_to_node, entity_to_node, knowledge_to_node, rumor_to_node, wikiprior_to_node`.
- edges: CONTAINS(region.parent_id), CONNECTED_TO(ConnectionEdge), SCOPED_TO(ScopeLink), ABOUT(knowledge.about_entity_ids), DERIVED_FROM(derived_from_prior_ids), RELATED_TO(Relation), DISTORTED_FROM(Rumor).
- search docs: `to_search_docs(knowledge|entity|wikiprior|rumor)` (text=name/statement+desc).

## 편집/근거
- `WikiAdmin.upsert_prior(prior)` (US-5.2) — provenance 유지.
- 모든 prior/노드 provenance 기록(US-5.3).

## Append (Q5=B)
- 재빌드는 기존 `__realworld__` 데이터를 **삭제하지 않고 누적**. 노드 id는 매 빌드 신규(UUID) → 중복 가능성 존재(차순 dedup 대상). MVP: append 그대로.
