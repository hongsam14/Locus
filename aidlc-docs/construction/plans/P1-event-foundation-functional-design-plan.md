# P1 Event Foundation — Functional Design Plan

> 단위: P1 (SessionEvent 모델 + enums + SessionRepository Event CRUD + 수동 Event API). 입력: unit-of-work.md, application-design/rumor-phase2/*.
> P1은 데이터 계층 + 수동 라이프사이클(엔진 비의존). distortion 복원/적용은 P2. 기존 Phase 1 영속화 패턴(하이브리드 컬럼+JSONB-variant, app-generated id, DB server time)을 계승.

## 설계 질문 (FD-P1) — 각 `[Answer]:`에 A/B/… 또는 X) Other

### FD-P1 Q1 — EventCategory 집합 + 기본 lifecycle 매핑
요구사항이 "최종 category 집합은 FD에서 확정"이라 했습니다. 아래 집합과 기본 lifecycle 매핑을 제안합니다(생성 시 override 가능, CL1.3).

A) **제안 집합** (6종):
| category | 기본 lifecycle | 의미 |
|---|---|---|
| `WAR` | PERSISTENT | 전쟁/분쟁 — 지속 |
| `PLAGUE` | PERSISTENT | 역병 — 지속 |
| `POLITICS` | PERSISTENT | 정치 격변/통치 변화 — 지속 |
| `DISASTER` | ONE_SHOT | 자연재해(지진/홍수) — 일회성 충격 |
| `FESTIVAL` | ONE_SHOT | 축제/행사 — 일회성 |
| `DISCOVERY` | ONE_SHOT | 발견/사건 — 일회성 |

B) **최소 집합** (3종: `WAR`(persistent)/`DISASTER`(one_shot)/`FESTIVAL`(one_shot)) — 단순하게 시작.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P1 Q2 — create_event 시 region_id 검증
수동 Event 생성 시 `region_id`가 그 world의 캐노니컬 토폴로지에 존재하는지 검증할까요? (Phase 1 FD-S1 Q2=A가 start_session에서 world 존재를 검증→404한 선례)

A) **검증** — 존재하지 않는 region이면 거부(LookupError→404). 데이터 무결성.
B) **미검증** — region_id를 그대로 저장(느슨; 검증은 P2 advance_turn 적용 시).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P1 Q3 — 필드 규약 & 기본값 (Phase 1 패턴 계승 확인)
SessionEvent 필드 규약을 다음으로 확정할까요?

A) **확정** — `id=new_id()`(app 생성), `magnitude` 필수 ∈[0,1], `status` 기본 = 생성 경로별(수동=ACTIVE, 제안=SUGGESTED), `lifecycle` 미지정 시 category 기본값, `created_turn` = 생성 시 세션 turn, `resolved_turn` nullable, `contributions: dict[str,float]` 기본 `{}`(JSONB-variant), `provenance`(source=세션/ generated_by gm|llm). Phase 1 하이브리드 영속(핵심=정규 컬럼+인덱스, contributions/provenance=JSONB) 계승.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P1 Q4 — P1 resolve 동작 범위
P1의 `POST …/events/{eid}/resolve`는 어디까지 하나요? (distortion 복원은 dynamics 의존 → P2)

A) **상태전이만** — ACTIVE→RESOLVED + `resolved_turn` 기록 + EVENT_RESOLVED 타임라인. distortion 복원은 P2에서 이 메서드에 추가. (P1 시점엔 이벤트가 distortion에 적용된 적 없으므로 복원 대상도 없음 → 의미상 완결)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 산출물 (생성 완료) — `aidlc-docs/construction/P1-event-foundation/functional-design/`
- [x] `domain-entities.md` — SessionEvent + enums(EventCategory/Lifecycle/Status) + 매핑 + TimelineKind 확장 + 필드/불변식.
- [x] `business-logic-model.md` — Event CRUD/상태전이 흐름, 수동 생성/조회/해소(상태전이)/폐기, 영속 매핑.
- [x] `business-rules.md` — BR-P1-*: 검증·상태전이 규칙·기본값·세션 격리·idempotent·닫힌 세션 가드.
