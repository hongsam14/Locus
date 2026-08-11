# S2 (Rumor Engine) — Functional Design Plan

App Design: `inception/application-design/rumor-session/`. FR-R2 + FR-R3 + FR-R4 + FR-R5.
의존: S1(models/port/SessionService) + 기존 `QueryEngine`/`ConsensusEngine`/`WorldLoader`/`LLMProvider`(무변경 재사용).

## 작업 체크리스트 (답변 후 생성)
- [x] domain-entities.md — `RumorDraft`(LLM structured output), `PromotionResult`/`TurnResult` 결과 타입, `canonical_known` helper, 강도 체인 상수. SessionRumor 모델 변경 없음.
- [x] business-logic-model.md — RumorGenerator(강도 체인·confidence·graceful), PromotionPolicy(순수), GameMasterService(generate/regenerate/adjust_support/set_distortion/advance_turn + Timeline), SessionQueryEngine(캐노니컬+오버레이), 세션 API 확장, 와이어링
- [x] business-rules.md — 왜곡/체인/confidence/승격·강등/턴/타임라인/NPC 쿼리 규칙

생성: `construction/S2-rumor-engine/functional-design/{domain-entities,business-logic-model,business-rules}.md` (2026-06-15). 답변: Q1=A/Q2=direct+propagated+세션Rumor/Q3=A/Q4=A/Q5=A/Q6=A/Q7=A.

---

## 설계 확인 질문 (S2 결정)

### FD-S2 Q1 — 강도별 체인 degrees와 region distortion_degree 관계
FR-R2.3(약→중→강 다단계 체인) + FR-R2.5(리전 `distortion_degree` 사용)를 어떻게 결합?

A) **리전 degree = 체인의 최댓값(상한)**: 기본 3단계 체인을 `[0.34·d, 0.67·d, d]`로 스케일(d=리전 distortion). 리전이 약하면 전체 체인이 약하게, 강하면 강하게.
B) 고정 체인 `[0.2, 0.5, 0.8]` 사용, 리전 degree는 무시(단순)
C) 리전 degree 단일 단계만(체인 길이 1 = d)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S2 Q2 — 소문 생성 원본(캐노니컬 Knowledge) 범위
`generate_rumors(region)`이 어떤 Knowledge에서 소문을 만드나?

A) **그 리전의 direct Knowledge만**(SCOPED_TO direct). 명확·국소적
B) direct + inherited + global (그 리전 NPC가 아는 전체)
C) direct + 기존 세션 Rumor(연쇄 왜곡 원본 포함)
X) Other (please describe after [Answer]: tag below)

[Answer]: X → 확정: **direct + propagated + 기존 세션 Rumor** (clarify 라운드). NPC 뷰에선 propagated 제외 → 원거리 정보는 (왜곡된) 소문으로만 리전 도달.

### FD-S2 Q3 — 체인 linking 의미(distorted_from)
다단계 체인에서 각 단계의 원본은?

A) **이전 단계 텍스트를 다시 왜곡**(진짜 연쇄): degree[i] 소문의 `distorted_from_id` = degree[i-1] 소문 id, `kind=rumor`. 첫 단계만 원본 Knowledge. (FR-R2.2/2.3)
B) 매 단계가 원본 Knowledge를 독립 왜곡: 모든 `distorted_from_id` = 원본 Knowledge id
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S2 Q4 — regenerate_region(재생성) 시 기존 소문 처리
리전 재생성(re-roll) 시?

A) **그 리전의 세션 Rumor 전체 삭제 후 재생성**(승격된 것 포함). 깨끗한 re-roll
B) 승격된 Rumor는 보존하고 비승격만 삭제·재생성
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S2 Q5 — support 초기값 & 승격 threshold
생성 소문의 초기 support와 advance_turn 승격 기준은?

A) **초기 support=0.0, threshold=0.6 기본**(수동으로 올려야 승격). 명시적·기획자 주도
B) 초기 support = confidence(원본 신뢰 반영), threshold=0.6
C) 초기 support=0.0, threshold는 세션/설정값으로 가변
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S2 Q6 — 승격 Rumor의 NPC 쿼리 표현
승격된 Rumor를 NPC 결과에 어떻게 노출?

A) **direct-like KnowledgeView**(`scope_type=direct`, `is_rumor=True` 유지) — direct처럼 취급하되 출처가 소문임은 표시(투명). (FR-R3.2)
B) 완전히 Knowledge로 위장(`is_rumor=False`)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S2 Q7 — SessionQueryEngine의 캐노니컬 접근 방식
"기존 QueryEngine 무변경" 하에서 direct+inherited+global만 취하고 propagated/auto-rumor를 빼려면?

A) **`query/engine.py`에 순수 helper 추가**(예: `canonical_known(view)` = direct+inherited+global), SessionQueryEngine이 `WorldLoader`+`ConsensusEngine`로 view를 얻어 helper로 필터 후 세션 오버레이 합성. QueryEngine 클래스는 무변경(추가만). (FR-R5.1/5.2)
B) SessionQueryEngine 내부에 필터 로직 자체 구현(헬퍼 추가 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A (설명 후 확정 — query/engine.py에 순수 helper `canonical_known` 추가, QueryEngine 클래스 무변경)

---

## 참고 (S1에서 확정된 계약 — 변경 없음)
- `SessionRumor`(degree/support/confidence/promoted/distorted_from_id/kind), `TimelineKind`(GENERATE/REGENERATE/PROMOTE/DEMOTE/ADJUST_SUPPORT/ADVANCE_TURN/SET_DISTORTION), `SessionRepository` 포트(upsert/list/delete rumor, get/set distortion, bump_turn, append/list timeline).
- confidence = 원본 confidence × (1 − degree) (FR-R2.6, 고정).
- graceful(NFR-R4): LLM 실패 단계는 생략, 성공분만 저장, 타임라인에 부분 결과 기록, 턴 진행 계속.
