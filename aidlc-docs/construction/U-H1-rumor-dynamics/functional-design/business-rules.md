# U-H1 Rumor Dynamics — Business Rules

> BR-H1-*. additive; 캐노니컬 불변; Phase 1/2 회귀 0. FD-H Q1..Q6 = all A.

| ID | 규칙 |
|---|---|
| **BR-H1-1** | support 감쇠는 **매 턴** 실행(빈 턴 포함, FD-H Q1=A). 강화되지 않은 활성 루머의 support를 `support_decay`(0.05)만큼 감소, clamp[0,1]. |
| **BR-H1-2** | "강화됨"(감쇠 면제) = 이번 턴 **이벤트 influenced ∪ 피드백 지역**에 속한 루머(Q2=A). 그 외 활성 루머는 감쇠. |
| **BR-H1-3** | 승격(`promoted=True`) 루머는 감쇠 **면제**(FD-H Q6=A). 감쇠·피드백 집계엔 정상 참여하되 support는 감쇠로 줄지 않음. |
| **BR-H1-4** | prune 판정: `not promoted and support < prune_floor`(0.05) → 정리 대상(Q7=A 승격 예외). |
| **BR-H1-5** | prune은 **soft-flag**: `active=False`로 표시, 행 보존(Q2=B). 하드 삭제 없음. 이력/타임라인 유지. |
| **BR-H1-6** | pruned(`active=False`) 루머는 감쇠·피드백·소스 수집·승격 평가에서 **완전 제외**(Q6=A). `list_rumors` 기본은 활성만; `include_pruned=True`로만 노출. |
| **BR-H1-7** | 증식 자격(FR-H2): 자동 append 소스 수집 시 **세션 루머 소스**는 `support ≥ min_source_support`(0.3)만 재사용. 캐노니컬 direct/propagated 소스는 게이트 대상 아님. |
| **BR-H1-8** | 수동 경로(`generate_rumors`/`regenerate_region`)는 `min_source_support=None` → 게이트 미적용(기존 동작 불변). |
| **BR-H1-9** | 루머→지역 피드백(FR-H3): `delta[region] = feedback_weight × (강한 루머 수 / 지역 활성 루머 수)`, 강한 = `support ≥ high_support_threshold`(0.6). 밀도 0이면 delta 없음(Q4=A). |
| **BR-H1-10** | 피드백 적용은 지역 `distortion_degree += delta`, clamp[0,1]. 변화 지역은 reinforced 집합에 포함(BR-H1-2). |
| **BR-H1-11** | 동역학 순수 함수(decay/prune 판정/자격/피드백)는 **활성 루머만** 입력받음(호출자 필터 or 함수 내 `active` 필터). |
| **BR-H1-12** | advance_turn 스텝 순서(FD-H Q5=A): 이벤트 적용 → 게이트 append → **피드백 → 감쇠 → prune** → 승격/강등 → **배치 upsert** → bump → timeline. |
| **BR-H1-13** | support 영속화는 턴당 **1 트랜잭션** `upsert_rumors(active)`(FR-H5, Q6=A). 강화·감쇠·prune(active)·승격 플래그가 모두 반영된 리스트를 한 번에 저장. |
| **BR-H1-14** | `TurnResult`는 `pruned_rumor_ids`·`feedback_regions` **필드 추가만**(기존 필드/소비자 호환). |
| **BR-H1-15** | 신규 파라미터는 `RumorDynamicsParams`(frozen)로 묶고 `Settings`에서 조립(FR-H4/Q5=B). 순수 함수는 인자로 수령(기본 `DEFAULT_RUMOR_DYNAMICS`) — 결정성·PBT 보존. |
| **BR-H1-16** | 스키마 변경은 `session_rumors.active` idempotent 가산 컬럼만(NFR-H4). 기존 행 default TRUE. |
| **BR-H1-17** | 동역학 전 과정 **LLM 비의존·결정론**(NFR-H1). LLM은 루머 텍스트 생성만(graceful, 실패 시 빈 체인·턴 진행). |
| **BR-H1-18** | 캐노니컬(Neo4j/OpenSearch) 불변·NPC 세션 쿼리 규칙 불변(NFR-H2). 피드백은 세션 `region_distortions`만 변경. |
| **BR-H1-19** | 닫힌 세션 쓰기 금지(advance_turn) → SessionClosedError. 읽기 허용(Phase 1/2 가드 계승). |
| **BR-H1-20** | 이벤트 support 강화(+`SUPPORT_REINFORCE`)는 기존 `dynamics.evolve_support`가 담당하되 advance_turn은 **`decay=0.0`** 으로 호출(강화만); 모든 감쇠는 `rumor_dynamics.decay_support`가 소유(이중 감쇠 방지, 피드백 지역 면제 정합). |
| **BR-H1-21** | 신생 루머는 `birth_support`(0.2, FD-H Q7=A)로 태어나 바닥 위에서 시작 → 강화 없으면 몇 턴에 걸쳐 감쇠 후 정리(즉시 사멸 방지). 제너레이터 직접 호출은 기본 0.0(Phase 1/2 호환); `RumorService`가 `RumorDynamicsParams.birth_support`를 주입. |

