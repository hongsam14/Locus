# U-H1 Rumor Dynamics — Business Logic Model

> FD-H Q1..Q6 = all A. 순수 로직은 `rumor_dynamics.py`(부수효과·LLM·DB 없음, PBT). 서비스가 수집→호출→영속.

## 1. 순수 함수 (`locus/session/rumor_dynamics.py`)

### 1.1 decay_support(rumors, reinforced_region_ids, *, decay)
```
for r in rumors:                       # 활성 루머만 전달됨 (BR-H1-11)
    if r.promoted or r.region_id in reinforced_region_ids:
        continue                       # 승격/강화 지역 → 감쇠 면제 (Q6=A, Q2=A)
    r.support = clamp(r.support - decay)
return rumors                          # in-place, 호출자 영속
```
- **매 턴 호출**(빈 턴 포함, FD-H Q1=A). `reinforced` = 이벤트 influenced ∪ 피드백 지역(Q2=A).
- 승격 루머는 감쇠 대상에서 제외(Q6=A: 감쇠 면제) — 승격=합의된 사실 보호.

### 1.2 is_prunable(rumor, *, floor) / partition_prunable(rumors, *, floor)
```
is_prunable(r) := (not r.promoted) and (r.support < floor)     # Q7=A 승격 예외
partition_prunable(rumors) := (survivors, prunable)            # 활성 루머만 입력
```
- 순수 판정. 호출자가 prunable을 `active=False`로 표시(하드 삭제 아님, Q2=B).

### 1.3 is_eligible_source(rumor, *, min_support)
```
is_eligible_source(r) := r.support >= min_support             # FR-H2 자동 증식 게이트
```
- RumorService가 자동 append 소스 수집 시 **세션 루머 소스**에만 적용(캐노니컬 소스는 게이트 안 함).

### 1.4 region_feedback(rumors, *, weight, high_support_threshold) — 고-support 밀도 (Q4=A)
```
by_region = group active rumors by region_id
for region, rs in by_region:
    strong = count(r in rs if r.support >= high_support_threshold)
    density = strong / len(rs)          # 0..1
    if density > 0:
        delta[region] = weight * density
return delta                            # region_id -> distortion delta (>0)
```
- 순수·결정론. 밀도 기반이라 지역 루머 수에 스케일 안정. 강한 소문 밀집 ⇒ 지역 distortion↑.

### 1.5 (참고) 기존 evolve_support
- 이벤트 support 강화(+reinforce)는 Phase 2 `dynamics.evolve_support`가 계속 담당. U-H1의 `decay_support`는
  **감쇠·prune 전용**. FD에서 두 함수의 책임 분리 유지(강화=이벤트 dynamics, 감쇠=rumor_dynamics). 통합 여부는
  코드젠에서 회귀 최소 방향으로 결정(기본: 분리 유지).

## 2. RumorFeedbackService (`rumor_feedback_service.py`)
```
apply_feedback(session, active_rumors) -> dict[region_id, delta]:
    delta = rumor_dynamics.region_feedback(active_rumors,
              weight=params.feedback_weight,
              high_support_threshold=params.high_support_threshold)
    for region, d in delta.items():
        cur = repo.get_region_distortion(session.id, region) or DEFAULT_DISTORTION_DEGREE
        repo.set_region_distortion(session.id, region, clamp(cur + d))
    return delta
```
- 순수 집계는 CH1 위임, 부수효과(distortion 쓰기)만 담당(SRP, Q4=B). 반환 delta의 키 = 피드백 지역.

## 3. RumorService (증식 게이트, Q3=A)
```
append_for_region(session, region_id, *, min_source_support=None):
    return _generate_for_region(session, region_id,
             _chain_degrees(...), min_source_support=min_source_support)

_collect_sources(world_id, region_id, session_id, *, min_source_support=None):
    sources = [canonical direct + propagated]           # 게이트 안 함
    for r in repo.list_rumors(session_id, region_id):   # 활성만(include_pruned=False 기본)
        if min_source_support is None or rumor_dynamics.is_eligible_source(r, min_support=min_source_support):
            sources.append(rumor source)
    return sources
```
- 수동 경로(`generate_rumors`/`regenerate_region`)는 `min_source_support=None` → 기존 동작 불변.

## 4. advance_turn 확장 시퀀스 (TurnAdvancer, FD-H Q5=A)
```
0. session = _require_open(session_id)
1. events = _apply_active_events(session)                       # 기존(이벤트 dynamics) 불변
      → applied/resolved ids, target_regions, influenced_regions
2. for region in events.target_regions:                        # FR-H2 증식 게이트
      rumors.append_for_region(session, region, min_source_support=params.min_source_support)
3. active = repo.list_rumors(session_id)                        # 활성만
   fb = feedback.apply_feedback(session, active)                # FR-H3 피드백(먼저)
   reinforced = events.influenced_regions | set(fb.keys())      # Q2=A
4. dynamics.evolve_support(active, events.influenced_regions)   # 이벤트 강화(+) 기존
   rumor_dynamics.decay_support(active, reinforced, decay=params.support_decay)  # FR-H1 감쇠(매 턴)
   survivors, prunable = rumor_dynamics.partition_prunable(active, floor=params.prune_floor)
   for r in prunable: r.active = False                          # soft-flag (승격 예외)
5. res = promotion.evaluate(survivors, promotion_threshold)     # 활성 생존만 평가
   set promoted flags + PROMOTE/DEMOTE timeline
6. repo.upsert_rumors(active)                                   # FR-H5 배치, 1 트랜잭션
7. new_turn = repo.bump_turn(session_id)
   timeline(ADVANCE_TURN, {applied, resolved, promoted, demoted, pruned, feedback_regions})
8. return TurnResult(... + pruned_rumor_ids, feedback_regions=list(fb))
```
- **순서 근거(Q5=A)**: 피드백 → 감쇠 → prune. 강한 루머가 자신의 지역을 먼저 왜곡(피드백)하고, 그 지역은
  reinforced에 포함돼 감쇠를 면함 — "강한 소문이 스스로를 보호·전파"하는 일관 루프. 약한 루머만 감쇠·정리.
- **배치 영속화**: 강화·감쇠·prune(active)·승격 플래그가 모두 반영된 `active` 리스트를 한 번에 `upsert_rumors`.

## 5. GameMasterService (DI 조립)
```
__init__(..., *, feedback=None, rumor_params=DEFAULT_RUMOR_DYNAMICS, turns=None):
    rumor_params ← (settings 조립 or 인자)
    feedback ← feedback or RumorFeedbackService(repo, rumor_params)
    turns ← turns or TurnAdvancer(repo, loader, rumors, feedback, rumor_params)
```
- 공개 API 불변(thin coordinator). 미주입 시 default-construct(테스트 대체 가능).

## 6. 데이터 흐름 (1턴)
```
Settings ─조립→ RumorDynamicsParams ─주입→ {TurnAdvancer, FeedbackService, RumorService(via append)}
events ─dynamics→ distortion Δ, influenced
append(min_source_support) ─is_eligible_source→ 새 루머(자격 소스만)
active rumors ─region_feedback→ distortion Δ(고-support 밀도) → feedback_regions
active ─decay_support(reinforced=influenced∪feedback)→ support↓ ; evolve_support→ 강화지역 support↑
partition_prunable(floor, 승격 예외) → prunable.active=False
promotion.evaluate(survivors) → promote/demote
repo.upsert_rumors(active)  (1 트랜잭션)
```
