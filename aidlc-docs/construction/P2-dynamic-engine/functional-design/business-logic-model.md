# P2 Dynamic Engine — Business Logic Model

## 1. dynamics 순수 함수 (`locus/session/dynamics.py`)
```python
MAX_EVENT_DELTA = 0.3
PROPAGATE_MIN_WEIGHT = 0.15
SUPPORT_REINFORCE = 0.1
SUPPORT_DECAY = 0.05

def distortion_delta(magnitude):           # FD-P2 Q1=A
    return _clamp(magnitude) * MAX_EVENT_DELTA

def propagate_delta(region_id, base_delta, connections, *, min_weight=PROPAGATE_MIN_WEIGHT):
    # FD-P2 Q2=A. best_path_weights: 1.0 at source, decays with distance.
    weights = best_path_weights(region_id, connections)
    out = {region_id: base_delta}
    for rid, w in weights.items():
        if rid == region_id:
            continue
        if w >= min_weight:
            out[rid] = base_delta * w
    return out

def apply_deltas(current, deltas):         # cumulative + clamp [0,1] (persistent 누적 동일 경로)
    out = dict(current)
    for rid, d in deltas.items():
        out[rid] = _clamp(out.get(rid, DEFAULT_DISTORTION_DEGREE) + d)
    return out

def restore_contributions(current, contributions):   # FD-P2 Q3(persistent resolve) / CL1.2
    out = dict(current)
    for rid, d in contributions.items():
        out[rid] = _clamp(out.get(rid, DEFAULT_DISTORTION_DEGREE) - d)
    return out

def evolve_support(rumors, influenced_region_ids, *, reinforce=SUPPORT_REINFORCE, decay=SUPPORT_DECAY):
    # FD-P2 Q4=A. In-place new support; clamp [0,1].
    for r in rumors:
        r.support = _clamp(r.support + (reinforce if r.region_id in influenced_region_ids else -decay))
    return rumors
```

## 2. advance_turn 통합 시퀀스 (`GameMasterService.advance_turn`, 확장)
```
advance_turn(session_id, *, promotion_threshold=0.6):
  session = require_open(session_id)
  _kg, topo = loader.load(session.world_id)          # 캐노니컬 읽기 참조만 (NFR-P2)
  active = repo.list_events(session_id, status="active")
  cur = {rd.region_id: rd.distortion_degree for rd in repo.list_region_distortions(session_id)}
  influenced: set[str] = set()
  applied_ids, resolved_ids = [], []

  # (1) Event 적용 — distortion 갱신(주 대상 + 전파, 누적)
  for ev in active:
      base = dynamics.distortion_delta(ev.magnitude)
      deltas = dynamics.propagate_delta(ev.region_id, base, topo.connections)   # FD-P2 Q1/Q2
      cur = dynamics.apply_deltas(cur, deltas)
      ev.contributions = _merge_add(ev.contributions, deltas)   # 복원용 누적
      influenced |= set(deltas)
      applied_ids.append(ev.id)
      if ev.lifecycle == ONE_SHOT:            # FD-P2 Q3=A: 1회 적용 후 resolved, 복원 없음
          ev.status = RESOLVED; ev.resolved_turn = session.turn + 1
          resolved_ids.append(ev.id)
      repo.update_event(ev)
      timeline(EVENT_APPLIED, {event_id, region_id, deltas})
  for rid, deg in cur.items():
      repo.set_region_distortion(session_id, rid, deg)

  # (2) 주 대상 리전 소문 append 생성 (FD-P2 Q5=A / FR-P4.1) — 전파 이웃은 distortion만 (CL4.1)
  for region_id in {ev.region_id for ev in active}:
      self._generate_for_region(session, region_id, self._chain_degrees(session_id, region_id))
      # 기존 소문/support 보존(wipe 없음). 새 distortion이 chain cap.

  # (3) support 자동 진화 (FD-P2 Q4=A)
  rumors = repo.list_rumors(session_id)
  for r in dynamics.evolve_support(rumors, influenced):
      repo.upsert_rumor(r)

  # (4) 승격/강등 재평가 (Phase 1 promotion 재사용)
  res = promotion.evaluate(repo.list_rumors(session_id), promotion_threshold)
  for rid in res.promoted_ids: set_promoted(rid, True);  timeline(PROMOTE, ...)
  for rid in res.demoted_ids:  set_promoted(rid, False); timeline(DEMOTE, ...)

  # (5) 턴 증가 + 요약
  new_turn = repo.bump_turn(session_id)
  timeline(ADVANCE_TURN, {applied: applied_ids, resolved: resolved_ids,
                          promoted: res.promoted_ids, demoted: res.demoted_ids}, turn=new_turn)
  return TurnResult(session_id, new_turn, res.promoted_ids, res.demoted_ids,
                    applied_event_ids=applied_ids, resolved_event_ids=resolved_ids)
```
- **graceful (NFR-P3)**: (1)(3)(4)는 순수/DB로 LLM 비의존. (2)의 LLM 실패는 기존 RumorGenerator graceful(빈 체인)로 흡수 — 턴 진행 계속.
- **결정론 (NFR-P4)**: (1)(3)는 dynamics 순수 — 동일 입력 동일 출력.

