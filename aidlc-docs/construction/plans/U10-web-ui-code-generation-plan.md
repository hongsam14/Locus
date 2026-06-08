# U10 Web UI — Code Generation Plan

Code 위치 = `web/` (React+Vite+TS) + 소규모 백엔드 보강(`locus/`, `api/`). Stories US-7.1~7.3.

## Steps
- [ ] **Step 1 — Region.position (U1 additive)**: `locus/models/graph.py` `Coord{x,y in [0,1]}` + `Region.position: Coord | None`. graph_mapping 정/역(position JSON round-trip) — 자동(_flatten/_json_field). 회귀 확인.
- [ ] **Step 2 — coords in ingestion (U2 additive)**: `ExtractedRegion.position{x,y}?`(0~1); `mapping.to_region`이 position 전달.
  - **구조화맵**: Locus Map JSON `x`/`y`(또는 `position`) → position; GeoJSON geometry → centroid 정규화(bbox) → position(순수 `geojson_centroid`/`normalize`).
  - **지도 이미지(VLM)**: `MapImageIngestor`의 추출 프롬프트(`_STRUCT_SYSTEM`)가 "각 지역의 지도상 상대 위치(0,0=좌상단 ~ 1,1=우하단)를 추정해 position에 채우라"고 요청 → ExtractedRegion.position → Region.position(저신뢰 추정, UI 드래그로 보정 가능).
- [ ] **Step 3 — export endpoint**: `GET /api/authoring/worlds/{world_id}/export` → Exporter.export_world (state의 exporter 사용).
- [ ] **Step 4 — Vite scaffold** (`web/`): package.json, vite.config.ts(proxy /api→8000), tsconfig, index.html, src/main.tsx, vitest 설정(jsdom).
- [ ] **Step 5 — api client** (`web/src/api.ts`): fetch 래퍼(export/knowledge/diff/build/wiki/upsert/delete/augment).
- [ ] **Step 6 — pure helpers** (`web/src/layout.ts` autoLayout, `web/src/viz.ts` edgeStyle/markerPos) + types(`web/src/types.ts`).
- [ ] **Step 7 — components**: `MapOverlay.tsx`(+RegionMarker/ConnectionLine, 드래그→onMove), `RegionPanel.tsx`(지식 조회·편집), `AugmentPanel.tsx`(세션 Q&A·revert), `Toolbar.tsx`, `App.tsx`. data-testid 부여.
- [ ] **Step 8 — Tests** (`web/src/__tests__/`): layout/viz 순수(vitest); MapOverlay 렌더(마커/연결선 수, 드래그 onMove); RegionPanel(mock api→지식); AugmentPanel(start→answer). 
- [ ] **Step 9 — verify**: `npm install` + `npm test`(vitest) + `npm run build`(tsc+vite). Python 회귀 pytest(Step1~3).
- [ ] **Step 10 — Docs**: `construction/U10-web-ui/code/code-gen-summary.md`.

## Story Coverage
US-7.1(시각화)→Step6,7 · US-7.2(편집)→Step3,5,7 · US-7.3(UI 보강)→Step5,7(AugmentPanel).

## Notes
- 백엔드 보강(Step1~3)은 pytest 회귀. 프론트는 vitest. `npm install` 네트워크 필요 — 실패 시 코드는 생성하되 검증은 문서화.
