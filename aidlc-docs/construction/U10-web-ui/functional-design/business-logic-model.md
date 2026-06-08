# U10 Web UI — Logic & Flows

## API 클라이언트 (`web/src/api.ts`)
- 얇은 fetch 래퍼: `getExport(worldId)`, `getRegionKnowledge(worldId, regionId, includeRumors)`, `diff(...)`, `buildWorldDemo(worldId)`, `buildWiki()`, `upsertRegion(worldId, region)`, `upsertKnowledge(worldId, k)`, `deleteNode(worldId, id)`, `startAugment(worldId)`, `submitAnswer(sid, answer)`, `revertAugment(sid, changeId)`.
- base URL = `import.meta.env.VITE_API_URL || ""`(프록시/동일 오리진).

## 신규 백엔드 엔드포인트 (U10 추가, 최소)
- `GET /api/authoring/worlds/{world_id}/export` → `Exporter.export_world` dict(regions+connections+knowledge+scopes). UI 토폴로지 렌더에 사용. (app state에 `exporter` DI 이미 존재.)

## 페이지 흐름
1. **빌드**: world_id 입력 → "Build World(데모)" → `POST .../build` → 완료 후 `GET export` 로 그래프 로드.
2. **토폴로지 뷰**: export의 regions/connections → MapOverlay 렌더. 마커 드래그 → `position` 갱신 → `PUT region`.
3. **지역 선택** → RegionPanel: `GET region knowledge` → direct/inherited/global/propagated/rumors 표시. 지식 편집 → `PUT knowledge` / 삭제 → `DELETE node`.
4. **보강**: AugmentPanel "Start" → `POST augment/session` → 질문 표시 → 답변(action) → `POST answer`(ChangeSet) → 수렴까지 반복. "Revert" → `POST revert`.

## 자동 레이아웃 (`web/src/layout.ts`, 순수)
- `autoLayout(regions) -> {id:{x,y}}`: position 있으면 사용, 없으면 원형/그리드 배치(0~1). 결정적 → 테스트.

## 시각화 헬퍼 (`web/src/viz.ts`, 순수)
- `edgeStyle(kind, weight) -> {width, opacity, color, dashed}`; `markerPos(region, layout, size)`.

## 테스트 (vitest + RTL, FD10-Q5=A)
- `layout.ts`/`viz.ts` 순수 테스트.
- 컴포넌트: MapOverlay 렌더(마커/연결선 수), RegionPanel(mock api → 지식 표시), AugmentPanel(start→answer 흐름). api는 mock.

## 빌드/실행
- `web/`: Vite. `npm install`, `npm run dev`(5173), `npm run build`, `npm test`(vitest).
- API 프록시: vite.config `server.proxy /api -> localhost:8000`.
