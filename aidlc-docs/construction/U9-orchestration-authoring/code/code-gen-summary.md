# U9 Orchestration & Authoring — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-9.3 (app integration) + build_world orchestration + authoring edit; closes MVP end-to-end (SC-1/2/4).
**Verification**: 93 tests PASS (84 prior + 9 U9, incl. authoring TestClient); ruff + black clean; imports + `locus --help` OK (4 CLI commands; app 14 routes).

## Created files
- `locus/storage/persistence.py` — shared `persist_graph(...)` (domain → nodes/edges/docs → repos, graceful). Reused by U6 WikiBuilder (refactored to call it).
- `locus/services/orchestrator.py` — `PipelineOrchestrator.build_world` (Ingestion→Topology(+wiki)→Ontology→persist) + `from_factory`.
- `locus/services/editor.py` — `GraphEditor` (upsert region/knowledge + reindex, delete_node).
- `locus/services/exporter.py` — `Exporter.export_world` → JSON-able dict.
- `locus/services/__init__.py`.
- `locus/demo.py` — `load_demo_world()` (Aldermoor); `examples/demo_world/` (README/memo/map).
- `api/routers/authoring.py` — build world / build wiki / graph summary / wiki prior upsert / region·knowledge upsert / node delete.

## Modified files (additive)
- `locus/storage/base.py` + `neo4j_repo.py` — `GraphRepository.delete_node`.
- `locus/models/reports.py` + `__init__` — `GraphSummary`.
- `locus/commonsense_wiki/builder.py` — `_persist`/`_index` replaced by shared `persist_graph`.
- `api/main.py` — `create_app(**state)` wires serving + authoring; DI via state (tests) or `_wire_default` on startup.
- `locus/__main__.py` — CLI: `build-wiki`, `build-world` (`--demo`/`--inputs`), `export` (+ existing `init-schema`).

## Created tests
- `tests/services/test_services.py` — persist_graph, orchestrator counts (incl. corroboration), editor upsert/delete, exporter serialize.
- `tests/query/test_authoring_api.py` — TestClient: build 200, graph summary, region/knowledge upsert 200, delete 204.

## Key realizations
- **End-to-end** (FD9-Q1=A): `build_world` reuses U2/U3/U4 + shared `persist_graph`; consensus stays query-time (no persistence) — confirmed real-time per query (no cache, ND1-Q3=B).
- **Authoring edit** (Q2=C): region/knowledge upsert + node delete via GraphEditor; serving/authoring routers separated (AD-Q6=A), no auth (MVP).
- **CLI + demo**: `locus build-wiki` → `build-world --demo` → query/export gives a full offline-buildable walkthrough.
- DRY persistence shared between U6 and U9.

## MVP status
- MVP units U1–U6, U8, U9 COMPLETE (code + offline tests). Remaining: U7 Augmentation, U10 Web UI (next cycle) + **Build & Test** (live Neo4j/OpenSearch + OpenAI integration walkthrough).

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U9 (shared app container/infra).
