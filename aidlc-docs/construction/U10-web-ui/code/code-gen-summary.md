# U10 Web UI — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-7.1 (visualization), US-7.2 (edit), US-7.3 (in-UI augmentation). FR-G.
**Verification**: Frontend **9 vitest tests PASS** + `tsc` type-check clean + `vite build` OK (dist produced). Backend **108 pytest PASS** + ruff/black clean (Region.position additions).

## Created files
### Backend additions (additive)
- `locus/models/graph.py` — `Coord{x,y in [0,1]}` + `Region.position: Coord | None`; `models/__init__` export.
- `locus/storage/graph_mapping.py` — `node_to_region` restores `position` (JSON round-trip).
- `locus/ingestion/schemas.py` — `ExtractedRegion.x/y` (VLM-estimated normalized coords).
- `locus/ingestion/mapping.py` — `to_region` sets `position` from x/y.
- `locus/ingestion/structured_map_ingestor.py` — `_explicit_position` (Locus Map x/y), `geojson_centroid` + `normalize_positions` (GeoJSON geometry → normalized centroid, y inverted), assigns `region.position`.
- `locus/ingestion/map_image_ingestor.py` — VLM prompt asks for per-region normalized x,y.
- `api/routers/authoring.py` — `GET /worlds/{id}/export` (full graph for UI overlay).
- `tests/ingestion/test_positions.py` — explicit/GeoJSON/round-trip position tests.

### Frontend (`web/`, React+Vite+TS)
- Scaffold: `package.json`, `vite.config.ts` (proxy /api, vitest jsdom), `tsconfig.json`, `index.html`, `src/main.tsx`, `src/setupTests.ts`, `.gitignore`, `README.md`.
- `src/types.ts`, `src/api.ts` (fetch client), `src/layout.ts` (`autoLayout`, pure), `src/viz.ts` (`edgeStyle`/`toPixels`, pure).
- Components: `MapOverlay.tsx` (SVG-over-image, draggable markers, weighted/blocked lines), `RegionPanel.tsx` (knowledge query + delete), `AugmentPanel.tsx` (session Q&A + revert), `Toolbar.tsx` (build/load/map-pick), `App.tsx`.
- Tests: `src/__tests__/pure.test.ts`, `src/__tests__/components.test.tsx` (api mocked).

## Key realizations
- **Coordinates on the node** (`Region.position`, FD10-CL1=A): derived from the map — GeoJSON centroid (normalized, north=top), Locus Map x/y, or **VLM estimate** for image maps; UI auto-layout + drag-to-correct fallback (persisted via PUT region).
- **Map overlay**: relative container + background `<img>` + absolute SVG; edges styled by weight (blocked = red dashed → "mountain barrier" reads visually).
- All interactive elements carry stable `data-testid` (automation-friendly).
- Frontend pure helpers unit-tested; components tested with mocked API.

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U10 (consumes existing API; static frontend; dev served by Vite, build → static dist).
