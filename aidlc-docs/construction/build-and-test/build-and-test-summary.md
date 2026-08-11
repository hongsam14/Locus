# Build and Test Summary — Locus (full: 10 units + Web UI)

> **⚠️ Updated for MVP-Improvements cycle (2026-06-09).** See the dedicated section
> **"MVP Improvements Cycle"** at the bottom for the current authoritative results
> (124 backend tests, `__realworld__` removed, per-world wiki, Knowledge.title, VLM orphan fix).
> Sections above describe the original 10-unit build and remain for history.

## Build Status
- **Backend**: Python 3.11+ / setuptools (`pip install -e ".[dev]"`). Success — package imports; `api.main:app` (serving + authoring + augment routers); `locus` CLI (init-schema/build-wiki/build-world/export).
- **Frontend**: `web/` React+Vite+TS — `npm run build` (tsc + vite) → `web/dist/`. Success.
- **Artifacts**: `locus/` package, FastAPI app, `locus` console script, `web/dist/`, `docker-compose.yml` stack.
- **Acceptable warnings**: FastAPI `on_event` deprecation (3); npm audit advisories (dev deps).

## Test Execution Summary

### Unit Tests (offline — external I/O mocked)
- **Backend (pytest)**: **108 passed**, 0 failed · coverage ≈ 80% (`--cov=locus`) · ruff ✅ · black ✅ · PBT Partial ✅.
- **Frontend (vitest)**: **9 passed**, 0 failed · `tsc` clean · `vite build` OK.
- **Total**: **117 passed**.
- **Status**: ✅ PASS

### Integration Tests (live — operator-run)
- **Scenarios**: A schema · B wiki build · C world build (SC-1) · D region query + global · E diff shared/unique (SC-2) · F authoring edit + export · **G augmentation Q&A (U7)** · **H Web UI (U10)**.
- **Status**: ⏳ PENDING operator run (requires Docker Neo4j/OpenSearch + `OPENAI_API_KEY`; UI needs `npm run dev`). Instructions in `integration-test-instructions.md` + `frontend-test-instructions.md`.

### Performance Tests
- **Status**: N/A (best-effort, NFR1-Q3=C; no hard targets). Sanity-check steps documented.

### Additional Tests
- **Contract**: covered by serving API response_model + TestClient (200/404/422). 
- **Security**: N/A (Security extension OFF; basic hygiene — secrets via `.env`, world_id isolation, Cypher identifier guard).
- **E2E**: Scenario C–F constitute the e2e walkthrough.

## Requirement / Success-criteria coverage
- **SC-1** (auto build from inputs) — `build-world --demo` (Scenario C).
- **SC-2** (shared vs region-specific) — `/api/query/diff` (Scenario E) + `unique_ids`/`shared_ids` (offline unit tests).
- **SC-4** (≥1 corroboration) — `BuildReport.corroborations_created` (Scenario C; unit-tested in U4/U9).
- FR-A..I covered across U1–U6, U8, U9 (story map all MVP rows CODE DONE).

## Overall Status
- **Build**: Success (backend + frontend)
- **Unit tests**: ✅ PASS (backend 108 + frontend 9 = 117)
- **Live integration**: pending operator walkthrough A–H (offline equivalents GREEN)
- **Ready for Operations**: Yes (Operations = placeholder; deploy via Docker Compose + static `web/dist`)

## All units complete
- U1 Foundation · U2 Ingestion · U3 Topology · U4 Ontology · U5 Consensus · U6 Wiki build · U7 Augmentation · U8 Query&Serving · U9 Orchestration&Authoring · U10 Web UI — **all CODE DONE**.

## Next Steps
- Run the live integration walkthrough (Scenarios A–H) against real Neo4j/OpenSearch/OpenAI + Web UI, OR accept offline-GREEN.
- Future: live walkthrough hardening, performance/caching if needed, Operations (deploy/monitoring) expansion.

---

# MVP Improvements Cycle (2026-06-09) — Authoritative Results

## Scope
Brownfield increment on the completed MVP. Unit-A (model & wiki structure: real_world removal + cross-world reference, WikiPrior community, Knowledge.title) + Unit-B (ingestion connection: VLM entity orphan fix).

## Build Status
- **Backend**: `pip install -e ".[dev]"` — package imports; `api.main:app` (serving + authoring incl. `/worlds/{id}/related-priors`, augment); `locus` CLI = **init-schema / build-world / export** (`build-wiki` removed — each world self-distills its priors).
- **Frontend**: `web/` unchanged this cycle (Q17=B) — prior `npm run build` still valid.

## Unit Tests (offline — external I/O mocked)
- **Backend (pytest)**: **124 passed**, 0 failed · coverage **82%** (`--cov=locus`) · ruff ✅ · black ✅ · PBT Partial ✅.
- **Frontend (vitest)**: **9 passed** (unchanged).
- **Total**: **133 passed**.
- **Status**: ✅ PASS

## Key changes verified by tests
- **Area 1** — `__realworld__`/`REALWORLD_WORLD_ID`/`load_bundled_realworld`/`WikiBuilder`/`build-wiki` fully removed (`grep` residue = 0). WikiPrior carries `world_id`+`domains`; per-world distillation; `CrossWorldWikiExplorer` (designer-only, single-world NPC paths, BR-A9).
- **Area 2** — `WikiDomain` enum; `WikiPriorLink` (embedding top-k → LLM judge, in-world, cross_domain flag).
- **Area 3** — `Knowledge.title` (required, LLM + `fallback_title`, in search text).
- **Area 4** — `LOCATED_IN` edge added (was absent); VLM area-terrain → `Region(level=TERRAIN)`; barrier terrain → A–B hint; `EntityReconciler` (fuzzy→embed→LLM, non-VLM canonical) + orphan→region or `unconnected_entity_ids`; `detect_orphans` augmentation issue.

## Integration Tests (live — operator-run)
Updated scenarios (replace old B wiki-build):
- **A** schema init · **C** world build (now also distills per-world WikiPriors + WikiPriorLinks) · **D** region query + global · **E** diff · **F** authoring edit + export · **G** augmentation (now surfaces ORPHAN issues) · **H** Web UI.
- **New I** — cross-world reference: build two worlds with overlapping domains; `GET /api/authoring/worlds/{id}/related-priors` returns the OTHER world's priors only (read-through). Confirm NPC query/build never pulls cross-world.
- **New J** — VLM orphan-zero: build `--demo` (map.png) with live VLM; confirm no orphan entities (all have LOCATED_IN/RELATED_TO or appear as augmentation candidates), and area terrain promoted to TERRAIN regions.
- **Status**: ⏳ PENDING operator run (Docker Neo4j/OpenSearch + `OPENAI_API_KEY`).

## Overall Status
- **Build**: Success (backend; frontend unchanged)
- **Unit tests**: ✅ PASS (backend 124 + frontend 9 = 133)
- **Live integration**: pending operator walkthrough (offline equivalents GREEN)
- **Ready for Operations**: Yes (placeholder; deploy via Docker Compose + static `web/dist`)
