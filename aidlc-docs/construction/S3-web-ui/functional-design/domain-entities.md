# S3 (Web UI) — Domain Entities (Functional Design)

Unit **S3**. FR-R6. 프런트(`web/`)의 TS 타입 + API 클라이언트 표면. 백엔드 도메인은 S1/S2 그대로.
확정 답: FD-S3 **Q1=A**(SessionBar+SessionPanel)/**Q2=GameMaster(SessionPanel) 중심**/**Q3=A**(세션 선택 시 세션 NPC 쿼리)/**Q4=A**(support 슬라이더)/**Q5=A**(SessionPanel 타임라인+드롭다운)/**Q6=A**(dead buildWiki 전부 제거).

---

## 1. 신규 TS 타입 (`web/src/types.ts`)
백엔드 Pydantic 모델과 1:1 (필드명 동일, snake_case 유지).
```ts
export interface GameSession {
  id: string;
  world_id: string;
  status: "open" | "closed";
  turn: number;
  created_at?: string | null;
  closed_at?: string | null;
}

export interface SessionRumor {
  id: string;
  session_id: string;
  region_id: string;
  distorted_from_id: string;
  distorted_from_kind: string;       // "knowledge" | "rumor"
  statement: string;
  distortion_degree: number;         // [0,1]
  support: number;                   // [0,1]
  confidence: number;                // [0,1]
  promoted: boolean;
}

export interface RegionDistortion {
  session_id: string;
  region_id: string;
  distortion_degree: number;
}

export interface TimelineEntry {
  id: string;
  session_id: string;
  turn: number;
  kind: string;                      // TimelineKind value
  summary: string;
  payload: Record<string, unknown>;
  created_at?: string | null;
}

export interface TurnResult {
  session_id: string;
  turn: number;
  promoted_ids: string[];
  demoted_ids: string[];
}
```
- 기존 `QueryResult`/`KnowledgeView` 재사용(세션 NPC 쿼리 응답; `is_rumor`/`distortion_degree`로 소문·승격 표현).

## 2. API 클라이언트 표면 (`web/src/api.ts`)
```ts
// session lifecycle
listSessions(worldId): GameSession[]
startSession(worldId): GameSession
closeSession(sid): GameSession
getTimeline(sid): TimelineEntry[]
// rumor engine (GameMaster)
listRumors(sid, regionId): SessionRumor[]          // ← S2 API 보강(additive GET, 아래 §3)
generateRumors(sid, regionId): SessionRumor[]
regenRumors(sid, regionId): SessionRumor[]
setSupport(sid, rumorId, support): SessionRumor
setDistortion(sid, regionId, degree): RegionDistortion
advanceTurn(sid): TurnResult
sessionKnowledge(sid, regionId): QueryResult       // NPC 세션 뷰 (Q3=A)
```
- **제거(Q6=A)**: `api.buildWiki`.

## 3. 백엔드 보강 (additive, read-only) — `api/routers/session.py`
UI가 세션/리전 전환 시 소문을 support·promoted 값과 함께 다시 로드하려면 목록 GET이 필요(현 S2엔 없음). `SessionRepository.list_rumors` 재사용, 동작 변경 없음:
```
GET /api/session/sessions/{sid}/regions/{rid}/rumors -> list[SessionRumor]
```
- 닫힌 세션도 조회 가능(읽기). 없는 세션 → 404. (쓰기 규칙 불변)

## 4. 컴포넌트 ↔ 타입 매핑 (요약)
| 컴포넌트(신규/수정) | 사용 타입 |
|---|---|
| `SessionBar`(신규) | GameSession[] (드롭다운), GameSession(현재) |
| `SessionPanel`(신규, GameMaster 허브) | GameSession, TimelineEntry[], SessionRumor[], RegionDistortion, TurnResult |
| `RegionPanel`(수정) | QueryResult(세션 NPC 뷰 또는 캐노니컬) |
| `App`(수정) | sessionId 상태, selectedRegion 연동 |
| `Toolbar`(수정) | buildWiki 제거 |

- 상세 컴포넌트 책임/상태/동작은 `business-logic-model.md`, UI 규칙은 `business-rules.md`.
