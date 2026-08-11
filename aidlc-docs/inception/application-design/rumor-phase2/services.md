# Phase 2 — Services

> 서비스 정의·책임·오케스트레이션. Phase 2의 유일한 오케스트레이터는 확장된 **GameMasterService**(신규 서비스 없음).

## S1. GameMasterService (확장)
- **책임**: 한 세션의 동적 상태를 턴 단위로 구동. Phase 1(소문 생성/재생성/지지도/승격/턴) + **Phase 2 Event 라이프사이클·동적 distortion 진화·support 자동 진화**.
- **의존**: `SessionRepository`(C6, Event CRUD 포함), `RumorGenerator`(기존), **`EventSuggester`(C4, 신규 주입)**, `WorldLoader`(캐노니컬 읽기), `dynamics`(C3, 순수), `promotion`(기존, 순수).
- **트랜잭션 경계**: 각 public 메서드 = 1 논리 동작 + 1+ TimelineEntry. advance_turn은 다단계지만 단일 호출로 일괄.

### 오케스트레이션: 수동/제안 흐름 (AD-P Q3=A)
```
[수동]   create_event → repo.create_event(status=ACTIVE) → timeline(EVENT_CREATED)
[제안]   suggest_events → EventSuggester.suggest → repo.create_event(status=SUGGESTED) ×n
[승인]   approve_event  → status SUGGESTED→ACTIVE
[폐기]   discard_event  → repo.delete_event
[해소]   resolve_event  → dynamics.restore_contributions → repo.set_region_distortion(복원) →
                          status→RESOLVED, resolved_turn → timeline(EVENT_RESOLVED)
```

### 오케스트레이션: advance_turn 시퀀스 (FR-P3.3, 핵심)
```
advance_turn(session_id):
  session = require_open(session_id)
  active = repo.list_events(session_id, status=ACTIVE)
  influenced: set[region_id] = {}

  # 1) Event 적용 — distortion 갱신(주 대상 + 토폴로지 전파, 누적)
  kg, topo = loader.load(world_id)               # 캐노니컬 읽기 참조만 (NFR-P2)
  cur = {rd.region_id: rd.degree for rd in repo.list_region_distortions(session_id)}
  for ev in active:
      base = dynamics.distortion_delta(ev.magnitude)
      deltas = dynamics.propagate_delta(ev.region_id, base, topo.connections, min_weight=…)
      cur = dynamics.apply_deltas(cur, deltas)    # clamp
      ev.contributions = merge(ev.contributions, deltas)   # 복원용 누적
      influenced |= set(deltas)
      if ev.lifecycle == ONE_SHOT: ev.status = RESOLVED; ev.resolved_turn = turn+1
      repo.update_event(ev)
      timeline(EVENT_APPLIED, {event_id, deltas})
  for rid, deg in cur.items(): repo.set_region_distortion(session_id, rid, deg)

  # 2) 주 대상 리전 소문 add/update (보존, FR-P4.1 / CL3.1=B) — 이웃은 distortion만 (CL4.1=A)
  for ev in active:
      _update_region_rumors(session, ev.region_id)   # 기존 소문/support 보존하며 새 distortion 반영

  # 3) support 자동 진화 (FR-P5.1) — 영향 리전 강화 / 그 외 감쇠
  all_rumors = repo.list_rumors(session_id)
  dynamics.evolve_support(all_rumors, influenced, reinforce=…, decay=…) → upsert

  # 4) 승격/강등 재평가 (Phase 1 재사용)
  res = promotion.evaluate(repo.list_rumors(session_id), threshold)
  apply promote/demote + timeline(PROMOTE/DEMOTE)

  # 5) 턴 증가 + 요약 타임라인
  new_turn = repo.bump_turn(session_id); timeline(ADVANCE_TURN, …, turn=new_turn)
  return TurnResult(turn=new_turn, applied_event_ids=[…], created_event_ids=[…],
                    promoted_ids=res.promoted_ids, demoted_ids=res.demoted_ids)
```
- **graceful (NFR-P3)**: 1·3·4·5는 순수/DB로 LLM 비의존 → 항상 동작. suggest_events(LLM)만 graceful 분기.
- **결정론 (NFR-P4)**: 1·3 계산은 dynamics 순수 함수 — 동일 입력→동일 출력(PBT 대상).

## 서비스 상호작용 요약
- API(C7) → GameMasterService(S1) → {SessionRepository(C6), EventSuggester(C4), RumorGenerator, dynamics(C3), promotion, WorldLoader}.
- 신규 서비스/오케스트레이터 없음 — 기존 단일 서비스 확장으로 응집 유지.
