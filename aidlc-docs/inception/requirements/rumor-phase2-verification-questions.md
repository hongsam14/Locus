# Rumor / Game-Session **Phase 2** — 요구사항 확인 질문

> **사이클**: 완료된 Phase 1(S1+S2+S3, PostgreSQL 세션 레이어 / 191 offline tests GREEN) 위 **brownfield 신규 기능**.
> **범위**: Phase 1에서 deferred 된 **Event + Event 상호작용 → 동적 distortion 진화**
> (참조: `rumor-distortion-requirements.md` §7 Out of Scope, §4 FR-R4.3).
> **호환 정책(불변식)**: 캐노니컬 레이어(Neo4j/OpenSearch)는 **불변**. 세션 레이어(PostgreSQL)에 **additive**.
> 기존 177 backend + 14 frontend 테스트 GREEN 유지, ruff/black/tsc 클린.

## 배경 — Phase 1에서 합의된 "Phase 2의 씨앗"
- Phase 1 Q4 답변: distortion_degree 는 *"이벤트, 혹은 루머 그 자체가 리전에 영향을 미친다"* 는 개념으로 **동적으로 바뀔 예정** → 그래서 Event / Timeline 개념이 도입됨.
- 현재 상태: `RegionDistortion`(per-region degree)·`GameMasterService`(턴/생성/승격)·`TimelineEntry`·`SessionRepository` 포트는 존재. **Event 엔티티·이벤트→distortion 진화·support 자동 진화는 아직 없음**(수동/정적).

아래 각 `[Answer]:` 뒤에 선택지(A/B/C…)를 적어주세요. 맞는 게 없으면 마지막 **X) Other**.

---

## A. Event 개념 & 데이터 모델

### Question 1
Phase 2의 **Event**를 어디에 어떻게 저장하나요?

A) 세션 레이어 PostgreSQL에 **신규 `SessionEvent` 엔티티/테이블**(additive). 캐노니컬 불변, `SessionRepository` 포트로 접근.
B) 별도 엔티티 없이 **기존 `TimelineEntry`(kind=event)** 에 payload로만 기록(가벼움).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 2
Event의 **핵심 속성**은? (최종 필드는 Functional Design에서 확정)

A) 자유 텍스트 `description` + 수치 강도 `magnitude`(0~1) + 대상 region(s) + 발생 turn
B) 위 + **사전 정의 카테고리**(enum: war/disaster/festival/plague/… 등)로 분류
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 3
Event의 **대상 범위**는?

A) **단일 리전**만 영향
B) **여러 리전**(복수 선택) 동시 영향
C) **단일 리전 + 토폴로지 거리 기반 이웃 감쇠 전파**(consensus의 거리 전파 재사용)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## B. Event 생성 주체

### Question 4
Event는 **누가/어떻게** 생성하나요?

A) **GameMaster(사용자)가 웹에서 수동 생성**(description·magnitude·대상 리전 입력)
B) **LLM이 세션 상태를 보고 자동 생성/제안**
C) **A + B**(수동 생성 + LLM 제안·자동 생성 둘 다 지원)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## C. Event → distortion 동적 진화 (핵심)

### Question 5
Event가 리전의 `distortion_degree`를 바꾸는 **방식**은?

A) **결정론적 공식**(magnitude → distortion delta, [0,1] clamp). 순수 로직, 테스트 용이.
B) **LLM이 해석**해 새 distortion 제안(graceful 실패 시 결정론적 공식으로 폴백).
C) **A(결정론적) + 토폴로지 전파**(이웃 리전에 거리 감쇠 delta 적용).
X) Other (please describe after [Answer]: tag below)

[Answer]: C

### Question 6
Event 효과의 **적용 시점**은?

A) **`advance_turn` 시 일괄 처리** — 그 턴에 등록된 Event들을 모아 distortion 갱신 → 소문/승격 재평가 → 타임라인 기록(턴 기반 시뮬레이션).
B) **Event 생성 즉시** distortion에 반영(턴과 무관).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Question 7
Event 적용 후 **기존/신규 Rumor** 처리는?

