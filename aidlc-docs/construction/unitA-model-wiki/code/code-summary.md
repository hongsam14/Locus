# Unit-A (Model & Wiki Structure) — Code Summary

영역 1(real_world 삭제+교차참조) + 2(WikiPrior 커뮤니티) + 3(Knowledge.title). 117 tests GREEN, ruff/black 클린.

## Created
- `locus/commonsense_wiki/linker.py` — `WikiPriorLinker` (임베딩 top-k 후보 → LLM 관계 판정 → `WikiPriorLink`; world 내부, cross_domain 플래그, graceful).
- `locus/commonsense_wiki/cross_world.py` — `CrossWorldWikiExplorer` (기획자 전용 글로벌 도메인 검색, `world_domains` 집계, read-through, 현재 world 제외).

## Modified
- `locus/models/enums.py` — `WikiDomain` enum(13종, OTHER 안전망).
- `locus/models/graph.py` — `Knowledge.title`(필수) · `WikiPrior.world_id+domains` · `WikiPriorLink`(신규) · `fallback_title()` 헬퍼 · `World` realworld 의미 제거.
- `locus/models/io.py` — `KnowledgeView.title`(선택).
- `locus/models/__init__.py` — `WikiDomain`/`WikiPriorLink`/`fallback_title` export.
- `locus/storage/graph_mapping.py` — knowledge title 왕복+검색텍스트, wikiprior world_id/domains 왕복, `prior_link_edges`/`edge_to_prior_link`(`PRIOR_RELATED_TO`), `wikiprior_to_node/_doc` 시그니처(world_id from prior).
- `locus/storage/base.py` — `SearchRepository.hybrid_search(world_id: str | None)`.
- `locus/storage/opensearch_repo.py` — `world_id=None` 전역 검색 + list 필터(`terms`, 도메인 overlap).
- `locus/storage/neo4j_repo.py` — World 노드/제약 제거(미영속).
- `locus/storage/persistence.py` — `prior_links` 인자 + `PRIOR_RELATED_TO` upsert.
- `locus/commonsense_wiki/schemas.py` — `PriorSuggestion.domains` · `PriorLinkVerdict`.
- `locus/commonsense_wiki/distiller.py` — 범용화: world_id + domains 설정.
- `locus/commonsense_wiki/base.py` — `CommonsenseWiki` world_id 필수, hit/fallback에 world_id/domains.
- `locus/commonsense_wiki/admin.py` — per-world(world_id 명시), REALWORLD 제거.
- `locus/ingestion/schemas.py`·`mapping.py` — `ExtractedKnowledge.title`, `to_knowledge` title(+fallback).
- `locus/ontology/schemas.py`·`corroboration.py` — corroboration title(+fallback).
- `locus/ontology/builder.py`·`locus/topology/builder.py` — `set_wiki()` (build-time world-scoped wiki 주입).
- `locus/augmentation/types.py`·`apply.py`·`engine.py` — answer.title, ADD title(+fallback), `wiki_provider`(per-world).
- `locus/services/orchestrator.py` — build_world: distill→link→prior 우선 영속화→단일 world wiki→나머지; `from_factory`에 distiller/linker/llm.
- `locus/__main__.py` — `build-wiki` 명령 제거.
- `api/main.py` — wiki_builder 제거, `from_factory` orchestrator, `wiki_explorer`, per-world `wiki_provider`.
- `api/routers/authoring.py` — `wiki/build` 제거, `POST /worlds/{id}/priors`, `GET /worlds/{id}/related-priors`(기획자).
- `CLAUDE.md`·`examples/demo_world/README.md` — build-wiki/realworld 언급 갱신.

## Deleted
- `locus/commonsense_wiki/bundled.py`, `locus/commonsense_wiki/builder.py`(WikiBuilder), `examples/realworld_sample/`, `REALWORLD_WORLD_ID`(`locus/__init__.py`).

## Tests
- `tests/commonsense_wiki/test_wiki.py`·`test_wiki_build.py` 재작성(단일 world, domains, linker, cross-world, admin per-world).
- 모든 `Knowledge(...)` 픽스처에 title 추가; storage 스키마/topology fakes 갱신.
- 신규: fallback_title, WikiPrior/WikiPriorLink 왕복·필수 검증, linker 게이트/저가중치/임베딩 없음, cross-world 집계/제외/빈결과, orchestrator priors+links.

## 불변식 검증
- BR-A13: `grep -riE "realworld|load_bundled|WikiBuilder|build-wiki"` → 코드/테스트 0건.
- BR-A9: NPC 경로(corroboration/runtime/augmentation) 단일 world; 교차참조는 explorer(기획자)만.
