# U-H1 Rumor Dynamics — Domain Entities

> FD-H Q1..Q6 = all A. additive; 캐노니컬 불변; Phase 1/2 회귀 0.
> 신규 순수 값타입 + 기존 세션 엔티티의 가산 필드만. 영속 매핑은 리포지토리 어댑터.

## 1. 확장 엔티티

### SessionRumor (확장) — `locus/session/models.py`
| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `active` | bool | `True` | soft-flag. prune 시 `False`(행 보존, 이력/타임라인). pruned 루머는 감쇠·피드백·소스·승격 평가에서 완전 제외(BR-H1-11). |
- 나머지 필드 불변(`support`가 감쇠·prune·증식자격·피드백의 핵심 변수). 기본 True로 기존 데이터·직렬화 호환.

### RegionDistortion (mutate, 스키마 불변)
- 피드백 스텝이 `distortion_degree`를 갱신(FR-H3). 필드 추가 없음.

## 2. 신규 값타입

### RumorDynamicsParams — `locus/session/rumor_dynamics.py`
결정론 파라미터 묶음(frozen, `ConsensusParams` 패턴). 순수 함수가 인자로 수령, 기본은 `DEFAULT_RUMOR_DYNAMICS`.

| 필드 | 타입 | 기본(FD-H Q3=A) | 의미 |
|---|---|---|---|
| `support_decay` | float | `0.05` | 강화되지 않은 루머의 턴당 support 감쇠량 |
| `prune_floor` | float | `0.05` | support가 이 값 **미만**이면 정리 대상(승격 예외) |
| `min_source_support` | float | `0.3` | 자동 증식 소스 자격 임계(이상만 새 왜곡 소스) |
| `feedback_weight` | float | `0.1` | 루머→지역 피드백 distortion delta 스케일 |
| `high_support_threshold` | float | `0.6` | 피드백 집계 "강한 루머" 기준(승격 임계와 일치) |

- 불변식: 전 필드 ≥ 0; 임계값 ∈ [0,1]. frozen(런타임 불변). 모듈 상수 `DEFAULT_RUMOR_DYNAMICS`.
- 출처: `Settings`(env alias) → 팩토리로 조립(FR-H4, AD-H Q5=B). 값의 중앙화만; 계산은 순수.

### TurnResult (확장) — `locus/session/turn.py`
| 필드 | 타입 | 기본 | 설명 |
|---|---|---|---|
| `pruned_rumor_ids` | list[str] | `[]` | 이번 턴 정리(soft-flag)된 루머 id |
| `feedback_regions` | list[str] | `[]` | 루머 피드백으로 distortion이 변한 지역 id |
- 기존 필드(promoted/demoted/applied_event/resolved_event ids) 유지 — 소비자 호환(BR-H1-14).

## 3. Settings (확장) — `locus/config/settings.py`
| env alias | 필드 | 기본 |
|---|---|---|
| `RUMOR_SUPPORT_DECAY` | `rumor_support_decay` | 0.05 |
| `RUMOR_PRUNE_FLOOR` | `rumor_prune_floor` | 0.05 |
| `RUMOR_MIN_SOURCE_SUPPORT` | `rumor_min_source_support` | 0.3 |
| `RUMOR_FEEDBACK_WEIGHT` | `rumor_feedback_weight` | 0.1 |
| `RUMOR_HIGH_SUPPORT_THRESHOLD` | `rumor_high_support_threshold` | 0.6 |
- 팩토리(예: `Settings.rumor_dynamics_params() -> RumorDynamicsParams`) 또는 조립 헬퍼로 CH8이 서비스에 주입.

## 4. 영속 스키마 (가산, NFR-H4)
- `session_rumors.active BOOLEAN NOT NULL DEFAULT TRUE`.
- `ensure_schema`: `CREATE TABLE IF NOT EXISTS`(신규 DB) + idempotent `ADD COLUMN IF NOT EXISTS active`(기존 DB).
- 인메모리 어댑터: `SessionRumor.active` 그대로 보존. SQLite 오프라인 테스트: Boolean 컬럼 동등.

## 5. 관계 / 불변식 요약
- `RumorDynamicsParams`는 순수 함수·서비스로 **주입**만(엔티티가 참조 보관 안 함).
- `SessionRumor.active=False` ⇒ 동역학의 모든 대상 집합에서 제외(단, `include_pruned=True` 조회 시 노출).
- 승격(`promoted=True`) ⇒ prune 예외(감쇠·피드백엔 정상 참여, FD-H Q6=A).
