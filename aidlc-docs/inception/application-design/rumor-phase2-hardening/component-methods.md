# 하드닝 & 루머 동역학 — Component Methods

> 시그니처(입출력·타입) 수준. 구체 비즈니스 규칙·수치·공식·decay 타이밍은 per-unit
> Functional Design에서 확정(`[FD]` 표기). 모든 신규 순수 함수는 결정론·부수효과 없음(NFR-H1).

---

## CH1. rumor_dynamics (순수 모듈) — `locus/session/rumor_dynamics.py`

```python
class RumorDynamicsParams(LocusModel):   # frozen; ConsensusParams 패턴
    support_decay: float          # 강화되지 않은 루머의 턴당 감쇠량      [FD]
    prune_floor: float            # 이 값 미만이면 정리 대상               [FD]
    min_source_support: float     # 자동 증식 소스 자격 임계값             [FD]
    feedback_weight: float        # 지역 피드백 delta 스케일               [FD]
    high_support_threshold: float # 피드백 집계 시 "강한 루머" 기준        [FD]

DEFAULT_RUMOR_DYNAMICS: RumorDynamicsParams   # 모듈 상수(무효화-근접 기본값 고려)
```

| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `decay_support` | `(rumors: list[SessionRumor], reinforced_region_ids: set[str], *, decay: float) -> list[SessionRumor]` | 강화되지 않은(=reinforced 아님) 루머 support를 `decay`만큼 감쇠, clamp[0,1]. 리스트 in-place 진화 후 반환(영속은 호출자). `[FD]` empty-turn 포함 여부 |
| `is_prunable` | `(rumor: SessionRumor, *, floor: float) -> bool` | `support < floor` **and** `not rumor.promoted`(Q7=A 예외). 순수 판정 |
| `partition_prunable` | `(rumors: list[SessionRumor], *, floor: float) -> tuple[list[SessionRumor], list[SessionRumor]]` | (생존, 정리대상)으로 분할. 호출자는 정리대상을 `active=False`로 표시 |
| `is_eligible_source` | `(rumor: SessionRumor, *, min_support: float) -> bool` | `support ≥ min_support`. FR-H2 자동 append 소스 게이트 |
| `region_feedback` | `(rumors: list[SessionRumor], *, weight: float, high_support_threshold: float) -> dict[str, float]` | 지역별 강-support/승격 루머 밀도를 집계해 지역 distortion delta 산출(FR-H3). 집계 방식은 `[FD]`(고-support 밀도 vs 승격 수 vs 가중평균) |

- 규칙: pruned(`active=False`) 루머는 `region_feedback`·자격 판정에서 제외(호출자가 활성 리스트 전달 또는 함수 내 필터 — `[FD]`).

---

## CH2. RumorFeedbackService — `locus/session/rumor_feedback_service.py`

```python
class RumorFeedbackService(SessionAppService):
    def __init__(self, repo: SessionRepository,
                 params: RumorDynamicsParams = DEFAULT_RUMOR_DYNAMICS) -> None: ...
```

| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `apply_feedback` | `(session: GameSession, rumors: list[SessionRumor]) -> dict[str, float]` | 활성 루머로 `rumor_dynamics.region_feedback` 계산 → 지역 distortion을 repo로 갱신, 변화 지역→delta 맵 반환(TurnAdvancer가 influenced에 합산). 부수효과(distortion 쓰기)만 담당; 순수 집계는 CH1 위임 |

- 타임라인: 피드백 적용은 advance_turn 요약에 포함(별도 엔트리 여부 `[FD]`).

---

## CH3. RumorService (확장) — `locus/session/rumor_service.py`

| 메서드 | 변경 | 목적 |
|---|---|---|
| `append_for_region` | `(session, region_id, *, min_source_support: float | None = None) -> list[SessionRumor]` | TurnAdvancer가 자격 임계 전달 → 자동 증식 게이트 적용(FR-H2) |
| `_collect_sources` | `(world_id, region_id, session_id, *, min_source_support: float | None = None) -> list[tuple[...]]` | `min_source_support`가 있으면 **세션 루머 소스**를 `is_eligible_source`로 필터. 캐노니컬 direct/propagated는 게이트 대상 아님. `None`이면 기존 동작 |
| `_collect_sources`(내부) | 활성 루머만 소스로 | pruned(`active=False`) 루머는 소스에서 제외 |

