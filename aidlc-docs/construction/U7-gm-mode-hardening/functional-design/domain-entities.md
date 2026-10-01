# U7 GM 모드·안정화 — Domain Entities

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U7 기능 설계 중 데이터 정의입니다.
- 되먹임 몫, 새 타임라인 종류, 세계 상태 읽기 모델, 조정값, 포트 변경을 고정합니다.
- 모든 변경은 **추가**입니다. 예외는 §7 "설계 이탈"에 모읍니다.

근거
- **답**: FD-U7 Q1=B(두 화면 전환), Q2=A(복원+상한), Q3=A(내 행동 + 그때 있던 지역의 일), Q4=A(승격 제외 + 면제 해제 + 기준 0.45)
- **가정**: 플랜 A7-1~10. 이 문서는 그중 A7-1·A7-5를 답에 맞춰 고쳐 쓴다(§7).

## 1. 왜곡도와 되먹임 몫

### 1.1 `RegionDistortion` (필드 추가)
| 필드 | 타입 | 뜻 |
|---|---|---|
| `session_id`, `region_id`, `distortion_degree` | (그대로) | |
| `feedback_share` | `float`, `0 ≤ x ≤ 1`, 기본 `0.0` | 지금 `distortion_degree` 중 **되먹임이 올린 몫**. 되먹임이 올릴 때 늘고, 복원할 때 준다. `feedback_cap`을 넘지 않는다(BR-U7-3). GM이 왜곡도를 직접 정하면 0이 된다(BR-U7-5) |

- 이 몫은 왜곡도에 **이미 들어 있는** 양을 기록할 뿐이다. 따로 더하지 않는다.
- 사건 기여(`SessionEvent.contributions`)와 되먹임 몫은 서로 섞지 않는다. 사건 해소는 자기 기여만 되돌리고 몫은 그대로 둔다.

### 1.2 되먹임 계산 값 (순수 함수 입출력, `locus/play/rumor/dynamics.py`)
```python
@dataclass(frozen=True)
class FeedbackState:          # 한 지역의 입력
    degree: float             # 지금 왜곡도
    share: float              # 지금 되먹임 몫

@dataclass(frozen=True)
class FeedbackStep:           # 한 지역의 출력
    degree: float
    share: float
    raised: float             # 이번 턴 되먹임이 실제로 올린 양 (상한·clamp 뒤, ≥ 0)
    restored: float           # 이번 턴 되돌린 양 (≥ 0)
```
- `region_feedback(rumors, *, weight, high_support_threshold) -> dict[str, float]`
  - 시그니처는 그대로다. **승격 소문을 세지 않는다**(BR-U7-1).
- `step_feedback(states, deltas, *, cap, restore) -> dict[str, FeedbackStep]`
  - 새 순수 함수다(BR-U7-2~4).
  - 출력 키는 `deltas`의 지역과 `share > 0`인 지역의 합집합이다.

## 2. 타임라인 (추가만; 페이로드에 `region_id`·`region_name`, FR-D3)

### 2.1 새 종류 (`TimelineKind` 끝에 추가, 순서 보존)
| 값 | 언제 | 페이로드 |
|---|---|---|
| `event_suggested` | LLM 제안 하나가 SUGGESTED로 저장될 때 | `event_id, region_id, region_name, category, magnitude, description` |
| `event_approved` | SUGGESTED → ACTIVE | `event_id, region_id, region_name, category` |
| `event_discarded` | SUGGESTED 폐기(행 삭제 전) | `event_id, region_id, region_name, category, description` — 행이 사라지므로 무엇이었는지를 여기 남긴다 |

- `event_created`는 GM 직접 생성에만 쓴다.
- 지난 기록의 `event_created` + `suggested/approved: true` 줄은 그대로 둔다. 화면 템플릿은 두 형태를 다 읽는다.

### 2.2 기존 종류의 페이로드 보강 (D3, 새로 쓰는 줄부터)
| 종류 | 더하는 키 |
|---|---|
| `generate`, `regenerate` | `region_name`. `regenerate`는 `deleted` 대신 `deactivated`(BR-U7-16) |
| `adjust_support` | `region_id`, `region_name`(그 소문의 지역) |
| `set_distortion` | `region_name`, `feedback_share_cleared`(지운 몫) |
| `event_created`, `event_applied`, `event_resolved` | `region_name`. `event_resolved`는 `region_id`도 |
| `promote`, `demote`, `prune` | `region_id`, `region_name` |
| `advance_turn` | `feedback_restored_regions`(이번 턴 몫을 되돌린 지역 id) |
| `session_started` (GM 세션) | `player: null`. 플레이어 없는 세션도 이 줄을 남긴다(BR-U7-11) |

- 지난 줄은 고치지 않는다(append-only). 이름이 없는 지난 줄은 화면이 id로 보인다.

