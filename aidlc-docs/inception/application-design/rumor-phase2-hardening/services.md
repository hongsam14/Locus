# 하드닝 & 루머 동역학 — Services & Orchestration

> 서비스 경계와 advance_turn 오케스트레이션. 상세 규칙·순수 공식은 per-unit FD.

## 서비스 목록 (SRP, DI)

| 서비스 | 신규/확장 | 책임 | 주입 의존 |
|---|---|---|---|
| `GameMasterService` | 확장 | thin coordinator — 하위 서비스 조립·위임(공개 API 불변) | repo, generator, loader, params, suggester, rumors, events, distortions, turns **+ feedback, rumor_params** |
| `RumorService` | 확장 | 루머 생성/재생성/support 조정 + 자동 append(**증식 게이트**) | repo, generator, loader, consensus params |
| `EventService` | 불변 | 이벤트 라이프사이클(생성/제안/승인/해소) | repo, loader, suggester |
| `DistortionService` | 불변 | 지역 distortion 수동 조회/설정 | repo |
| `RumorFeedbackService` | **신규** | 루머→지역 피드백(FR-H3) 적용(순수 집계는 rumor_dynamics 위임) | repo, rumor_params |
| `TurnAdvancer` | 확장 | 턴 진행 오케스트레이션(감쇠·prune·게이트·피드백·배치 영속화) | repo, loader, rumors, **feedback, rumor_params** |

- **순수 엔진**: `rumor_dynamics`(신규, 루머 생명주기) + `dynamics`(기존, 이벤트) + `promotion`(기존) — 상태 없는 함수. 서비스가 수집→호출→영속.
- **DI 원칙**: 모든 하위 서비스는 `GameMasterService`가 default-construct 또는 주입(테스트에서 대체 가능). `RumorDynamicsParams`는 Settings에서 조립돼 주입.

---

## advance_turn 오케스트레이션 (확장 시퀀스)

`TurnAdvancer.advance_turn(session_id, *, promotion_threshold)`:

```
0. _require_open(session_id) → session
1. 이벤트 적용 (기존, 불변)
   _apply_active_events(session)  →  events(applied/resolved/target/influenced)
   · dynamics(이벤트 순수) 사용, one_shot resolve, persistent accumulate
2. 주 대상 지역 루머 append  (FR-H2 증식 게이트)
   for region in events.target_regions:
       rumors.append_for_region(session, region, min_source_support = params.min_source_support)
3. 루머→지역 피드백  (FR-H3)  [순서: 이벤트 후, 감쇠 전 — 확정 [FD]]
   fb = feedback.apply_feedback(session, active_rumors)   → 지역 distortion 갱신
   influenced |= fb.keys()
4. support 감쇠 + prune  (FR-H1)
   rumors = repo.list_rumors(session_id)                  # 활성만
   rumor_dynamics.decay_support(rumors, reinforced = influenced_regions, decay=params.support_decay)
   survivors, prunable = rumor_dynamics.partition_prunable(rumors, floor=params.prune_floor)
   for r in prunable: r.active = False                    # soft-flag (승격 예외 Q7)
5. 승격/강등 재평가  (기존)
   res = promotion.evaluate(survivors, promotion_threshold)  # 활성만 평가
   set promoted flags + timeline
6. 배치 영속화  (FR-H5)
   repo.upsert_rumors(rumors)                             # 감쇠·prune·승격 결과 1 트랜잭션
7. bump_turn + ADVANCE_TURN 요약 타임라인(+applied/resolved/promoted/demoted/pruned/feedback)
8. return TurnResult(... + pruned_rumor_ids, feedback_regions)
```

### 결정 포인트(순서·타이밍) → FD 확정
- **피드백 vs 감쇠 순서**(스텝 3↔4): 피드백은 distortion을 올리고, 감쇠는 support를 내린다. 상호 독립적이나 influenced 집합 구성에 영향 → FD에서 확정.
- **empty-turn 감쇠**: Phase 2 [3] 수정은 "이벤트 없는 빈 턴은 support 감쇠 금지"였다. 하드닝은 support를 **생존 지렛대**로 승격하므로, 빈 턴 감쇠 여부를 FD에서 명시적으로 재결정(승격 루머는 prune 예외라 강등 위험은 완화).
- **피드백 집계식**: 고-support 밀도 / 승격 수 / 가중평균 중 택1(FD).
- **decay가 reinforced로 보는 집합**: 이벤트 influenced ∪ 피드백 지역(잠정) — FD 확정.

---

## 회귀 / 불변식 (NFR)
- **캐노니컬 격리(NFR-H2)**: 모든 쓰기는 세션 레이어. 피드백은 세션 `region_distortions`만 바꾼다. NPC 쿼리 규칙 불변.
- **결정론(NFR-H1)**: rumor_dynamics·feedback·prune·게이트는 LLM 비의존. LLM은 루머 텍스트 생성만(graceful).
- **호환(NFR-H2/H3)**: 신규 파라미터는 "무효화-근접 기본값" 지향으로 기존 Phase 2 테스트 회귀 최소화; 의도된 기대치 변경은 명시 갱신. `list_rumors` 기본이 활성만 반환하는 변화는 소스/피드백/승격 경로에 일관 적용.
- **인프라 무변경(NFR-H4)**: `active` 컬럼만 idempotent 가산.