- 기존 `list_rumors`/`generate_rumors`/`regenerate_region`/`adjust_support` 시그니처·동작 불변(수동 경로).

---

## CH4. TurnAdvancer (확장) — `locus/session/turn.py`

```python
def __init__(self, repo, loader, rumors: RumorService,
             feedback: RumorFeedbackService,
             params: RumorDynamicsParams = DEFAULT_RUMOR_DYNAMICS) -> None: ...
```

| 메서드 | 변경 | 목적 |
|---|---|---|
| `advance_turn` | 스텝 추가(순서=services.md) | 감쇠+prune(H1) → 게이트 append(H2) → 피드백(H3) → 승격/강등 → 배치 영속화(H5) → bump |
| `_decay_and_prune`(신규 내부) | `(session, rumors) -> list[str]` | `rumor_dynamics.decay_support` + `partition_prunable`; 정리대상 `active=False` 표시, 정리 id 목록 반환(타임라인용) |
| `_apply_active_events` | 불변(이벤트 동역학은 `dynamics.py` 그대로) | Phase 2 동작 유지 |
| (영속화) | `self._repo.upsert_rumors(rumors)` 1회 | 스텝별 단건 upsert 루프 제거(FR-H5) |

- `TurnResult`: `pruned_rumor_ids: list[str]`, `feedback_regions: list[str]`(또는 delta) 추가(가산, 기존 필드 유지).

---

## CH5. SessionRumor (모델 확장) — `locus/session/models.py`

```python
class SessionRumor(LocusModel):
    ...
    active: bool = True   # soft-flag; prune 시 False (행 보존, NFR-H2)
```

---

## CH6. SessionRepository (포트 + 어댑터) — `repository.py` (+ memory/postgres)

| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `upsert_rumors` (신규) | `(rumors: list[SessionRumor]) -> list[SessionRumor]` | 단일 트랜잭션 배치 upsert, 저장 리스트 반환(FR-H5, Q6=A) |
| `list_rumors` (확장) | `(session_id, region_id=None, *, include_pruned: bool = False) -> list[SessionRumor]` | 기본 `active=True`만. `include_pruned=True`면 전체 |
| `ensure_schema` (확장) | `() -> None` | `session_rumors.active` 컬럼 idempotent 가산(`ADD COLUMN IF NOT EXISTS`) |

- 어댑터: 인메모리(dict 필터), Postgres(Boolean 컬럼 + `_row_to_rumor`에 `active` 매핑), SQLite 오프라인 테스트.

---

## CH7. Settings (확장) — `locus/config/settings.py`

| 항목 | 내용 |
|---|---|
| 신규 필드 | `rumor_support_decay`, `rumor_prune_floor`, `rumor_min_source_support`, `rumor_feedback_weight`, `rumor_high_support_threshold` (alias=대문자 env, 기본값 `[FD]`) |
| 팩토리 | `RumorDynamicsParams`로 조립(예: `settings.rumor_dynamics_params()` 또는 조립 헬퍼) → CH8이 서비스에 주입 |

---

## CH8. GameMasterService (코디네이터) — `locus/session/game_master.py`

| 메서드 | 변경 | 목적 |
|---|---|---|
| `__init__` | `RumorFeedbackService`·`RumorDynamicsParams` 조립 후 `TurnAdvancer`에 주입(미주입 시 default) | DI 확장, 공개 API 불변 |
| `advance_turn` | 위임 시그니처 호환 | 코디네이터 유지 |

---

## CH9. session API — `api/routers/session.py`
- `advance-turn` 응답 모델에 `pruned_rumor_ids`/`feedback_regions` 표면화(선택적). 신규 라우트 없음.

## CH10. web SessionPanel — `web/src/`
- `refresh()` 내부 read를 `Promise.all([...])`로 병렬화(FR-H6). 공개 동작 불변.

## CH11 / CH12 (U-H2, 조사 우선)
- `orchestrator.build_world`: wiki 주입 vs `topology.build` 순서 조사 → 결함 시 순서 수정(FR-H7).
- `map_image_ingestor`: barrier terrain(연결≠2) 드롭 조사 → 결함 시 orphan/경고/규칙 보강(FR-H8).
