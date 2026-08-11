# S3 (Web UI) — Code Summary

Executed 2026-06-15. **Backend 177 pytest GREEN · Frontend 14 vitest GREEN · tsc + vite build clean · ruff/black clean.** New: SessionBar + SessionPanel (GameMaster hub). dead `buildWiki` removed.

## Backend (additive, read-only)
- **`locus/session/game_master.py`** — `GameMasterService.list_rumors(session_id, region_id)` (validates session → 404; allowed on closed sessions).
- **`api/routers/session.py`** — `GET /api/session/sessions/{sid}/regions/{rid}/rumors -> list[SessionRumor]`. 12 session routes total now.

## Frontend (`web/src/`)
- **`types.ts`** — GameSession / SessionRumor / RegionDistortion / TimelineEntry / TurnResult.
- **`api.ts`** — session methods: listSessions / startSession / closeSession / getTimeline / listRumors / generateRumors / regenRumors / setSupport / setDistortion / advanceTurn / sessionKnowledge. **`buildWiki` removed**.
- **`SessionBar.tsx`** (new) — session dropdown + New + Close + status/turn; reloads on world change, drops selection (BR-S3-2).
- **`SessionPanel.tsx`** (new, GameMaster hub, Q2) — Advance Turn + timeline + (for map-selected region) distortion slider, Generate/Regenerate, rumor list with support slider + PROMOTED badge. All write controls disabled on closed sessions.
- **`RegionPanel.tsx`** (mod) — `sessionId` prop → `sessionKnowledge` (session NPC view) when set, else canonical `regionKnowledge` (Q3).
- **`App.tsx`** (mod) — `session` state, `<SessionBar>` + `<SessionPanel>` (when session) + `RegionPanel sessionId=…`; `buildWiki` removed.
- **`Toolbar.tsx`** (mod) — `onBuildWiki` prop + Build Wiki button removed.

## Tests
- **Backend** (`tests/session/test_session_api.py`): GET rumors list (3) + 404.
- **Frontend** (`web/src/__tests__/components.test.tsx`): SessionBar (list + New→onSelect), SessionPanel (rumors + PROMOTED badge + generate; advance-turn; closed-session disabled), RegionPanel (sessionId→sessionKnowledge, canonical not called). 14 vitest total.

## Verification
- Backend **177 pytest GREEN**, ruff/black clean. Frontend **14 vitest GREEN**, tsc clean, vite build OK (157 kB). `buildWiki`/`wiki/build` residue 0.

## Cycle status
**S3 = final unit of the Rumor / Game-Session Phase-1 cycle.** With S1 (foundation+infra) + S2 (rumor engine) + S3 (web), Phase 1 is code-complete. Phase 2 (Event interaction → dynamic distortion) deferred.