## 3. 플레이어 로그 규칙 값 (`locus/play/player/log.py`, 순수)
```python
OWN_KINDS: frozenset[str]     # 플레이어 자신의 일 — 늘 보인다
REGION_KINDS: frozenset[str]  # 지역의 일 — 그때 플레이어가 있던 지역이면 보인다
def player_log(entries: Sequence[TimelineEntry]) -> list[TimelineEntry]
```
| 묶음 | 종류 |
|---|---|
| `OWN_KINDS` | `session_started`, `session_closed`, `player_moved`, `player_waited`, `npc_talked`, `action_declared`, `deed_recorded`, `turn_run_failed` |
| `REGION_KINDS` | `event_applied`(체류마다 사건당 첫 줄만), `event_resolved`, `promote`, `demote`, `prune`, `deed_seeded`, `rumor_spread`(도착 지역 기준) |
| 그 밖 (숨김) | `generate`, `regenerate`, `adjust_support`, `set_distortion`, `advance_turn`, `event_created`, `event_suggested`, `event_approved`, `event_discarded`, `deed_appraised`, `deed_voided` |

- 위 세 묶음은 `TimelineKind` 전체를 빠짐없이 나눈다. 새 종류가 생기면 어느 묶음인지 정해야 테스트가 통과한다(TP-U7-6).

## 4. 세계 상태 읽기 모델 (FR-D4)
```python
class RegionState(LocusModel):
    region_id: str
    region_name: str
    distortion: float            # 저장 값, 없으면 기본값 (BR-U7-18)
    feedback_share: float
    active_rumors: int           # 활성 소문 전체 (승격 포함)
    promoted_rumors: int
    deed_rumors: int             # origin_kind != "canonical" 인 활성 소문
    active_events: int           # ACTIVE 사건 (SUGGESTED·RESOLVED 제외)

class WorldState(LocusModel):
    session_id: str
    turn: int
    player_region_id: str | None # 플레이어 없는 세션은 None
    regions: list[RegionState]   # 현재 월드의 지역마다 하나, 스냅샷 지역 순서
```
- 저장하지 않는다. 읽을 때 만든다.
- 순수 집계 함수: `summarize_state(regions, distortions, rumors, events) -> list[RegionState]` (`locus/play/world_state.py`, TP-U7-7)

## 5. 조정값 (FR-A7, US-8.5)

### 5.1 `KnowledgeTuning` (env 덮어쓰기 추가; 값 불변)
| 필드 | 기본 | env |
|---|---|---|
| `propagate_min` | 0.5 | `CONSENSUS_PROPAGATE_MIN` |
| `hearsay_min` | 0.15 | `CONSENSUS_HEARSAY_MIN` |

- `Settings.knowledge_tuning()`이 env 값을 넣는다. `hearsay_min ≤ propagate_min`이 아니면 설정 오류다(기동 실패).

### 5.2 `WorldTuning` (새 dataclass, `shared/config/tuning.py`)
| 필드 | 기본 | env |
|---|---|---|
| `base_weights` | `adjacent 0.8, route 0.6, river 0.5, blocked 0.2` | `TOPOLOGY_BASE_WEIGHTS` (JSON 객체, 주어진 키만 덮어씀) |
| `default_base` | 0.5 | `TOPOLOGY_DEFAULT_BASE` |
| `terrain_modifiers` | 지금 표 그대로 | `TOPOLOGY_TERRAIN_MODIFIERS` (JSON 객체, 주어진 키만 덮어씀) |
| `dedup_threshold` | 0.86 | `ONTOLOGY_DEDUP_THRESHOLD` |

- frozen이다. 표는 `Mapping[str, float]`(`MappingProxyType`)으로 둔다.
- JSON이 깨졌거나 값이 [0,1]을 벗어나면 설정 오류다.

### 5.3 `PlayTuning` (필드 추가·기본값 하나 변경)
| 필드 | 기본 | env | 비고 |
|---|---|---|---|
| `high_support_threshold` | **0.45** (was 0.6) | `RUMOR_HIGH_SUPPORT_THRESHOLD`(있음) | Q4=A |
| `feedback_cap` | 0.3 | `RUMOR_FEEDBACK_CAP` | Q2=A |
| `feedback_restore` | 0.05 | `RUMOR_FEEDBACK_RESTORE` | Q2=A, 턴당 |
| `promotion_threshold` | 0.6 | `RUMOR_PROMOTION_THRESHOLD` | 지금 `promotion.DEFAULT_PROMOTION_THRESHOLD` |
| `event_max_delta` | 0.3 | `EVENT_MAX_DELTA` | 지금 `event/dynamics.MAX_EVENT_DELTA` |
| `event_propagate_min` | 0.15 | `EVENT_PROPAGATE_MIN` | 지금 `PROPAGATE_MIN_WEIGHT` |
| `event_support_reinforce` | 0.1 | `EVENT_SUPPORT_REINFORCE` | 지금 `SUPPORT_REINFORCE` |
| `max_event_suggestions` | 5 | `EVENT_SUGGEST_MAX` | NFR-6, US-5.2 |
| `suggest_max_regions` | 30 | `EVENT_SUGGEST_MAX_REGIONS` | 제안 프롬프트 크기 |

