# U10 Web UI — Frontend Components

스택: React + Vite + TypeScript (FD10-Q1=A). 시각화: **지도 위 그래프 오버레이**(FD10-Q2=X). 상태: fetch + hooks (Q4=A). 전 기능 화면(Q3=A).

## 컴포넌트 계층
```
<App>
 ├─ <Toolbar>            world_id 입력/선택, Build World(데모), Build Wiki
 ├─ <MapOverlay>         배경 이미지(파일 선택) + SVG 오버레이(지역 마커 드래그 + 연결선)
 │    ├─ <RegionMarker>  circle+label, draggable → position 저장
 │    └─ <ConnectionLine> weight 굵기/투명도, blocked=빨강 점선
 ├─ <RegionPanel>        선택 지역의 지식(쿼리 API): direct/inherited/global/propagated/rumors + 편집(지식 upsert)
 └─ <AugmentPanel>       보강 세션 시작 → 질문 목록 → 답변(action) → ChangeSet/revert
```

## Props / State (요지)
- `App`: `worldId`, `graph`(GraphSummary+regions+connections), `selectedRegionId`, `mapImageUrl`.
- `MapOverlay`: props `regions`, `connections`, `onSelect(regionId)`, `onMove(regionId, x, y)`. 좌표=`region.position {x,y}`(0~1); 없으면 자동 레이아웃(`autoLayout(regions)`).
- `RegionMarker`: props `region`, `x`, `y`, `selected`, drag 핸들러.
- `ConnectionLine`: props `from{x,y}`, `to{x,y}`, `kind`, `weight`.
- `RegionPanel`: props `worldId`, `regionId`; state `result`(QueryResult); 편집 폼.
- `AugmentPanel`: props `worldId`; state `session`(AugmentationSession), `answers`.

## API 연동 지점 (src/api.ts)
- query: `GET /api/query/regions/{id}/knowledge?world_id=` ; `GET /api/query/diff`.
- authoring: `POST /worlds/{id}/build` ; `POST /wiki/build` ; `GET /worlds/{id}/graph` ; `PUT regions/{id}` ; `PUT knowledge/{id}` ; `DELETE nodes/{id}`.
- augment: `POST /worlds/{id}/augment/session` ; `POST /augment/{sid}/answer` ; `POST /augment/{sid}/revert`.
- 토폴로지 조회: graph summary는 region_ids만 → 토폴로지 좌표/연결은 **export 또는 신규 GET graph(full)** 필요. MVP: `GET /api/query/.../knowledge`로 지역별, 그리고 connections는 **build 응답/export**에서 취득. (간이: U9 export_world JSON을 UI가 로드해 regions/connections 렌더.)

## 자동화 친화 (data-testid)
- 모든 상호작용 요소에 `data-testid`: `world-input`, `build-world-btn`, `region-marker-{id}`, `region-panel`, `knowledge-item-{id}`, `augment-start-btn`, `augment-answer-btn`, `augment-revert-btn`.

## 시각화 규칙
- 연결선: stroke-width = 1+weight*4, opacity = 0.3+weight*0.7; kind=blocked → 빨강 점선.
- 마커 드래그 종료 시 `PUT region`(position) 저장.
- 지식 항목: scope_type 배지 + confidence + is_rumor(소문) 표시.
