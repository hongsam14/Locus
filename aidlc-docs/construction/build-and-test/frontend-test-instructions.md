# Frontend Build & Test — Locus Web UI (U10)

## Prerequisites
- Node 18+ (tested v20.19) + npm 9.

## Build / test
```bash
cd web
npm install
npm test            # vitest (jsdom): pure layout/viz + component tests (api mocked)
npm run build       # tsc type-check + vite build -> web/dist/
npm run dev         # dev server :5173, proxies /api -> :8000 (run backend separately)
```

## Expected (current)
- **9 vitest tests pass** (pure.test.ts ×5, components.test.tsx ×4).
- `tsc -b` clean; `vite build` produces `web/dist/`.

## Coverage
- Pure: `autoLayout` (position vs circular fallback, bounds), `edgeStyle`/`toPixels`.
- Components (api mocked): `MapOverlay` (marker per region, line per connection, select on click), `RegionPanel` (renders knowledge), `AugmentPanel` (start → questions).

## Manual UI walkthrough (with backend up)
1. `uvicorn api.main:app --port 8000` (needs Neo4j/OpenSearch/OPENAI per integration-test-instructions).
2. `cd web && npm run dev` → open http://localhost:5173.
3. Set world id (e.g. `aldermoor`) → **Build World (demo)** → **Load**.
4. Topology overlay renders (Riverton–Highcrag `blocked` = red dashed). Optionally pick a map image → drag markers (persists position).
5. Click a region → RegionPanel shows knowledge (direct/global etc.); delete an item.
6. AugmentPanel → **Start session** → answer questions → **Revert last**.