- 모듈 상수는 지우지 않고 `PlayTuning()` 기본값을 가리키게 둔다(기존 import 유지).
- 서비스는 생성자에서 받은 `PlayTuning`만 읽는다.

## 6. 포트·저장·오류

### 6.1 `DistortionStore`
| 메서드 | 변경 |
|---|---|
| `set_region_distortion(session_id, region_id, degree, *, feedback_share: float \| None = None)` | 키워드 인자 추가. `None`이면 몫을 그대로 둔다(행이 없으면 0) |
| `list_region_distortions(session_id)` | 시그니처 그대로. 돌려주는 `RegionDistortion`에 `feedback_share`가 실린다. 되먹임 단계는 이것으로 입력을 만든다 |

### 6.2 `RumorStore`
- `delete_rumor`는 **없앤다**(FR-E5 "삭제 방식은 하나로"). 재생성은 `active=False`로 저장한다. 다른 프로덕션 호출처는 없다.

### 6.3 `ConversationStore` (U5 C1)
- `message_counts(session_id) -> dict[str, int]`을 새로 둔다. 키는 `npc_id`, 값은 메시지 수다. 한 번의 질의(LEFT JOIN + GROUP BY)로 읽는다. 대화가 없는 NPC는 키가 없다.

### 6.4 테이블 (PostgreSQL, 추가만; 인메모리 트윈 같은 계약)
- `region_distortions.feedback_share DOUBLE PRECISION NOT NULL DEFAULT 0`. U6의 `ADDED_COLUMNS`에 한 줄을 더해 기존 DB에도 붙는다.

### 6.5 오류
| 오류 | 언제 | HTTP |
|---|---|---|
| `InvalidActionError` (있음) | SUGGESTED 사건 해소, `n` 범위 밖 | 400 |
| `LookupError` (있음) | 월드에 없는 지역의 왜곡도 설정 | 404 |
| `LlmCallFailedError` (새, `RuntimeError`) | 대화 LLM이 재시도 뒤에도 실패 | 503, 고정 문구(제공자 메시지를 싣지 않는다) |

## 7. 설계 이탈 (완결 목록)
1. **A7-1 고쳐 씀** (Q4=A)
   - 승격 소문은 되먹임에서 뺀다. 되먹임 지역은 더는 감쇠 면제가 아니다. 강한 소문 기준은 0.45다.
   - Phase 2 BR-H1-2(강화 지역 = 사건 영향 ∪ 되먹임)는 "강화 지역 = 사건 영향"으로 바뀐다.
2. **A7-5 고쳐 씀**
   - 빠진 지역의 기본값 행을 쓰지 않는다. 대신 목록·상태 읽기가 현재 월드의 지역마다 한 행을 만든다(저장 값 또는 기본값).
   - 턴 계산은 이미 빠진 지역을 기본값으로 읽는다(`apply_deltas`, 되먹임). 그래서 쓸 필요가 없다. 읽기 경로는 쓰지 않는다는 BR-U4-4와도 부딪치지 않는다.
3. **U6 frontend-components §2.5 고쳐 씀**
   - 화면의 `GM_ONLY_KINDS` 필터를 없애고 서버 필터(§3)로 옮긴다.
   - `deed_seeded`·`rumor_spread`는 **플레이어가 그 지역에 있을 때** 보인다. U6의 까닭("퍼진 곳은 여행해서 알게 된다")과 같다. 그 지역에 있을 때 생긴 일만 보이기 때문이다.
4. **U4 code-plan R-09 고쳐 씀**: 플레이어 없는 GM 세션 시작도 `session_started`를 남긴다(FR-E4 "세션 시작도 타임라인에").
5. **US-5.1 문구 "켠다/끈다"** (Q1=B)
   - 켜기는 플레이 화면의 "GM 모드" 버튼으로 `/gm/:sid`에 가는 것이고, 끄기는 GM 화면의 "플레이로 돌아가기"다.
   - 플레이어 상태는 서버에 있으므로 그대로다. GM 화면은 플레이어 위치·턴을 띠와 지도 표시로 보인다.
6. **`list_distortions`**: 월드에서 빠진 지역의 저장 행은 목록에 넣지 않는다(DB에는 남는다). 지역의 출처는 월드다.
