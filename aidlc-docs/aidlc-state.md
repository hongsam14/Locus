# AI-DLC State Tracking

## Project Information
- **Project Name**: Locus — Spatial Knowledge Graph Builder for Game Worlds
- **Project Type**: Greenfield
- **Start Date**: 2026-06-07T10:54:58Z
- **Current Stage**: OPERATIONS (placeholder) — **AI-DLC PROJECT COMPLETE 2026-06-08**. Both cycles done: MVP (U1–U6,U8,U9) + cycle 2 (U7,U10). All 10 units. 117 tests GREEN. Remaining: operator live walkthrough (A–H); future deploy/monitoring.

## Execution Plan Summary
- **Stages to Execute**: Application Design, Units Planning, Units Generation, Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation, Build and Test (per-unit loop).
- **Stages to Skip**: Reverse Engineering (greenfield).
- **Risk**: Medium-High. Rollback Easy (greenfield). Testing Complex.

## Workspace State
- **Existing Code**: No
- **Programming Languages**: None yet (to be decided in Inception)
- **Build System**: None yet
- **Project Structure**: Empty (only `.claude/`, `.aidlc/`, `CLAUDE.md`)
- **Reverse Engineering Needed**: No
- **Workspace Root**: /home/thinkpad/Desktop/src/Locus

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection — Greenfield; empty workspace; no reverse engineering needed.
- [ ] Reverse Engineering — N/A (greenfield).
- [x] Requirements Analysis — COMPLETE, **awaiting approval** (comprehensive depth). `requirements.md` written. 2 clarification rounds, no contradictions.
  - Answer map R1: Q1=B / Q2=C / Q3=C / Q4=C / Q5=A / Q6=X→CL6 / Q7=D(default OpenAI) / Q8=B / Q9=C / Q10=A / Q11=A / Q12=C / Q13=A / Security=B / PBT=B.
  - Answer map R2 (clarification): CL1=B / CL2=B(+디지털 트윈) / CL3=C / CL4=A / CL5=A,B,C / CL6=B.
  - New core features: (1) Common-sense Wiki = real-world digital-twin KB built via the SAME ingestion pipeline → topology weighting + lore corroboration; (2) interactive Knowledge-Augmentation Q&A loop (designer-in-the-loop).
  - Tech: Python 3.11+ / FastAPI / React / Neo4j + OpenSearch / Docker Compose / LLM provider-abstraction (default OpenAI).
- [x] Requirements Analysis — **APPROVED 2026-06-07T11:54:06Z** ("Approve & Continue").
- [x] User Stories — Part 1 plan APPROVED (SP1=D/SP2=B/SP3=A/SP4=A/SP5=A/SP6=A). Part 2 generated: `personas.md` (P1 내러티브·P2 월드/레벨·P3 NPC 런타임) + `stories.md` (9 Epic, 30 스토리, Given/When/Then, P0×22/P1×8). **Awaiting approval.**
- [x] Workflow Planning — COMPLETE (`execution-plan.md`); **awaiting approval**. All conditional stages EXECUTE; RE skipped.
- [x] Application Design — answers AD-Q1=A/Q2=A/Q3=A/Q4=C/Q5=A/Q6=A + AD-CL1=A (hybrid: sync orchestrator + LangGraph local). Artifacts generated (components/component-methods/services/component-dependency/application-design). 14 components, 8 services. **Awaiting approval.**
- [x] Units Planning — answers UOW-Q1=A/Q2=A/Q3=A/Q4=A/Q5=X/Q6=A + UOW-CL1=A. Plan approved via answers.
- [x] Units Generation — 10 Units (U1~U10). Artifacts: unit-of-work / -dependency / -story-map. Build order U1→U2→U3→U4→U6→U5→U8→U9 (MVP) → U7→U10 (next). All 30 stories assigned. **Awaiting approval.**

### Units (build order)
- MVP cycle: U1 Foundation, U2 Ingestion, U3 Topology, U4 Ontology, U6 Wiki build, U5 Consensus, U8 Query&Serving, U9 Orchestration&Authoring.
- Next cycle: U7 Augmentation, U10 Web UI.
- Wiki: U1 lookup interface + LLM fallback; U6 builds from user's real-world data (runtime-first).

