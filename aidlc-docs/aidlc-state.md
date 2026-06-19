# AI-DLC State Tracking

## Project Information
- **Project Name**: Locus — Spatial Knowledge Graph Builder for Game Worlds
- **Project Type**: Greenfield
- **Start Date**: 2026-06-07T10:54:58Z
- **Current Stage**: ✅ **RUMOR / GAME-SESSION PHASE 2 COMPLETE 2026-06-19** (P1 Event Foundation + P2 Dynamic Engine + P3 Web UI). 236 offline tests GREEN (219 backend + 17 frontend, 85% cov). Operations doc + CLAUDE.md updated. Phase 3 (rumor→region feedback, event-to-event interaction) deferred. Prior: Phase 1 (S1+S2+S3) COMPLETE 2026-06-15.

## Rumor / Game-Session PHASE 2 Cycle (2026-06-18) — Event + dynamic distortion
- **Concept**: Deferred Phase 2 — **Event** entity + Event interaction → **dynamic distortion evolution** (per-region degree changes over turns), optional rumor-feedback loop + support auto-evolution. Additive on PostgreSQL session layer; canonical (Neo4j/OpenSearch) immutable; NPC query rule unchanged (TBD by Q11).
- **Scope ref**: `rumor-distortion-requirements.md` §7 Out of Scope (Event+interaction, support auto-increase), §4 FR-R4.3 (Event=Phase 2).
- **Answers**: Q1=A(new SessionEvent)/Q2=B(category enum)/Q3=C(single+topology propagation)/Q4=C(manual+LLM)/Q5=C(deterministic+propagation)/Q6=A(advance_turn batch)/Q7=B(auto rumor update in turn)/Q8=B(rumor-feedback=Phase 3)/Q9=B(support auto evolve)/Q10=X(lifecycle by category)/Q11=A(NPC rule unchanged)/Q12=A(full UI)/Q13=A(additive port). Clarif: CL1.1=X(persistent until resolve; resolve=event)/CL1.2=A(per-turn cumulative delta, restore on resolve)/CL1.3=A(category-default lifecycle, overridable)/CL2.1=A(suggest-then-approve)/CL2.2=B(LLM proposes each turn)/CL3.1=B(preserve rumors+support, add/update)/CL3.2=A(event-region reinforce, else decay)/CL4.1=A(only primary regenerates).
- **Stage progress**: [x] Workspace Detection (brownfield resume) · [x] Requirements Analysis — `inception/requirements/rumor-phase2-{verification-questions,clarification-questions,requirements}.md`. **APPROVED?** awaiting approval. FR-P1..P8 + NFR-P1..P6.
- **Triggers (proposed)**: User Stories SKIP · Application Design EXECUTE (EventEngine/distortion+support evolution/LLM EventSuggester/GameMasterService ext) · Units Generation EXECUTE (backend→API→web) · Infrastructure Design SKIP (no new infra, additive session_events table only) · NFR light.
- **Workflow Planning (2026-06-19)**: APPROVED. `inception/plans/rumor-phase2-execution-plan.md`. EXECUTE: Workflow Planning, Application Design, Units Generation, per-unit Functional Design + NFR-light + Code Gen, Build&Test. SKIP: User Stories, Infrastructure Design. Risk Medium / Rollback Moderate / Testing Moderate. Units: **P1 Event Foundation → P2 Dynamic Engine → P3 Web UI**.
- **Application Design (2026-06-19)**: APPROVED. answers **AD-P Q1=A**(dynamics.py pure module)/**Q2=A**(event_suggester.py EventSuggester)/**Q3=A**(suggest→approve→advance separate endpoints)/**Q4=A**(status=suggested|active|resolved, suggestions persisted)/**Q5=A**(symmetric multi-region accumulated restore)/**Q6=A**(keep P1→P2→P3). Components C1 SessionEvent / C2 enums+mapping+TimelineKind ext / C3 dynamics(pure) / C4 EventSuggester(LLM) / C5 GameMasterService ext(advance_turn sequence) / C6 SessionRepository Event CRUD / C7 session API routes / C8 web. Artifacts: `inception/application-design/rumor-phase2/{components,component-methods,services,component-dependency,application-design}.md`.
- **Units Generation (2026-06-19)**: APPROVED. answer **UOW-P Q1=A**(P1 includes manual Event CRUD API). Units **P1 Event Foundation**(C1/C2/C6/C7-manual, FR-P1/P2.1/P2.4/P6.1) → **P2 Dynamic Engine**(C3/C4/C5/C7-suggest+advance, FR-P2.2/2.3/P3/P4/P5/P6.2/P7) → **P3 Web UI**(C8, FR-P8). Sequential. All FR-P*/NFR-P* assigned (0 unassigned). Artifacts: `inception/application-design/rumor-phase2/{unit-of-work,unit-of-work-dependency,unit-of-work-story-map}.md`. **INCEPTION COMPLETE.**
- **P1 Functional Design (2026-06-19)**: answers **FD-P1 Q1=A**(6 categories WAR/PLAGUE/POLITICS=persistent, DISASTER/FESTIVAL/DISCOVERY=one_shot)/**Q2=A**(create validates region→404)/**Q3=A**(Phase 1 field/persistence conventions)/**Q4=A**(P1 resolve=state transition only, restore in P2). Artifacts: `construction/P1-event-foundation/functional-design/{domain-entities,business-logic-model,business-rules}.md` (BR-P1-1..14). SessionEvent + EventCategory/Lifecycle/Status enums + CATEGORY_DEFAULT_LIFECYCLE + TimelineKind(EVENT_*) + session_events table. APPROVED. NFR for P1 = light (`construction/P1-event-foundation/nfr/nfr-light.md`).
- **P1 Code Generation (2026-06-19)**: plan `construction/plans/P1-event-foundation-code-generation-plan.md` (12 steps) APPROVED & EXECUTED. Modified enums.py(SESSION_EVENT)/session/models.py(SessionEvent+enums+TimelineKind)/repository.py/memory_repo.py/postgres_session_repo.py(session_events)/game_master.py(create/list/resolve/discard event+_require_region)/api/routers/session.py(EventCreate+4 routes)/session/__init__.py. New tests/session/test_events.py + extended repo-contract/postgres/api tests. **194 backend pytest GREEN (177+17), ruff/black/compileall clean**, 4 new event routes; canonical/Phase 1 regression 0. Code summary: `construction/P1-event-foundation/code/code-summary.md`. **P1 UNIT CODE APPROVED.** Note: API magnitude clamps (not 422) per support/distortion convention.
- **P2 Functional Design (2026-06-19)**: answers **FD-P2 Q1=A**(distortion_delta=magnitude*MAX_EVENT_DELTA, 0.3)/**Q2=A**(propagate min_weight 0.15 = consensus rumor_min)/**Q3=A**(one_shot permanent bump, no baseline decay; only persistent restores on resolve)/**Q4=A**(support influenced +0.1 / others -0.05 → promotion.evaluate 0.6)/**Q5=A**(primary-region rumors append, preserve existing+support; neighbors distortion-only)/**Q6=A**(suggest_events n, graceful [], persisted SUGGESTED). Artifacts: `construction/P2-dynamic-engine/functional-design/{domain-entities,business-logic-model,business-rules}.md` (BR-P2-1..16). New: dynamics.py pure fns + constants, EventDraft, TurnResult +applied_event_ids/+resolved_event_ids, EventSuggester, advance_turn 6-step sequence, resolve restore, suggest/approve, main.py optional suggester inject. APPROVED. (FD-P2 all-A; rumor count grows per turn per Q5=A.)
- **P2 Code Generation (2026-06-19)**: plan `construction/plans/P2-dynamic-engine-code-generation-plan.md` (11 steps) APPROVED & EXECUTED. New `locus/session/dynamics.py`(pure+constants MAX_EVENT_DELTA=0.3/PROPAGATE_MIN_WEIGHT=0.15/SUPPORT_REINFORCE=0.1/SUPPORT_DECAY=0.05) + `event_suggester.py`(EventDraft/EventDraftList/EventSuggester graceful). Modified game_master.py(suggester param + TurnResult fields + advance_turn 6-step + _apply_active_events + resolve restore + suggest_events/approve_event), api/routers/session.py(+suggest-events/approve), main.py(EventSuggester inject), session/__init__.py. New tests test_dynamics.py(PBT) + test_advance_turn.py. **218 backend pytest GREEN (194+24), ruff/black/compileall clean**, event routes=5; Phase 1/P1 regression 0; dynamics determinism PBT + LLM graceful verified. Code summary: `construction/P2-dynamic-engine/code/code-summary.md`. **P2 UNIT CODE APPROVED.**
- **P3 Functional Design (2026-06-19)**: answers **FD-P3 Q1=A**(SessionPanel: event form + session-wide list + suggest button)/**Q2=A**(additive GET /sessions/{sid}/distortions + reflect real distortion)/**Q3=A**(session-wide event list)/**Q4=A**(TS types + 7 api methods). Artifacts: `construction/P3-web-ui/functional-design/{domain-entities,frontend-components,business-rules}.md` (BR-P3-1..10). DISCOVERY: additive backend GET distortions endpoint needed (FR-P8.5). APPROVED. NFR light.
- **P3 Code Generation (2026-06-19)**: plan `construction/plans/P3-web-ui-code-generation-plan.md` (8 steps) APPROVED & EXECUTED. Backend: `game_master.list_distortions` + `GET /sessions/{sid}/distortions` + test. Frontend `web/src/`: types(SessionEvent/EventDraft/enums + TurnResult ext), api.ts(+7 methods), SessionPanel(event create form + session-wide event list approve/discard/resolve + suggest button + real distortion + closed disabled), components.test.tsx(mock + 3 tests). **219 backend pytest + 17 frontend vitest GREEN (236 total), ruff/black/compileall + tsc/vite clean**, session route +1; regression 0. Code summary: `construction/P3-web-ui/code/code-summary.md`. **PHASE 2 CODE COMPLETE (P1+P2+P3).**
- **Phase 2 Build & Test (2026-06-19)**: APPROVED. offline GREEN — **236 (219 backend pytest 85% cov + 17 frontend vitest)**, ruff/black/tsc/vite clean, 0 regressions. Live scenarios P2-A..G + P3-H documented (operator-run). Artifacts: `construction/build-and-test/rumor-phase2/{build,unit-test,integration-test,performance-test,build-and-test-summary}.md`.
- **Phase 2 Operations (2026-06-19)**: `operations/operations.md` Phase 2 section (event/turn workflow, no new infra, session_events via init-schema) + CLAUDE.md Status updated. **🎉 RUMOR / GAME-SESSION PHASE 2 COMPLETE.**

## Extension Configuration (Phase 2 — unchanged from prior cycles)
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Phase 2 Requirements Analysis (Security=B) |
| Property-Based Testing | Yes (Partial) | Phase 2 Requirements Analysis (PBT=B) |

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
