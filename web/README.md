# Locus Web UI

React + Vite + TypeScript UI for the Locus API: the world list, the world editor, the GM hub and
the player screen.

## Run
```bash
cd web
npm install
npm run dev        # http://localhost:5173 (proxies /api -> http://localhost:8000)
# (start the backend separately: uvicorn api.main:app --port 8000)
```

## Test / build
```bash
npm test           # vitest (jsdom) — pure layout/viz + component tests (api mocked)
npm run build      # tsc type-check + vite production build -> dist/
```

## Screens
- `/` — the world list (`routes/HomePage.tsx`): each world's regions and open sessions, edit,
  start a player session; with no world, load the demo or build from sources.
- `/editor/:worldId` — the world editor (`features/editor/`), below.
- `/gm/:sessionId` — the GameMaster hub (`features/gm/`).
- `/play/:sessionId` — the player screen (`features/play/`).

## World editor
- **Map** (`MapCanvas`): select tool picks a region or a connection; drag a marker more than
  4px to move it (`PUT …/regions/{id}`); the region tool adds a region where you click; the
  connection tool joins two regions with a kind and weight. A background image overlays the map.
- **Inspector** (`RegionInspector`): the region's fields, its connections, its knowledge and
  scopes, NPCs (with LLM drafts) and entities. Deleting a region asks first; the server
  refuses (409) while an open session's player stands there and names those sessions.
- **Side tabs**: unscoped knowledge, augmentation Q&A (answer, ignore, undo latest-first),
  the wiki priors used as evidence.
- **Bar** (`WorldFileBar`): save the World File, load one (replaces the world after a yes;
  closing open sessions needs a second yes), build from sources, and the open-sessions band.
- Connection lines: width/opacity by weight; `blocked` = red dashed (e.g. mountain barrier).
