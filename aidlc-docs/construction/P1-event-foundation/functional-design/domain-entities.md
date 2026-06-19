# P1 Event Foundation — Domain Entities

> 결정: FD-P1 Q1=A(6-category 집합), Q2=A(region 검증), Q3=A(Phase 1 규약 계승), Q4=A(resolve=상태전이). 모두 additive — 캐노니컬 불변.

## Enums (additive in `locus/session/models.py`)

### EventCategory (str, Enum)
`WAR`, `PLAGUE`, `POLITICS`, `DISASTER`, `FESTIVAL`, `DISCOVERY`.

### EventLifecycle (str, Enum)
`ONE_SHOT`, `PERSISTENT`.

### EventStatus (str, Enum)
`SUGGESTED`, `ACTIVE`, `RESOLVED`.

### CATEGORY_DEFAULT_LIFECYCLE (dict[EventCategory, EventLifecycle])
| category | default lifecycle |
|---|---|
| WAR | PERSISTENT |
| PLAGUE | PERSISTENT |
| POLITICS | PERSISTENT |
| DISASTER | ONE_SHOT |
| FESTIVAL | ONE_SHOT |
| DISCOVERY | ONE_SHOT |

- `default_lifecycle(category) -> EventLifecycle` 헬퍼(순수). 생성 시 명시 lifecycle이 없으면 이 값 사용(override 가능, CL1.3).

### TimelineKind (확장 — 기존 값 불변)
추가: `EVENT_CREATED`, `EVENT_APPLIED`, `EVENT_RESOLVED`. (EVENT_APPLIED는 P2 advance_turn에서 사용; enum은 P1에서 함께 정의.)

## Entity: SessionEvent (`locus/session/models.py`, LocusModel)
| 필드 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `id` | str | `new_id()` | 앱 생성 uuid4 (Phase 1 규약) |
| `session_id` | str | (필수) | 소속 세션 |
| `region_id` | str | (필수) | 주 대상 리전(캐노니컬 id 참조만) |
| `category` | EventCategory | (필수) | 분류 |
| `description` | str | `""` | 자유 텍스트 |
| `magnitude` | float | (필수) | 강도 ∈[0,1] (검증) |
| `lifecycle` | EventLifecycle | category 기본값 | one_shot/persistent |
| `status` | EventStatus | (생성 경로별) | 수동=ACTIVE, 제안=SUGGESTED |
| `created_turn` | int | 0, ge=0 | 생성 시 세션 turn |
| `resolved_turn` | int \| None | None | 해소된 turn |
| `contributions` | dict[str, float] | `{}` | region_id→누적 적용 delta(복원용; P2가 채움) |
| `provenance` | Provenance | (필수) | source=세션, generated_by `gm`/`llm` |

- **불변식**: `magnitude∈[0,1]`(Field ge/le); status 전이 `SUGGESTED→ACTIVE→RESOLVED` 또는 `ACTIVE(직행)→RESOLVED`; `contributions` 값은 P2 적용 전까지 `{}`.
- **캐노니컬 참조**: `region_id`는 문자열 id만(복사/스냅샷 없음, Phase 1 BR-S1-9 계승).

## 영속 매핑 (`locus/storage/postgres_session_repo.py`, additive)
신규 테이블 `session_events` (하이브리드, FD-P1 Q3=A):
- 정규 컬럼(+인덱스): `id`(PK), `session_id`(idx), `region_id`(idx), `category`, `status`(idx), `magnitude`, `lifecycle`, `description`(Text), `created_turn`, `resolved_turn`(nullable).
- JSONB-variant: `contributions`(`_JSON`, default {}), `provenance`(`_JSON`).
- in-memory 어댑터: `dict[session_id][event_id]` (Phase 1 rumor 저장 패턴 계승, deepcopy 격리).

## 확장 타입 (P2에서 채움 — enum/필드만 P1에서 정의 가능)
- `EventDraft`(P2), `TurnResult` 확장(P2). P1 범위 아님.
