# P1 Event Foundation — Business Logic Model

> P1 범위: Event 데이터 계층 + 수동 라이프사이클(엔진 비의존). distortion 적용/복원·LLM 제안·advance_turn 통합은 P2.

## SessionRepository Event CRUD (포트 + 두 어댑터)
| 메서드 | 동작 | 비고 |
|---|---|---|
| `create_event(event) -> SessionEvent` | INSERT, 저장본 반환 | id/필드 그대로; created_at 불요(turn 기반) |
| `get_event(session_id, event_id) -> SessionEvent \| None` | 단건 조회(세션 스코프) | 격리 |
| `list_events(session_id, status=None) -> list[SessionEvent]` | 목록(옵션 status 필터) | created_turn,id 순 정렬 |
| `update_event(event) -> SessionEvent` | UPSERT(status/resolved_turn/contributions 갱신) | P2 복원도 이걸 사용 |
| `delete_event(session_id, event_id) -> None` | 삭제(suggested 폐기용) | idempotent |

- in-memory + PostgreSQL 어댑터 둘 다 동일 가시 동작(정렬·세션 격리). 오프라인 테스트는 SQLite 엔진으로 postgres 어댑터 스모크.

## GameMasterService — 수동 Event 메서드 (P1 구현분)
```
create_event(session_id, region_id, *, category, description, magnitude, lifecycle=None):
  session = require_open(session_id)                 # 닫힌 세션 쓰기 금지(BR-P1-7)
  assert region_id in canonical topology(world_id)   # FD-P1 Q2=A → LookupError if absent
  lifecycle = lifecycle or default_lifecycle(category)
  ev = SessionEvent(session_id, region_id, category, description, magnitude,
                    lifecycle, status=ACTIVE, created_turn=session.turn,
                    provenance=Provenance(source=SESSION, generated_by="gm:event"))
  saved = repo.create_event(ev)
  timeline(EVENT_CREATED, summary, {event_id, region_id, category, magnitude})
  return saved

list_events(session_id, status=None):                # 읽기 — 닫힌 세션에도 허용
  require session exists; return repo.list_events(session_id, status)

resolve_event(session_id, event_id):                 # FD-P1 Q4=A: 상태전이만(P1)
  session = require_open(session_id)
  ev = repo.get_event(...) or raise LookupError
  if ev.status == RESOLVED: return ev                # idempotent(BR-P1-6)
  ev.status = RESOLVED; ev.resolved_turn = session.turn
  saved = repo.update_event(ev)
  timeline(EVENT_RESOLVED, summary, {event_id})
  return saved
  # P2가 여기에 dynamics.restore_contributions + set_region_distortion 추가.

discard_event(session_id, event_id):                 # suggested 폐기(P1은 수동 생성=ACTIVE라 주로 P2 제안용; 메서드는 P1에 둠)
  session = require_open(session_id)
  ev = repo.get_event(...) or raise LookupError
  if ev.status != SUGGESTED: raise ValueError        # active/resolved는 폐기 불가(BR-P1-8)
  repo.delete_event(session_id, event_id)
```

## API (additive, `api/routers/session.py`)
| 라우트 | → 서비스 | 응답 |
|---|---|---|
| `POST /sessions/{sid}/events` | create_event | SessionEvent (201/200) |
| `GET /sessions/{sid}/events?status=` | list_events | list[SessionEvent] |
| `POST /sessions/{sid}/events/{eid}/resolve` | resolve_event | SessionEvent |
| `DELETE /sessions/{sid}/events/{eid}` | discard_event | 204 |

- 에러 매핑(Phase 1 라우터 패턴 계승): LookupError→404, SessionClosedError→409, ValueError(잘못된 전이)→409/400.

## 데이터 흐름
```
API → GameMasterService(create/list/resolve/discard) → SessionRepository(Event CRUD) → {InMemory | Postgres(session_events)}
                                              ↘ WorldLoader.load(world).topology (region 검증, 읽기만)
                                              ↘ append_timeline(EVENT_CREATED/EVENT_RESOLVED)
```
- 캐노니컬은 region 검증을 위한 **읽기 참조만**(NFR-P2).
