# U8 Query & Serving — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-8.1 (region knowledge), US-8.2 (shared vs unique / diff, SC-2), US-8.3 (metadata).
**Verification**: 84 tests PASS (73 prior + 11 U8, incl. FastAPI TestClient 200/404/422); ruff + black clean. Offline (repo/engine mocked; API via TestClient).

## Created files
- `locus/query/loader.py` — `WorldLoader.load(world_id)` → (KnowledgeGraph, RegionTopology) via reverse mapping.
- `locus/query/engine.py` — pure `view_items` / `split_shared_unique` / `diff_sets`; `QueryEngine.knowledge_for_region` / `diff_regions`.
- `locus/query/__init__.py`.
- `api/__init__.py`, `api/main.py` (`create_app` factory + `/health` + module `app`), `api/routers/query.py` (serving router: region knowledge / diff), `api/routers/__init__.py`.

## Modified files (additive)
- `locus/storage/base.py` + `neo4j_repo.py` — `GraphRepository.get_edges(world_id, types)`.
- `locus/storage/graph_mapping.py` — reverse mappers (`node_to_region/entity/knowledge/rumor/wikiprior`, `edge_to_connection/scope`, `_provenance`, `_json_field`).

## Created tests (`tests/query/`)
- `test_query.py` — reverse-mapping round-trip (region/knowledge flags), WorldLoader reconstruction, pure split/diff, QueryEngine region knowledge + not-found.
- `test_api.py` — TestClient: health, region knowledge 200, missing→404, diff 200, missing-param→422.

## Key realizations
- **WorldLoader** reconstructs the in-memory graph from Neo4j (nodes carry parent_id/about/derived/is_global; CONNECTED_TO + SCOPED_TO come from `get_edges`) → reuses U5 ConsensusEngine (Q4=A round-trips with graph_mapping).
- **shared/unique** (FD8-Q3=A): unique = direct (region-specific), shared = inherited+global+propagated+rumors; `diff_regions` for SC-2.
- **serving API** (FastAPI): public, no auth (MVP), JSON contract; LookupError→404, missing param→422.
- Pure split/diff separated; loader/engine/HTTP mockable.

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U8 (runs in shared app container).
- Live API against real Neo4j (uvicorn `api.main:app`) validated in Build & Test; `app` module-level connects on startup.