A) **distortion만 갱신**하고 소문 재생성은 GameMaster가 수동(기존 `regenerate_region` 사용).
B) Event 적용 시 **대상 리전 소문 자동 재생성**(새 distortion 반영).
C) Event가 **기존 소문의 support/텍스트를 동적으로 조정**(LLM 해석).
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 결국 위의 advance_turn에서 소문/승격 재평가 + 소문 재생성이 되겠지.

---

## D. "루머가 리전에 영향" 피드백 루프

### Question 8
Phase 1 Q4에서 언급된 *"루머 그 자체가 리전에 영향"* 을 Phase 2에서 구현하나요?

A) **구현** — 승격된(promoted) 소문 수/지지도가 그 리전 distortion을 끌어올리는 **피드백 루프**(턴마다 반영).
B) **이번엔 제외** — Phase 2는 **Event 구동 distortion**에만 집중, 루머 피드백은 다음(Phase 3).
C) **구현(완화형)** — 턴마다 리전 distortion이 그 리전 소문들의 평균/최대 distortion 쪽으로 점진 이동.
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## E. support 자동 진화 (Phase 1은 수동)

### Question 9
`support`(지지도) **자동 증감**을 Phase 2에 도입하나요? (Phase 1: 수동 조정만)

A) **턴 기반 자동 감쇠(decay)** — 방치 시 support 하락 → threshold 미만이면 자동 강등.
B) **강화 시 증가 + 미강화 시 감쇠** — Event/재생성으로 보강된 소문은 support↑, 아니면 ↓.
C) **수동 유지** — support 자동화는 Phase 2 범위 밖(Event/distortion에 집중).
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## F. Event 생애주기

### Question 10
Event는 **일회성**인가 **지속성**인가?

A) **일회성** — 발생/적용 턴에 1회 효과 적용 후 타임라인 기록으로만 남음.
B) **지속성** — 여러 턴에 걸쳐 효과 유지, 명시적 해소/만료(expire)까지 매 턴 영향.
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 이벤트 타입에 따라 일회성인지 지속성인지 다를 듯.

---

## G. NPC 쿼리 & 회귀

### Question 11
Phase 2가 **NPC 쿼리 규칙**(현재: direct+inherited+global Knowledge + 승격 Rumor + Rumor, propagated 비노출)을 바꾸나요?

A) **변경 없음** — Phase 2는 distortion/소문 *값*만 동적으로 진화시키고, NPC 노출 규칙은 Phase 1 그대로 유지.
B) 변경 필요(아래 Other에 기술).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## H. 웹 UI 범위

### Question 12
Phase 2 **웹 UI** 범위는?

A) **풀 UI** — SessionPanel에 Event 생성 폼 + Event 목록/타임라인 표시 + 변화된 per-region distortion 시각화.
B) **백엔드/API만** — 웹은 다음 사이클.
C) **최소 UI** — Event 생성 버튼 + 목록만(고급 시각화 제외).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## I. 영속화 & 포트

### Question 13
`SessionRepository` 포트 확장 방식은?

A) **기존 포트에 Event CRUD 메서드 추가**(PostgreSQL 어댑터 + in-memory mock 둘 다 구현, 기존 시그니처 불변 — additive). `init-schema`에 `session_events` 테이블 추가.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## J. Extension Opt-In (이번 사이클 적용 여부 재확인)

> 참고: 이전 사이클 설정 — Security=**No**, PBT=**Partial**. Phase 2도 동일 유지하려면 같은 선택지를 적어주세요.

### Question: Security Extensions
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question: Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?

A) Yes — enforce all PBT rules as blocking constraints (recommended for projects with business logic, data transformations, serialization, or stateful components)
B) Partial — enforce PBT rules only for pure functions and serialization round-trips (suitable for projects with limited algorithmic complexity)
C) No — skip all PBT rules (suitable for simple CRUD applications, UI-only projects, or thin integration layers with no significant business logic)
X) Other (please describe after [Answer]: tag below)

[Answer]: B
