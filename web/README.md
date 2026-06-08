# Locus Web UI (U10)

React + Vite + TypeScript review/edit UI: map-overlay topology, region knowledge, in-UI augmentation Q&A. Consumes the Locus serving + authoring API.

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

## Map overlay
- Region markers are placed by `region.position` (normalized 0..1), derived from the map
  input (GeoJSON centroid / Locus Map x,y / VLM estimate) or auto-laid-out on a circle.
- Drag a marker to reposition → persisted via `PUT /api/authoring/.../regions/{id}`.
- Pick a background map image (top toolbar) to overlay the graph on your world map.
- Connection lines: width/opacity by weight; `blocked` = red dashed (e.g. mountain barrier).
