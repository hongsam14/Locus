# S3 (Web UI) — Build & Test Summary

Cycle: Rumor Distortion / Game Session, Phase 1 (final unit). Date 2026-06-15. Scope: FR-R6 + dead buildWiki cleanup.

## Build Status
- **Backend**: 1 additive read route (`GET …/rumors`). 12 session routes total. No new dependency.
- **Frontend**: `web/` React+Vite+TS — `tsc -b && vite build` → `web/dist/` (157 kB / 50 kB gzip). No new npm dependency. New components SessionBar + SessionPanel.
- **Artifacts**: `web/dist/`, updated `web/src/*`, `api/routers/session.py`, `locus/session/game_master.py`.

## Test Execution Summary

### Unit / Component Tests (offline)
- **Backend (pytest)**: **177 passed**, ruff ✅ black ✅.
- **Frontend (vitest)**: **14 passed** (was 9; +5 S3), `tsc` clean, `vite build` OK.
- **Total**: **191** (177 backend + 14 frontend).
- **S3 frontend tests**: SessionBar (list + create→onSelect); SessionPanel (rumor list + PROMOTED badge + generate; advance-turn; closed-session controls disabled); RegionPanel (sessionId → sessionKnowledge, canonical not called).
- **Status**: ✅ PASS

### Integration Tests (live — operator-run, full UI)
**Status**: ⏳ PENDING operator run.

## Live Scenarios (operator)
Prereq: `docker compose up -d` (+postgres) · `.env` w/ `OPENAI_API_KEY` · `uvicorn api.main:app` · `cd web && npm run dev`. Build a world first.

- **S3-A — Session lifecycle**: SessionBar → New Session (appears in dropdown, status open/turn 0); Close → status closed, write controls disabled. [FR-R6.1]
- **S3-B — Generate + display (GameMaster)**: select a region on the map → SessionPanel shows region controls; click **Generate rumors** → rumor list with statement·distortion·support·(badge). [FR-R6.2, Q2]
- **S3-C — Support + promotion**: drag a rumor's support slider ≥0.6 → release (PUT); **Advance Turn** → PROMOTED badge appears; timeline shows promote/advance entries. Drop support, advance → badge clears. [FR-R6.3, FR-R3]
- **S3-D — Distortion control**: drag region distortion slider → release; subsequent Generate produces a stronger/weaker chain. [FR-R2.5]
- **S3-E — Session NPC view**: with a session selected, RegionPanel shows promoted rumors direct-like + rumors, no propagated/auto-rumor; deselect session → canonical view returns. [FR-R5.1, Q3]
- **S3-F — Browse history**: select a past (closed) session in the dropdown → its timeline + rumors are viewable read-only. [FR-R6.4]
- **S3-G — buildWiki gone**: no "Build Wiki" button; no `wiki/build` call. [FR-R6.5]
- **S3-H — graceful**: any API error surfaces as an inline message, app stays usable. [NFR-R4]

## Requirement coverage
- FR-R6.1 → SessionBar (S3-A). FR-R6.2 → SessionPanel generate (S3-B). FR-R6.3 → support slider + promotion (S3-C). FR-R6.4 → timeline + session dropdown (S3-F). FR-R6.5 → buildWiki removed (S3-G).
- NFR-R6 regression → backend 177 + frontend 14 GREEN, tsc/build clean.

## Overall Status
✅ **Offline GREEN (191 total: 177 backend + 14 frontend), tsc/vite build clean, ruff/black clean.** Live full-UI scenarios pending operator run.

**Rumor / Game-Session Phase 1 — CODE COMPLETE (S1 + S2 + S3).** Phase 2 (Event interaction) deferred.