## 3. resolve_event 확장 (P1 → P2: 복원 추가)
```
resolve_event(session_id, event_id):     # FR-P3.6 / CL1.2=A
  session = require_open(session_id)
  ev = repo.get_event(...) or raise LookupError
  if ev.status == RESOLVED: return ev      # idempotent (BR-P1-6)
  if ev.contributions:                     # 누적 기여분 대칭 복원 (주 대상 + 전파 이웃, AD-P Q5=A)
      cur = {rd.region_id: rd.distortion_degree for rd in repo.list_region_distortions(session_id)}
      cur = dynamics.restore_contributions(cur, ev.contributions)
      for rid in ev.contributions: repo.set_region_distortion(session_id, rid, cur[rid])
  ev.status = RESOLVED; ev.resolved_turn = session.turn
  repo.update_event(ev); timeline(EVENT_RESOLVED, {event_id, restored: ev.contributions})
  return ev
```

## 4. EventSuggester + suggest/approve (`event_suggester.py` + service)
```
class EventSuggester(llm):
  def suggest(*, world_id, region_ids, turn, context="", n=1) -> list[EventDraft]:
      try: return llm.structured(prompt, EventDraftList, system=_SYSTEM).drafts[:n]
      except Exception: return []          # graceful (NFR-P3)

GameMasterService.suggest_events(session_id, *, n=1) -> list[SessionEvent]:   # AD-P Q3/Q4, CL2.2
  session = require_open(session_id)
  region_ids = [r.id for r in loader.load(session.world_id)[1].regions]
  drafts = self._suggester.suggest(world_id=session.world_id, region_ids=region_ids, turn=session.turn, n=n)
  out = []
  for d in drafts:
      if d.region_id not in region_ids: continue          # skip invalid region
      ev = SessionEvent(..., status=SUGGESTED, magnitude=clamp(d.magnitude),
                        lifecycle=default_lifecycle(d.category), created_turn=session.turn,
                        provenance=Provenance(source=SESSION_EVENT, generated_by="llm:event"))
      out.append(repo.create_event(ev)); timeline(EVENT_CREATED, {suggested:true,...})
  return out

GameMasterService.approve_event(session_id, event_id) -> SessionEvent:   # CL2.1=A
  session = require_open(session_id)
  ev = repo.get_event(...) or raise LookupError
  if ev.status != SUGGESTED: raise ValueError
  ev.status = ACTIVE; repo.update_event(ev); timeline(EVENT_CREATED,{approved:true})  # or dedicated note
  return ev
```

## 5. API (additive, `api/routers/session.py`)
| 라우트 | → 서비스 | 응답 |
|---|---|---|
| `POST /sessions/{sid}/suggest-events?n=` | suggest_events | list[SessionEvent] (suggested) |
| `POST /sessions/{sid}/events/{eid}/approve` | approve_event | SessionEvent |
| `POST /sessions/{sid}/advance-turn` (기존, 동작 확장) | advance_turn | TurnResult(확장) |

## 6. main.py 와이어링
- `GameMasterService(repo, RumorGenerator(llm), loader, suggester=EventSuggester(llm))` — EventSuggester 주입(생성자 옵션 추가, 기존 호출 호환을 위해 기본값 None 허용; None이면 suggest_events는 빈 결과/503 처리).
