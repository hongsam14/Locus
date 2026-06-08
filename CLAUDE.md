# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Locus** is a system that ingests a game world's terrain, cultural, and conceptual data (unstructured notes, world maps, concept art) and automatically constructs (1) a **connection-network topology** mapping regions of the map and (2) a region-scoped **knowledge graph / ontology** of "Spatial Knowledge" — the locally-shared consensus (places, people, events, customs, rumors) that an NPC living in a given region would know. The output is consumed by downstream NPC dialogue/behavior systems (e.g. LLM-based NPCs) as a context source, replacing hand-written scripts.

## Status

AI-DLC build complete (2026-06-08) — all 10 units across 2 cycles. **117 offline tests GREEN** (108 pytest backend + 9 vitest frontend); live Neo4j/OpenSearch/OpenAI integration is operator-run (see `aidlc-docs/construction/build-and-test/`).

## Tech Stack & Layout
- **Backend**: Python 3.11+, Pydantic v2, FastAPI, Neo4j (graph) + OpenSearch (hybrid search), LangChain/LangGraph, OpenAI (provider-abstracted). Docker Compose.
- **Frontend**: `web/` — React + Vite + TypeScript (map-overlay topology, edit, augmentation Q&A).
- **Code**: `locus/` (core package: models, config, llm, storage, ingestion, topology, ontology, consensus, commonsense_wiki, query, augmentation, services) · `api/` (FastAPI serving + authoring routers) · `web/` (UI) · `tests/`.
- **CLI**: `locus init-schema | build-wiki | build-world [--demo] | export`.

## Build / Test / Run
```bash
pip install -e ".[dev]" && pytest          # backend (offline, mocked)
cd web && npm install && npm test          # frontend (vitest)
docker-compose up -d neo4j opensearch      # deps for live use
locus init-schema && locus build-wiki && locus build-world --world demo --demo
uvicorn api.main:app --port 8000           # API ; cd web && npm run dev for UI
```

## Conventions
- All external I/O behind ports (GraphRepository/SearchRepository/LLMProvider) — mockable; offline tests mock them.
- `world_id` partitions every graph; real-world Common-sense Wiki uses reserved id `__realworld__`.
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
