# U3 Topology — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-2.1 (hierarchy), US-2.2 (connection edges), US-2.3 (Wiki-weighted strength).
**Verification**: 48 tests PASS (38 prior + 10 U3, incl. PBT weight-range); ruff + black clean. Offline (Wiki mocked).

## Created files (`locus/topology/`)
- `weights.py` — `BASE_WEIGHT` / `TERRAIN_MODIFIER` tables, `base_weight`, `terrain_modifier`, `compute_weight` (clamp 0..1). Pure/deterministic.
- `hierarchy.py` — `assign_hierarchy(regions)`: parent_name→parent_id, orphans top-level, cycle break (BR-U3-2/3/4). Pure.
- `builder.py` — `collect_connection_candidates(regions)` (resolve names, dedupe unordered pairs, stronger-kind merge) + `TopologyBuilder.build(ingestion, world_id)` (hierarchy + symmetric weighted edges + Wiki rationale/DERIVED_FROM, graceful).
- `__init__.py` — re-exports.

## Modified files
- `locus/ingestion/map_image_ingestor.py` — small integration refinement: now emits `terrain.between` as connection hints carrying `terrain_kind` (+ `_TERRAIN_TO_KIND` map), so U3 has a single uniform edge source. (Existing U2 tests still green.)

## Created tests (`tests/topology/test_topology.py`)
weight values + PBT range, hierarchy link/orphan/cycle, candidate resolve/dedupe/unresolved-warn, build symmetric+weighted+wiki-rationale, build-without-wiki base weight.

## Key realizations
- weight = `clamp(base[kind] × Π terrain_modifier)` — deterministic; Wiki supplies rationale + `wiki_prior_ref` only (FD3-Q3/Q4=A).
- Edges only from explicit hints + terrain (FD3-Q2=A); names unresolved → skipped with warning.
- Symmetric edges (two directed CONNECTED_TO per pair) for simple traversal (FD3-Q5=A).
- Persisting topology to Neo4j is done by the orchestrator/U9 (TopologyBuilder returns the in-memory `RegionTopology`).

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U3 (inherits U1 wiki+storage + shared infra).
