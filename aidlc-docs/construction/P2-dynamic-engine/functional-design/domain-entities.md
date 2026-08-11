# P2 Dynamic Engine — Domain Entities

> 결정: FD-P2 Q1=A(선형 delta) / Q2=A(min_weight 0.15) / Q3=A(one_shot 영구 bump) / Q4=A(support ±0.1/−0.05) / Q5=A(append 생성) / Q6=A(suggest_events n). additive — 캐노니컬 불변.

## 상수 (`locus/session/dynamics.py`)
| 상수 | 값 | 의미 |
|---|---|---|
| `MAX_EVENT_DELTA` | `0.3` | magnitude=1.0일 때 한 턴 최대 distortion 증가분 (FD-P2 Q1) |
| `PROPAGATE_MIN_WEIGHT` | `0.15` | 전파 임계 best_path_weight (consensus rumor_min 일치, FD-P2 Q2) |
| `SUPPORT_REINFORCE` | `0.1` | 영향 리전 소문 support 증가분 (FD-P2 Q4) |
| `SUPPORT_DECAY` | `0.05` | 비영향 리전 소문 support 감소분 (FD-P2 Q4) |

## 신규 타입

### EventDraft (`locus/session/event_suggester.py`, LocusModel)
LLM 제안의 미커밋 표현(영속 전).
| 필드 | 타입 | 설명 |
|---|---|---|
| `region_id` | str | 제안 대상 리전 |
| `category` | EventCategory | 분류 |
| `description` | str | 사건 설명 |
| `magnitude` | float ∈[0,1] | 강도 |

### TurnResult (확장, `game_master.py`) — 기존 필드 유지(additive)
| 필드(추가) | 타입 | 설명 |
|---|---|---|
| `applied_event_ids` | list[str] | 이 턴에 적용된 활성 Event ids |
| `resolved_event_ids` | list[str] | 이 턴에 자동 resolved 된 one_shot ids (정보용) |
- 기존: `session_id`, `turn`, `promoted_ids`, `demoted_ids`.

## dynamics 순수 함수 시그니처
```python
def distortion_delta(magnitude: float) -> float        # magnitude * MAX_EVENT_DELTA
def propagate_delta(region_id, base_delta, connections, *, min_weight=PROPAGATE_MIN_WEIGHT) -> dict[str,float]
def apply_deltas(current: dict[str,float], deltas: dict[str,float]) -> dict[str,float]   # +clamp[0,1]
def restore_contributions(current: dict[str,float], contributions: dict[str,float]) -> dict[str,float]  # −clamp
def evolve_support(rumors, influenced_region_ids, *, reinforce=SUPPORT_REINFORCE, decay=SUPPORT_DECAY) -> list[SessionRumor]
```
- 모두 순수(부수효과/LLM/DB 없음) → PBT 대상(NFR-P4).

## 기존 엔티티 재사용/변경
- `SessionEvent`(P1): advance_turn이 `contributions`를 채우고 one_shot은 status→RESOLVED. (P1 모델 변경 없음)
- `RegionDistortion`: advance_turn이 동적 갱신(set_region_distortion).
- `SessionRumor`: support 진화 + 주 대상 리전 append 생성.
- 캐노니컬 모델 변경 없음(읽기 참조만).
