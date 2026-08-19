# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Locus** is a system that ingests a game world's terrain, cultural, and conceptual data (unstructured notes, world maps, concept art) and automatically constructs (1) a **connection-network topology** mapping regions of the map and (2) a region-scoped **knowledge graph / ontology** of "Spatial Knowledge" — the locally-shared consensus (places, people, events, customs, rumors) that an NPC living in a given region would know. The output is consumed by downstream NPC dialogue/behavior systems (e.g. LLM-based NPCs) as a context source, replacing hand-written scripts.

## Status

AI-DLC build complete. MVP (10 units) + MVP-improvements + **Rumor / Game-Session Phase 1** (S1+S2+S3) + **Phase 2** (P1+P2+P3) + **Rumor Dynamics & Hardening** (U-H1+U-H2) + **UX Improvement** (X1 Localization Backend + X2 Frontend Design System + X3 Frontend UX Features, 2026-08-11). **305 offline tests GREEN** (281 pytest backend + 24 vitest frontend); live Neo4j/OpenSearch/PostgreSQL/OpenAI integration is operator-run (see `aidlc-docs/construction/**/build-and-test/`).

**UX Improvement** adds: (1) **Localization** — LLM ko translation of session content + canonical Knowledge cached in a PostgreSQL `translations` table (`locus/translation/`), read-non-blocking (cache-only reads + background warm), en+ko response fields with a per-item original toggle; (2) **Frontend** — Tailwind v4 "Doodly" (paper+ink) design system with self-hosted Gaegu Korean font + `web/src/ui/` primitives, Korean UI labels + timeline i18n; (3) **Rumor UX** — bulk generate (empty regions only, parallel + progress), confirm-gated regenerate that **preserves promoted rumors** (canonical-only reseed), and per-region turn-change notifications from `TurnResult.region_changes`.

The game-session layer (PostgreSQL) over the static canonical world provides GameMaster turns, LLM rumor distortion (degree chains), support/promotion, timeline, and a session NPC query. **Phase 2 adds Events** (`SessionEvent`, category/magnitude/lifecycle) that **dynamically evolve per-region distortion** each turn: deterministic delta + topology-decayed propagation, persistent accumulation / one_shot, resolve-restore, support auto-evolution, and LLM event suggestion (suggest→approve) — see `locus/session/{dynamics,event_suggester}.py`, the single-responsibility services `locus/session/{rumor_service,event_service,distortion_service,turn}.py` composed by the `game_master.py` coordinator (DI), `api/routers/session.py`, and `web/` SessionPanel. Phase 3 (rumor→region feedback loop, event-to-event interaction) deferred.

## Tech Stack & Layout
- **Backend**: Python 3.11+, Pydantic v2, FastAPI, Neo4j (graph) + OpenSearch (hybrid search) for the canonical world, **PostgreSQL (SQLAlchemy) for the game-session layer**, LangChain/LangGraph, OpenAI (provider-abstracted). Docker Compose.
- **Frontend**: `web/` — React + Vite + TypeScript (map-overlay topology, edit, augmentation Q&A, **game sessions: SessionBar + SessionPanel GameMaster hub**).
- **Code**: `locus/` (core package: models, config, llm, storage, ingestion, topology, ontology, consensus, commonsense_wiki, query, augmentation, services, **session**) · `api/` (FastAPI serving + authoring + **session** routers) · `web/` (UI) · `tests/`.
- **CLI**: `locus init-schema | build-world [--demo] | export`. (`init-schema` also creates the PostgreSQL session tables; each world self-distills its own WikiPriors during `build-world`.)

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
- All external I/O behind ports (GraphRepository/SearchRepository/LLMProvider) — mockable; offline tests mock them.
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
