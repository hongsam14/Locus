# U1 Foundation — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-9.1 (Neo4j persistence), US-9.2 (OpenSearch hybrid search), US-9.4 (provider abstraction), US-9.3 (Docker Compose foundation), FR-E lookup (Wiki interface + fallback).
**Verification**: 24 unit tests PASS (incl. hypothesis PBT round-trip); `ruff` + `black` clean; `compileall` clean. External calls (OpenAI/Neo4j/OpenSearch) are lazily imported and mocked in tests, so the suite runs fully offline.

## Created files (application code — workspace root)

### Package `locus/`
- `__init__.py` — version + `REALWORLD_WORLD_ID = "__realworld__"`.
- `__main__.py` — minimal CLI: `locus init-schema` (full surface in U9).
- `models/` — `enums.py`, `graph.py` (World/Region/Entity/Relation/Knowledge/Rumor/WikiPrior/ConnectionEdge/ScopeLink/Provenance), `io.py` (IngestionResult/RegionTopology/KnowledgeGraph/ConsensusView/QueryResult/RegionDiff/SearchDoc/SearchHit/KnowledgeView), `reports.py` (BuildReport/BuildWarning), `__init__.py` (re-exports).
- `config/` — `settings.py` (pydantic-settings `Settings` + `get_settings`), `__init__.py`.
- `llm/` — `base.py` (LLMProvider/VLMProvider/EmbeddingProvider Protocols), `retry.py` (tenacity 3×/exp, 30s), `openai_provider.py` (LangChain+OpenAI adapters), `factory.py` (ProviderFactory), `__init__.py`.
- `storage/` — `base.py` (GraphRepository/SearchRepository ports + Node/Edge/TraversalSpec/Path DTOs), `neo4j_repo.py` (Neo4jGraphRepository: MERGE upserts, world_id scoping, ensure_schema, weighted traverse), `opensearch_repo.py` (OpenSearchRepository: single index `locus_search`, kNN+BM25, world_id filter; `index_mapping`/`build_search_body` pure fns), `schema.py` (SchemaInitializer), `__init__.py`.
- `commonsense_wiki/` — `base.py` (CommonsenseWiki lookup + LLM fallback), `__init__.py`.

### Tests `tests/`
- `models/test_models.py` — PBT round-trip (BR-20/21), range validation (BR-4..6), Rumor invariant (BR-13), enum stability.
- `llm/test_retry_and_factory.py` — retry success/exhaustion, factory error paths.
- `storage/test_storage.py` — Cypher construction + injection guard, world_id scoping, schema constraints, traverse params, OpenSearch body (world_id filter, kNN/BM25), index mapping dim.
- `commonsense_wiki/test_wiki.py` — wiki hit (no LLM) vs miss→LLM fallback.

### Root build / deploy
- `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `env.example`, `README.md`, `docker-compose.yml` (app + neo4j:5 + opensearch:2, named volumes, healthchecks, OpenSearch security off), `Dockerfile`.

## Key design realizations
- **Ports & Adapters**: core depends only on Protocols; Neo4j/OpenSearch/OpenAI behind adapters → mockable, swappable.
- **world_id partition** everywhere; wiki = `__realworld__`. `:Rumor` is a separate label (FD1-Q4=B).
- **Graceful fallback**: `CommonsenseWiki` degrades to LLM inference when the wiki is empty/low-score → U3/U4 can run before U6 (CL1=A).
- **No caching** (ND1-Q3=B). **Retry** 3×/exp/30s (ND1-Q1=A).
- Cypher labels/rel-types validated against an identifier regex (injection guard) since they cannot be parameterized.

## Deferred / notes
- Embedding default `text-embedding-3-small` (dim 1536, configurable) — vs Enola's sentence-transformers, per NFR1-Q1=A.
- `app` compose service runs `init-schema` then idles; uvicorn (`api.main:app`) is wired in U8/U9.
- Live integration (real Neo4j/OpenSearch via `docker-compose up`) to be exercised in Build & Test.
