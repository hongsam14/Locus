# P3 Web UI — Domain Entities (TS contract)

> FD-P3 all A. additive TS types + 신규 read 엔드포인트. 기존 타입/메서드 불변.

## types.ts (additive)
```ts
export type EventCategory = "war" | "plague" | "politics" | "disaster" | "festival" | "discovery";
export type EventLifecycle = "one_shot" | "persistent";
export type EventStatus = "suggested" | "active" | "resolved";

export interface SessionEvent {
  id: string;
  session_id: string;
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
  lifecycle: EventLifecycle;
  status: EventStatus;
  created_turn: number;
  resolved_turn?: number | null;
  contributions: Record<string, number>;
}

export interface EventDraft {
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
}

// TurnResult: +applied_event_ids / +resolved_event_ids (additive)
export interface TurnResult {
  session_id: string;
  turn: number;
  promoted_ids: string[];
  demoted_ids: string[];
  applied_event_ids: string[];
  resolved_event_ids: string[];
}
// RegionDistortion 이미 존재(types.ts) — 재사용.
```

## api.ts (additive 메서드)
| 메서드 | HTTP | 비고 |
|---|---|---|
| `createEvent(sid, body)` | POST `/sessions/{sid}/events` | body{region_id,category,description,magnitude,lifecycle?} → SessionEvent |
| `listEvents(sid, status?)` | GET `/sessions/{sid}/events?status=` | → SessionEvent[] |
| `suggestEvents(sid, n?)` | POST `/sessions/{sid}/suggest-events?n=` | → SessionEvent[](suggested) |
| `approveEvent(sid, eid)` | POST `/sessions/{sid}/events/{eid}/approve` | → SessionEvent |
| `resolveEvent(sid, eid)` | POST `/sessions/{sid}/events/{eid}/resolve` | → SessionEvent |
| `discardEvent(sid, eid)` | DELETE `/sessions/{sid}/events/{eid}` | 204 |
| `listDistortions(sid)` | GET `/sessions/{sid}/distortions` | → RegionDistortion[] (신규 백엔드) |

## 신규 백엔드 read 엔드포인트 (additive, P3 발견)
- `GET /api/session/sessions/{sid}/distortions` → `list[RegionDistortion]` (`GameMasterService.list_distortions` → `repo.list_region_distortions`). 닫힌 세션에도 허용(읽기). LookupError→404.
