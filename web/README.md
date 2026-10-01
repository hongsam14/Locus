# Locus Web UI

React + Vite + TypeScript UI for the Locus API: the home screen (demo cards and the world list),
the world editor, the GM hub and the player screen.

## Run
```bash
cd web
npm ci             # the lock as committed (Node 22)
npm run dev        # http://localhost:5173 (proxies /api -> http://localhost:8000)
# (start the backend separately: uvicorn api.main:app --port 8000 --workers 1)
```
In compose, the `web` service builds this image (`node:22-alpine`, `npm ci`) and serves it from
nginx on :3000, proxying `/api` to the app.

## Test / build
```bash
npm test           # vitest (jsdom) — pure layout/viz + component tests (api mocked)
npm run build      # tsc type-check + vite production build -> dist/
```

## Screens
- `/` — the home screen (`routes/HomePage.tsx`):
  - **Demo cards** (`features/home/DemoCards`, `DemoCard`): one per demo in the server's manifest
    (`GET /api/world/demos` — no demo name in this code). [Play now] loads the demo if it is not
    there (asking before it replaces one, then before it closes open sessions), starts a session at
    the demo's start region and opens the player screen; [Open in editor] opens it.
  - The world list: each world's regions and open sessions, edit, start a player session, build
    from sources.
- `/editor/:worldId` — the world editor (`features/editor/`), below.
- `/gm/:sessionId` — the GameMaster hub (`features/gm/`).
- `/play/:sessionId` — the player screen (`features/play/`).

## Without an LLM key
`src/capabilities.ts` reads `GET /api/capabilities` once. When the server has no LLM, the home,
editor and GM screens show one line (`ui/LlmNotice`) and the LLM buttons (build, NPC drafts, event
suggestion, rumor generate/regenerate) are off with "LLM 키가 필요합니다". A failed read turns
nothing off; a 503 naming the provider shows the same words.

## GM hub
- **Seed panel** (`features/gm/SeedPanel`): the world's event seeds with region, category and size;
  [Start] makes one an ACTIVE event (no LLM); a seed whose event still runs shows "running".
- Manual turn, events, distortion, rumors, timeline and deeds panels; the player strip and the
  world-state overlay on the map.

## World editor
- **Map** (`MapCanvas`): select tool picks a region or a connection; drag a marker more than
  4px to move it (`PUT …/regions/{id}`); the region tool adds a region where you click; the
  connection tool joins two regions with a kind and weight. A background image overlays the map.
- **Inspector** (`RegionInspector`): the region's fields, its connections, its knowledge and
  scopes, and NPCs (with LLM drafts). Deleting a region asks first; the server
  refuses (409) while an open session's player stands there and names those sessions.
- **Side tabs**: unscoped knowledge, augmentation Q&A (answer, ignore, undo latest-first),
  the wiki priors used as evidence.
- **Bar** (`WorldFileBar`): save the World File, load one (replaces the world after a yes;
  closing open sessions needs a second yes — `useReplaceConfirm` in `api/http.ts`), build from
  sources, and the sessions band (the open ones, or a session start when there are none).
- The connection tool on a pair that already has the chosen kind edits that connection (its
  grounds and prior stay); the build panel's concept-art field carries an "in progress" badge.
- Connection lines: width/opacity by weight; `blocked` = red dashed (e.g. mountain barrier).
