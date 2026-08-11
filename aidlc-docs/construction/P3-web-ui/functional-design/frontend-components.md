# P3 Web UI — Frontend Components

> SessionPanel 확장(GameMaster 허브). 기존 컴포넌트/흐름 보존, Event UI additive. data-testid로 자동화 친화.

## SessionPanel (확장)
기존 props 유지: `{ session, regionId, onChanged? }`.

### 추가 state
| state | 용도 |
|---|---|
| `events: SessionEvent[]` | 세션 전역 Event 목록(FD-P3 Q3=A) |
| `distortions: Record<string, number>` | 실제 per-region distortion(listDistortions) |
| `evForm: { category, description, magnitude, lifecycle? }` | Event 생성 폼 입력 |

### refresh() 확장
- 기존(timeline, rumors) + `events = listEvents(sid)` + `distortions = listDistortions(sid)`.
- 선택 리전 distortion 슬라이더 초기값/라벨 = `distortions[regionId] ?? 0.3`(로컬 기본 대신 실제값, FR-P8.5).

### 컴포넌트 계층 (확장 영역)
```
SessionPanel
├─ Advance Turn 버튼 (기존)
├─ [세션 전역] Suggest events 버튼  →  api.suggestEvents(sid, n=1)        [data-testid=suggest-events-btn]
├─ [세션 전역] Event 목록 (events)                                         [data-testid=events]
│   └─ li[event-{id}]  region 라벨 · category · magnitude · status badge
│        ├─ status=suggested → Approve [approve-{id}] / Discard [discard-{id}]
│        └─ status=active    → Resolve [resolve-{id}]
├─ [선택 리전] region 섹션 (기존: distortion 슬라이더·generate·regen·소문 목록)
│   └─ Event 생성 폼 (대상=regionId)                                       [data-testid=event-form]
│        ├─ category <select>            [event-category]
│        ├─ description <input>          [event-description]
│        ├─ magnitude <input range>      [event-magnitude]
│        ├─ lifecycle <select>(default/override) [event-lifecycle]
│        └─ Create 버튼                  [event-create-btn]  → api.createEvent(...)
└─ Timeline (기존; EVENT_* 항목도 자동 표시 — kind/summary 렌더)
```

### 상호작용 (기존 `run(fn)` 래퍼 재사용 — 실행→refresh→onChanged)
- Create event: 폼 입력 → `createEvent(sid,{region_id:regionId,...})` → refresh.
- Suggest: `suggestEvents(sid)` → suggested 항목이 목록에 등장.
- Approve/Discard/Resolve: 항목 액션 → 각 api 호출 → refresh.
- 모든 쓰기 컨트롤은 `closed`(session.status==="closed") 시 `disabled`(기존 패턴).

### 폼 검증
- magnitude: range 0~1(slider). category/lifecycle: enum select. description: 자유(빈 값 허용).
- regionId 없으면 Event 생성 폼 비표시(기존 "select a region" 안내 재사용).

## 기타 컴포넌트
- **types.ts / api.ts**: domain-entities.md대로 additive.
- **RegionPanel / SessionBar / App / Toolbar / MapOverlay**: 변경 없음(P3는 SessionPanel + types + api 중심). 지도 distortion 틴트는 범위 외(최소).

## 테스트(vitest) 포인트
- Event 생성 폼 제출 → createEvent 호출(올바른 region/category/magnitude).
- Suggest 버튼 → suggestEvents 호출; suggested 항목 approve/discard 렌더·호출.
- active event resolve 호출.
- distortion 슬라이더가 listDistortions 실제값 반영.
- 닫힌 세션에서 Event 쓰기 컨트롤 disabled.
- 기존 14 vitest 회귀 GREEN.