## 결정론 / 경계 시나리오
- 동일 루머 집합·파라미터 → 동일 감쇠·prune·피드백 결과(PBT).
- 신생 루머(support 0.0): 자동 증식 소스 자격 없음(< 0.3) + 강화 없으면 다음 턴부터 감쇠 → 몇 턴 내 prune(< 0.05).
  이벤트/피드백으로 support가 오른 루머만 생존·증식 → 지수 증가 억제([2] 근본 해결).
- 승격 루머: 감쇠·prune 면제. 강등(support < 0.6)돼도 삭제 안 됨 — 이후 강화 없으면 강등만, 유지.
- 피드백 루프: 고-support 밀집 지역 distortion↑ → 그 지역 신규 루머의 distortion_degree↑(체인 캡) → 강한 소문이
  지역을 계속 다이나믹하게(이벤트 없어도). weight=0.1로 한 턴 폭주 방지, clamp 1.0 상한.

## 회귀 관리 (기존 Phase 2 테스트)
- **의도된 변경**: [3] "빈 턴 감쇠 금지"는 FD-H Q1=A로 **뒤집힘** — 관련 테스트(`test_empty_turn_does_not_decay_support`)는
  새 정책(빈 턴 감쇠 O, 단 승격 루머는 강등만/삭제 없음)으로 **명시적 갱신** 필요.
- **무효화-근접 기본값**: 피드백/증식 게이트는 기존 테스트가 강한 루머·이벤트 위주라 대부분 영향 적음.
  깨지는 케이스는 기대치 갱신 또는 파라미터를 테스트 국소로 무효화(min_source_support=0 등).

## 테스트 포인트 (U-H1)
- **PBT(순수)**: decay 단조·범위·승격/reinforced 면제; is_prunable 경계(floor, 승격 예외); is_eligible_source 경계;
  region_feedback 밀도 ∈ [0,1]·delta 부호·clamp.
- **advance_turn 통합**(in-memory repo, mock LLM): 감쇠→prune(soft-flag), 승격 예외, 게이트 append(자격 미달 소스 제외),
  피드백 distortion↑+reinforced 면제, 배치 upsert 1회, TurnResult 신규 필드.
- **생명주기 시나리오**: 신생 루머 몇 턴 내 prune; 강한 루머 생존·증식; 승격 루머 강등만·유지; 피드백으로 이벤트 없는 지역 유지.
- **배치 어댑터**(SQLite 오프라인): `upsert_rumors` 다건 1 트랜잭션, `list_rumors(include_pruned)` 필터, `active` 컬럼 가산.
- **회귀**: Phase 1/2 NPC 쿼리·수동 소문·이벤트 동역학 불변([3] 테스트만 의도적 갱신).
