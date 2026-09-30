# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Locus** is a system that ingests a game world's terrain, cultural, and conceptual data (unstructured notes, world maps, concept art) and automatically constructs (1) a **connection-network topology** mapping regions of the map and (2) a region-scoped **knowledge graph / ontology** of "Spatial Knowledge" — the locally-shared consensus (places, people, events, customs, rumors) that an NPC living in a given region would know. The output is consumed by downstream NPC dialogue/behavior systems (e.g. LLM-based NPCs) as a context source, replacing hand-written scripts.

## Status

AI-DLC build complete through **UX Improvement** (2026-08-11); **Purpose Restructure** cycle in progress (2026-09): U1 경계 재정리 + U2 World File·캐노니컬 기반 + **U4 플레이어 모드** + **U5 NPC 대화·언어** done (five boundaries, World File v1, WorldCache, LLM-free demo; player sessions, movement along connections, action-driven turns with LLM budget / per-region caps / one-run-per-session guard, `/play/:sessionId` screen; NPC dialogue scoped to what that region's NPC knows — one LLM call per line, no hearsay — plus a ko/en display language (`?lang=`, `SUPPORTED_LANGS`) and translation purge on regenerate / world replace). **599 offline tests GREEN** (543 pytest backend + 56 vitest frontend); live Neo4j/OpenSearch/PostgreSQL/OpenAI integration is operator-run (see `aidlc-docs/construction/**/`).

**UX Improvement** adds: (1) **Localization** — LLM ko translation of session content + canonical Knowledge cached in a PostgreSQL `translations` table (`locus/localization/`), read-non-blocking (cache-only reads + background warm), en+ko response fields with a per-item original toggle; (2) **Frontend** — Tailwind v4 "Doodly" (paper+ink) design system with self-hosted Gaegu Korean font + `web/src/ui/` primitives, Korean UI labels + timeline i18n; (3) **Rumor UX** — bulk generate (empty regions only, parallel + progress), confirm-gated regenerate that **preserves promoted rumors** (canonical-only reseed), and per-region turn-change notifications from `TurnResult.region_changes`.

The game-session layer (PostgreSQL) over the static canonical world provides GameMaster turns, LLM rumor distortion (degree chains), support/promotion, timeline, and a session NPC query. **Phase 2 adds Events** (`SessionEvent`, category/magnitude/lifecycle) that **dynamically evolve per-region distortion** each turn: deterministic delta + topology-decayed propagation, persistent accumulation / one_shot, resolve-restore, support auto-evolution, and LLM event suggestion (suggest→approve) — see `locus/play/event/{dynamics,suggester}.py`, the single-responsibility services `locus/play/{rumor/service,event/service,distortion_service,turn/advancer}.py` wired by `locus/play/wiring.py` (no facade; routers take the `PlayContainer`), `api/routers/{play,gm}.py`, and `web/` SessionPanel. Phase 3 (rumor→region feedback loop, event-to-event interaction) deferred.

## Tech Stack & Layout
- **Backend**: Python 3.11+, Pydantic v2, FastAPI, Neo4j (graph) + OpenSearch (hybrid search) for the canonical world, **PostgreSQL (SQLAlchemy) for the game-session layer**, LangChain/LangGraph, OpenAI (provider-abstracted). Docker Compose.
- **Frontend**: `web/` — React + Vite + TypeScript (map-overlay topology, edit, augmentation Q&A, **game sessions: SessionBar + SessionPanel GameMaster hub**, **player screen `features/play/` at `/play/:sessionId`** with NpcList + DialoguePanel; ko/en dictionaries + `LangToggle` in `src/i18n.ts`).
- **Code**: `locus/` is five boundaries — `shared/` (models, config incl. `tuning.py`, llm, storage ports/adapters, `wiring.py`) · `knowledge/` (consensus, propagation, loader, query) · `world/` (ingestion, topology, ontology, wiki, augmentation, `build.py` WorldBuilder, `editor.py`, `worldfile/`, `demo/`) · `play/` (models, ports, storage incl. unit of work, session/distortion services, `rumor/`, `event/`, `turn/` (advancer = single turn entry point, guard, executor, budget, summary), `player/` (movement rules + PlayService), `npc/` (pure `scope.py` + `prompts.py`, `dialogue.py` NpcDialogueService), `region_knowledge.py` (`region_sources` = the one consensus resolve per region); `gm/` reserved) · `localization/` (translation cache + service). Each boundary exposes `assemble_<boundary>()` + a typed container in its `wiring.py`. `api/` is the composition root (`deps.py`, `errors.py`, `schemas.py` DTOs with `*_ko`, routers `world`/`knowledge`/`play`/`gm` under `/api/<name>`). `web/` (React + react-router: `/editor/:worldId`, `/gm/:sessionId`, `/play`) · `tests/<boundary>/` + `tests/test_boundaries.py` (import-matrix guard).
- **CLI**: `locus init-schema [--world] [--play] [--localization] | world build|export|import|demo|list` (aliases `build-world`, `export`). `world demo --name aldermoor --world <id>` loads the packaged World File with no LLM; `world build` needs an LLM and self-distills the world's WikiPriors; replacing a world with open sessions needs `--force`.

## Build / Test / Run
```bash
pip install -e ".[dev]" && pytest              # backend (offline, mocked)
cd web && npm install && npm test              # frontend (vitest)
cp env.example .env                            # REQUIRED: set NEO4J_PASSWORD, SESSION_DB_PASSWORD (no insecure defaults)
docker compose up -d neo4j opensearch postgres # deps for live use (postgres = session layer)
locus init-schema && locus build-world --world demo --demo
uvicorn api.main:app --port 8000               # API ; cd web && npm run dev for UI
```

## Conventions
- All external I/O behind ports (GraphRepository/SearchRepository/LLMProvider/PlayRepository/TranslationStore) — mockable; offline tests mock them.
- Boundary imports: shared ← knowledge ← {world, play}; localization → shared only; `locus/**` never imports `api`; play never imports localization (translations are applied in `api/schemas.py`). Enforced by `tests/test_boundaries.py`.
- `world_id` partitions every graph; each world holds its own Common-sense Wiki (WikiPriors). Cross-world prior reference is a designer-only, read-through search by shared domain tags (NPC build/query stays single-world).
- ruff + black (line 100); PBT (Partial) via hypothesis on pure functions/serialization.

## AI-DLC

This project follows the AWS AI-DLC (AI-Driven Development Life Cycle) methodology.

When the user invokes AI-DLC or requests software development work, read and follow
`.aidlc/aws-aidlc-rules/core-workflow.md` to start/continue the workflow.

- Workflow rules: `.aidlc/aws-aidlc-rules/core-workflow.md`
- Rule details: `.aidlc/aws-aidlc-rule-details/`
- State tracking: `aidlc-docs/aidlc-state.md` (read FIRST to resume)
- Audit log: `aidlc-docs/audit.md` (append-only; never overwrite)
- All design/planning artifacts live under `aidlc-docs/`; application code lives at the workspace root (never inside `aidlc-docs/`).
- **Plan Review** (ported from the telemetry-projects AI-DLC reviewer protocol): before a reviewed stage's approval gate, an independent reviewer sub-agent reviews the plan/design artifact and its findings are quoted at the gate. Rule: `.aidlc/aws-aidlc-rule-details/common/plan-review.md` (stage table, flow, record format, Review brief); personas: `common/reviewers/{architecture-reviewer,product-lead-reviewer}.md`; Claude Code agents: `.claude/agents/aidlc-{architecture,product-lead}-reviewer.md` (tracked; `.claude/agents/` is un-ignored). Review records: `<artifact dir>/reviews/<key>-review-NN.md`.
