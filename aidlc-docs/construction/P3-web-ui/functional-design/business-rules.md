# P3 Web UI — Business Rules

> BR-P3-*. 프론트 + 1 additive 백엔드 read 엔드포인트. 기존 14 vitest 회귀 0.

| ID | 규칙 |
|---|---|
| **BR-P3-1** | Event 생성 폼 대상 = 지도에서 선택된 리전(`regionId`). regionId 없으면 폼 비표시(기존 안내 재사용). |
| **BR-P3-2** | 모든 Event 쓰기 컨트롤(create/suggest/approve/discard/resolve)은 닫힌 세션에서 `disabled`(기존 SessionPanel 패턴). 읽기(목록/distortion/timeline)는 표시. |
| **BR-P3-3** | Event 목록은 세션 전역(모든 리전), region 라벨 + status badge(suggested/active/resolved) 표시 (FD-P3 Q3=A). |
| **BR-P3-4** | suggested 항목 → Approve/Discard 액션만; active 항목 → Resolve 액션. resolved 항목은 액션 없음(표시만). |
| **BR-P3-5** | 모든 액션은 기존 `run(fn)` 래퍼로 실행 → 성공 시 `refresh()` + `onChanged?()` 호출(낙관적 아님, 재로드). 에러는 패널 상단 표시. |
| **BR-P3-6** | 선택 리전 distortion 슬라이더 초기값·라벨 = `listDistortions` 실제값(`distortions[regionId] ?? 0.3`). 수동 set은 기존 `setDistortion` 유지. (FR-P8.5) |
| **BR-P3-7** | 신규 백엔드 `GET /sessions/{sid}/distortions`는 additive·읽기 전용(`list_region_distortions` 재사용). 기존 라우트/시그니처 불변. |
| **BR-P3-8** | TS 타입/ api.ts는 additive — 기존 타입·메서드 불변(GameSession/SessionRumor/TurnResult 확장은 필드 추가만). |
| **BR-P3-9** | data-testid 안정 명명(`event-{id}`/`approve-{id}`/`event-create-btn`/`suggest-events-btn` 등) — 자동화 친화. |
| **BR-P3-10** | tsc/vite build 클린, 기존 14 vitest GREEN + 신규 테스트. |

## 테스트 포인트 (vitest)
- create form 제출 → `createEvent(sid, {region_id, category, magnitude,...})`.
- suggest → `suggestEvents`; suggested 항목 approve/discard 호출.
- active resolve 호출; distortion 실제값 반영; 닫힌 세션 disabled.
- 회귀: 기존 SessionPanel(generate/advance/promoted badge) 동작 유지.
