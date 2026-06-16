# AI-DLC State Tracking

## Project Information
- **Project Name**: Locus — Spatial Knowledge Graph Builder for Game Worlds
- **Project Type**: Greenfield
- **Start Date**: 2026-06-07T10:54:58Z
- **Current Stage**: INCEPTION (**RUMOR DISTORTION / GAME SESSION cycle**, started 2026-06-09) — Requirements Analysis ✅ (awaiting approval). Prior cycle: MVP IMPROVEMENTS COMPLETE 2026-06-09.

## Rumor Distortion / Game Session Cycle (2026-06-09) — Phase 1
- **Concept**: New dynamic **game-session layer** (PostgreSQL) over the static canonical world (Neo4j). LLM-distorted Rumors, support/promotion, GameMaster turns, Timeline. Triggered from web.
- **Answers**: Q1=B/Q2=B/Q3=C/Q4=GameMaster/Q5=A+support/Q6=A/Q7=A/Q8=A/Q9=X(PG, not indexed)/Q10=X/Q11=A/Q12=A. Clarif: A=B(GameMaster per-turn rumor lifecycle + Timeline; Event=Phase2)/B=X(rephased)/C1=A/C2=A/D1=A/D2=A/E=A/F1=A(PostgreSQL)/F2=A(SessionRepository port)/G=A.
- **Phase 1 (this cycle)**: GameSession lifecycle + PostgreSQL SessionRepository + region rumor generation (degree chain, LLM) + support + promotion/demotion + GameMaster turns + Timeline + NPC query rule (Knowledge(+promoted)+Rumor only) + web (session UI, generate button, browse history) + dead buildWiki cleanup.
- **Phase 2 (deferred)**: Event + Event interaction driving dynamic distortion.
- **Docs**: `inception/requirements/rumor-distortion-{verification-questions,clarification-questions,requirements}.md`.
- **Triggers**: NEW infra (PostgreSQL) → Infrastructure Design EXECUTE; new components/services → Application Design likely EXECUTE.
- **Stage progress**: [x] Workspace Detection · [x] Requirements APPROVED · [x] User Stories SKIP · [x] Workflow Planning APPROVED · [x] Application Design APPROVED · [x] Units Generation (awaiting approval; UOW-R Q1=A) · [~] CONSTRUCTION (S1→S2→S3): **S1 Functional Design ✅ — awaiting approval**.
- **S1 Functional Design (2026-06-15)**: APPROVED. answers **FD-S1 Q1=B**(세션 시작 시 모든 region에 기본 distortion row 생성, degree=0.3)/**Q2=A**(start_session에서 world 존재 검증→404)/**Q3=A**(PostgreSQL 하이브리드: 핵심=정규 컬럼+인덱스, provenance/payload=JSONB)/**Q4=A**(id=new_id() uuid4, created_at=DB now)/**Q5=A**(미사용 Neo4j Rumor 전용 테스트만 정리, consensus auto-rumor view 유지). Artifacts: `construction/S1-session-foundation/functional-design/{domain-entities,business-logic-model,business-rules}.md`.
- **S1 Infrastructure Design (2026-06-15)**: answers **SI-Q1=A**(`postgres:16-alpine`)/**Q2=A**(바인드마운트 `./data/postgres`)/**Q3=A**(psycopg3 + SQLAlchemy 동기, `postgresql+psycopg://`)/**Q4=A**(단일 `SESSION_DB_URL`)/**Q5=A**(`init-schema`+앱부팅 둘다 `ensure_schema`)/**Q6=A**(`app`→postgres `service_healthy` 의존). 세션 전용 PostgreSQL을 기본 인프라 tier에 추가(캐노니컬 불변, NFR-R3). Artifacts: `construction/S1-session-foundation/infrastructure-design/{infrastructure-design,deployment-architecture}.md` + `shared-infrastructure.md` 갱신. pyproject: `sqlalchemy>=2`/`psycopg[binary]>=3`. **APPROVED**.
- **S1 NFR (light, 2026-06-15)**: NFR-R1~R6을 단일 light 노트로 고정(별도 질문 없음 — 요구사항 명시·FD/Infra 반영). `construction/S1-session-foundation/nfr/nfr-light.md`. (NFR-R4 graceful·승격/confidence 순수로직은 S2 범위.)
- **S1 Code Generation Plan (2026-06-15)**: 17 steps. `construction/plans/S1-session-foundation-code-generation-plan.md`. **APPROVED & EXECUTED**.
- **S1 Code Generation EXECUTED (2026-06-15)**: new `locus/session/`(models/repository port/memory_repo/service) + `locus/storage/postgres_session_repo.py`(SQLAlchemy, JSONB-variant, ensure_schema) + `api/routers/session.py`(5 routes) + main.py wiring + config `session_db_url` + CLI init-schema. Infra: docker-compose `postgres:16-alpine`(default tier, healthcheck, bind-mount), pyproject `sqlalchemy>=2`/`psycopg[binary]>=3`, setup-volumes, env.example. Removed unused Neo4j Rumor (model/mapping/persist/loader/exporter/orchestrator/NODE_LABELS); kept consensus auto-rumor view. **153 backend tests GREEN (was 124), ruff+black clean, compileall clean** (Postgres adapter tested offline against SQLite; live PG operator-run). Code summary: `construction/S1-session-foundation/code/code-summary.md`. APPROVED.
- **S1 Build & Test (2026-06-15)**: offline GREEN — 153 backend pytest, ruff/black/compileall clean; import smoke OK (5 session routes mounted). Live PostgreSQL scenarios S1-A..G documented (operator-run). `construction/S1-session-foundation/build-and-test/build-and-test-summary.md`. **S1 UNIT COMPLETE.**
- **S2 Rumor Engine — Functional Design (2026-06-15)**: answers **FD-S2 Q1=A**(체인 degrees=[d/3,2d/3,d], 리전 distortion=상한)/**Q2=direct+propagated+기존 세션Rumor**(원본 집합; NPC뷰에선 propagated 제외→원거리=소문only)/**Q3=A**(체인=직전 텍스트 재왜곡)/**Q4=A**(regenerate=전체삭제 후 재생성, 승격 포함)/**Q5=A**(support 초기 0.0, threshold 0.6)/**Q6=A**(승격=KnowledgeView scope=direct·is_rumor=True)/**Q7=A**(query/engine.py 순수 helper `canonical_known`, QueryEngine 무변경). Artifacts: `construction/S2-rumor-engine/functional-design/{domain-entities,business-logic-model,business-rules}.md`. 신규 타입: RumorDraft/PromotionResult/TurnResult. SessionRumor 모델 무변경. APPROVED.
- **S2 Code Generation Plan (2026-06-15)**: 15 steps. `construction/plans/S2-rumor-engine-code-generation-plan.md`. APPROVED & EXECUTED.
- **S2 Code Generation EXECUTED (2026-06-15)**: new `locus/session/{rumor_generator,promotion,game_master,query}.py` + pure `canonical_known` helper in `query/engine.py`(QueryEngine 무변경) + session router +6 routes(generate/regen/support/distortion/advance-turn/knowledge) + main.py wiring(game_master/session_query) + `__init__` exports. `SourceKind.SESSION_RUMOR` 추가(additive). 체인 degrees=[d/3,2d/3,d]; 소스=direct+propagated+기존 세션Rumor; 텍스트 계보; confidence=src*(1-degree); threshold 0.6 전이; 승격=direct-like KnowledgeView(is_rumor=True). **177 backend tests GREEN (was 153), ruff+black clean**; 11 session routes(5 S1+6 S2); 캐노니컬/S1 회귀 0. Code summary: `construction/S2-rumor-engine/code/code-summary.md`. APPROVED.
- **S2 Build & Test (2026-06-15)**: offline GREEN — 177 backend pytest, ruff/black clean; 11 session routes mounted. Live LLM+PostgreSQL scenarios S2-A..H documented (operator-run). `construction/S2-rumor-engine/build-and-test/build-and-test-summary.md`. **S2 UNIT COMPLETE.**
- **S3 Web UI — Functional Design (2026-06-15)**: answers **FD-S3 Q1=A**(SessionBar+SessionPanel)/**Q2=GameMaster(SessionPanel) 중심**(소문 생성/관리 컨트롤은 SessionPanel, 대상=지도 선택 리전; RegionPanel은 세션 NPC 지식만)/**Q3=A**(세션 선택 시 sessionKnowledge)/**Q4=A**(support 슬라이더)/**Q5=A**(SessionPanel 타임라인+드롭다운)/**Q6=A**(dead buildWiki 전부 제거). 발견: 소문 목록 재로드용 **additive read 엔드포인트 `GET /api/session/sessions/{sid}/regions/{rid}/rumors`** 추가 필요(repo.list_rumors 재사용). Artifacts: `construction/S3-web-ui/functional-design/{domain-entities,business-logic-model,business-rules}.md`. APPROVED.
- **S3 Code Generation Plan (2026-06-15)**: 11 steps. APPROVED & EXECUTED.
- **S3 Code Generation EXECUTED (2026-06-15)**: backend additive `GET …/rumors`(+GameMasterService.list_rumors); frontend `web/src/` — types(GameSession/SessionRumor/RegionDistortion/TimelineEntry/TurnResult), api.ts session methods(buildWiki 제거), **SessionBar**(생성/선택/종료) + **SessionPanel**(GameMaster 허브: advance-turn·timeline·distortion 슬라이더·generate/regen·소문 목록+support 슬라이더+PROMOTED 배지), RegionPanel(sessionId→sessionKnowledge), App/Toolbar 수정. **Backend 177 pytest + Frontend 14 vitest GREEN, tsc+vite build clean, ruff/black clean**; buildWiki residue 0. Code summary: `construction/S3-web-ui/code/code-summary.md`. APPROVED.
- **S3 Build & Test (2026-06-15)**: offline GREEN — **191 total (177 backend + 14 frontend)**, tsc/vite build clean. Live full-UI scenarios S3-A..H documented. `construction/S3-web-ui/build-and-test/build-and-test-summary.md`. **S3 UNIT COMPLETE.**
- **🎉 RUMOR / GAME-SESSION PHASE 1 CODE COMPLETE (2026-06-15)** — S1 (Session Foundation & Infra/PostgreSQL) + S2 (Rumor Engine) + S3 (Web UI). 191 offline tests GREEN. Phase 2 (Event interaction → dynamic distortion) deferred. Remaining (optional): Operations doc update (PostgreSQL stack) for this cycle.
- **Units**: S1 Session Foundation & Infra (R1,NFR; Infra Design here; deletes Neo4j Rumor) → S2 Rumor Engine (R2-R5) → S3 Web UI (R6). Artifacts: `inception/application-design/rumor-session/unit-of-work{,-dependency,-story-map}.md`.
- **App Design decisions**: AD-R Q1=A(SQLAlchemy)/Q2=A(ensure_schema)/Q3=A(GameMasterService)/Q4=A(SessionQueryEngine)/Q5=A(advance_turn)/Q6=A(SessionRumor new + delete Neo4j Rumor). New package `locus/session/`. Components: GameSession/SessionRumor/RegionDistortion/TimelineEntry, SessionRepository(+Postgres/InMemory), RumorGenerator, PromotionPolicy, GameMasterService, SessionService, SessionQueryEngine, session API.
- **Stages**: EXECUTE = Application Design, Units Generation, per-unit Functional Design, NFR-R/NFR-D (light, S1·S2), Infrastructure Design (S1: PostgreSQL), Code Gen, Build&Test. SKIP = User Stories.
- **Units (proposed)**: S1 Session Foundation & Infra → S2 Rumor Engine → S3 Web UI.

## (prior) MVP IMPROVEMENTS cycle COMPLETE 2026-06-09 Units A+B done across Inception→Construction→Build&Test→Operations. **133 offline tests GREEN (124 backend + 9 frontend), 82% cov, ruff/black clean.** `__realworld__` removed; per-world wiki + cross-world designer reference; Knowledge.title; VLM orphan fix (LOCATED_IN + terrain promotion + reconciler). Prior: AI-DLC project complete 2026-06-08.

## MVP Improvements Cycle (2026-06-09)
- **Scope**: 4 improvements — (1) remove `__realworld__` + cross-world wiki reference, (2) WikiPrior community/cross-domain edges, (3) Knowledge.title, (4) VLM entity orphan fix.
- **Answers**: Q1=B/Q2=C/Q3=A/Q4=B/Q5=B/Q6=C/Q7=B/Q8=C/Q9=A+UI/Q10=A/Q11=B/Q12-14=X/Q15=B/Q16=C/Q17=B. Clarif: CL1=A/CL2=C/CL3=C/CL4=A. Assumptions 1-3 accepted.
- **Unit split (Q16=C)**: Unit-A (model+wiki: areas 1+2+3) → Unit-B (ingestion: area 4). Web UI excluded (Q17=B).
- **Docs**: `inception/requirements/mvp-improvements-{verification-questions,clarification-questions,requirements}.md`.
- **Stage progress (this cycle)**:
  - [x] Workspace Detection (brownfield resume)
  - [x] Requirements Analysis — APPROVED 2026-06-09
  - [x] User Stories — SKIP (existing personas/stories cover actors)
  - [x] Workflow Planning — **awaiting approval** (`inception/plans/mvp-improvements-execution-plan.md`)
  - [x] Application Design — SKIP / Units Generation — SKIP (units defined in plan)
  - [x] Unit-A Functional Design — **awaiting approval** (`construction/unitA-model-wiki/functional-design/`)
    - Decisions: FD-A Q1=X(no World node)/Q2=A(cross-world=designer-only)/Q3=A(in-world edges)/Q4=A(fixed WikiDomain enum)/Q5=A(WikiPriorLink)/Q6=A(title in search); CL-A1=A/CL-A2=A.
    - Key: no `build-wiki`/WikiBuilder (each world self-distills priors during build-world); NPC paths single-world; CrossWorldWikiExplorer for designer.
  - [x] Unit-A Code Generation — **awaiting approval**. 30 steps done. **117 tests GREEN, ruff/black clean.** `__realworld__` residue 0 (BR-A13).
    - New: `commonsense_wiki/{linker,cross_world}.py`. Deleted: bundled.py, builder.py(WikiBuilder), examples/realworld_sample, REALWORLD_WORLD_ID, build-wiki CLI/endpoint.
    - Models: Knowledge.title(req), WikiDomain enum, WikiPrior(world_id+domains), WikiPriorLink. Orchestrator self-distills per-world priors+links; NPC single-world (BR-A9); CrossWorldWikiExplorer designer-only.
    - Code summary: `construction/unitA-model-wiki/code/code-summary.md`.
  - [x] Unit-B Functional Design — **awaiting approval** (`construction/unitB-ingestion/functional-design/`)
    - Decisions: FD-B Q1=B(type-split: barrier=hint, area=promote)/Q2=A(RegionLevel.TERRAIN)/Q3=A(fuzzy→embed→LLM, non-VLM canonical)/Q4=A+Q&A/Q5=A(augmentation)/Q6=A(terrain x,y).
    - Key finding: LOCATED_IN edge does not exist today (located_in is node-prop only) → Unit-B adds it. case2 promote in ingester; case1 merge in OntologyBuilder (EntityReconciler); leftovers → unconnected_entity_ids → augmentation.
  - [x] Unit-B Code Generation — **awaiting approval**. 20 steps done. **124 tests GREEN, ruff/black clean.**
    - New: `ontology/reconciler.py`(EntityReconciler). RegionLevel.TERRAIN, located_in_edges(LOCATED_IN), terrain classify(barrier=hint/area=Region promote), KnowledgeGraph.unconnected_entity_ids, IssueType.ORPHAN+detect_orphans.
    - Code summary: `construction/unitB-ingestion/code/code-summary.md`.
  - [x] Build & Test — APPROVED. 133 offline GREEN (124 backend + 9 frontend), 82% cov, ruff/black clean. `__realworld__` residue 0.
  - [x] Operations (placeholder) — operations.md updated (build-wiki removed, related-priors workflow, no infra change). **MVP IMPROVEMENTS CYCLE COMPLETE.**
- **Stages to Execute**: Workflow Planning, per-unit Functional Design (A,B), Code Generation (A,B), Build and Test.
- **Stages to Skip**: User Stories, Application Design, Units Generation, NFR-R/NFR-D/Infra (per-unit).


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