### 🟢 CONSTRUCTION PHASE
- [~] **U1 Foundation** — FD ✅ / NFR-R ✅ / NFR-D ✅ / Infra ✅ / **Code Gen ✅ (24 tests PASS, ruff/black clean)**. Awaiting code approval.
  - FD: FD1-Q1=A/Q2=A/Q3=A/Q4=B(:Rumor label)/Q5=A/Q6=A. NFR-R: Q1=A/Q2=A/Q3=C/Q4=A/Q5=A/Q6=A. NFR-D: Q1=A/Q2=A/Q3=B(no cache). Infra: all A.
  - Code: `locus/{models,config,llm,storage,commonsense_wiki}` + CLI + docker-compose/Dockerfile + tests. Stories US-9.1/9.2/9.4/9.3 [x].
- [~] **U2 Ingestion** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (38 tests total PASS)**. `locus/ingestion/` (schemas/mapping/4 ingestors/service). Stories US-1.1~1.4 [x]. Awaiting code approval.
- [~] **U3 Topology** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (48 tests PASS)**. `locus/topology/` (weights/hierarchy/builder). Refined U2 map_image to emit terrain.between as hints. Stories US-2.1~2.3 [x]. Awaiting code approval.
- [~] **U4 Ontology** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (58 tests PASS)**. `locus/ontology/` (similarity/dedup/corroboration/builder). Additive: Knowledge.is_global+region_hint, ScopeType.GLOBAL, ExtractedKnowledge.is_global, ABOUT resolved in U2 text_ingestor. Stories US-3.1~3.3 [x]. Awaiting code approval.
- [~] **U6 Wiki build** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (67 tests PASS)**. `locus/commonsense_wiki/` (distiller/builder/admin/bundled) + shared `locus/storage/graph_mapping.py` (reused by U9) + `WikiBuildReport` + `examples/realworld_sample/`. Stories US-1.5/5.1/5.2/5.3 [x]. Awaiting code approval.
- [~] **U5 Consensus** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (73 tests PASS)**. `locus/consensus/` (propagation max-product, engine compute_consensus). Additive: ConsensusView.global_knowledge, KnowledgeView.distortion_degree. Stories US-4.1~4.3 [x]. Awaiting code approval.
- [~] **U8 Query&Serving** — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (84 tests PASS)**. `locus/query/` (loader/engine) + `api/` (FastAPI serving). Additive: GraphRepository.get_edges + reverse graph_mapping. Stories US-8.1~8.3 [x]. Awaiting code approval.
- [~] **U9 Orchestration&Authoring** (last MVP unit) — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (93 tests PASS)**. `locus/services/` (orchestrator/editor/exporter) + shared `persist_graph` + `api/routers/authoring.py` + CLI(build-world/build-wiki/export) + demo world. Additive: delete_node, GraphSummary. US-9.3 [x]. Awaiting code approval. **MVP CODE COMPLETE.**
- [~] **U7 Augmentation** (cycle 2) — FD ✅ / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (104 tests PASS)**. `locus/augmentation/` (types/detectors/questions/apply/session_store/engine/service/graph) + authoring augment API. Stories US-6.1~6.3 [x]. Awaiting code approval.
- [~] **U10 Web UI** (cycle 2, final) — FD ✅ (FD10 all A; CL1=A Region.position from map) / NFR-R·NFR-D·Infra SKIP / **CodeGen ✅ (frontend 9 vitest + tsc + vite build; backend 108 pytest)**. `web/` React app (MapOverlay/RegionPanel/AugmentPanel/Toolbar) + backend: Region.position, GeoJSON/VLM coords, GET export. Stories US-7.1~7.3 [x]. Awaiting code approval. **ALL 10 UNITS DONE.**
- [x] **Build and Test** — instructions generated (build/unit/integration/performance/summary). Offline: **93 tests PASS, 82% cov, ruff/black clean**. Live integration (Scenarios A–F: schema/wiki/world-build SC-1/query+global/diff SC-2/edit+export) operator-run. **APPROVED.**

### 🟡 OPERATIONS PHASE
- [x] Operations — PLACEHOLDER (local Docker Compose + web/dist). `operations/operations.md`. **Full project complete 2026-06-08 — all 10 units, 2 cycles.**

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Requirements Analysis (Q: Security = B) |
| Property-Based Testing | Yes (Partial — pure functions & serialization round-trips only) | Requirements Analysis (Q: PBT = B) |
