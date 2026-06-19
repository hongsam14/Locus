# P2 Dynamic Engine — Functional Design Plan

> 단위: P2 (dynamics 순수 로직 + EventSuggester(LLM) + GameMasterService.advance_turn 통합 + suggest/approve API). 입력: P1 코드, application-design/rumor-phase2/*.
> 핵심: 결정론적 distortion 진화·토폴로지 전파·support 자동 진화·lifecycle/복원. 요구사항이 FD로 이연한 **공식/상수**를 여기서 확정.

## 확정된 설계 (요구사항/AD/P1에서 — 질문 아님)
- 적용 시점: `advance_turn` 일괄(FR-P3.3). 처리 순서: 활성 Event 수집 → distortion 갱신(주 대상+전파, 누적) → 주 대상 리전 소문 처리 → support 진화 → 승격/강등(promotion.evaluate) → one_shot 자동 resolve → bump_turn → Timeline.
- 전파 메커니즘: `consensus.propagation.best_path_weights` 재사용.
- 복원: persistent 해소 시 `contributions` 대칭 차감(P1 resolve_event에 추가).
- suggest→approve 분리(AD-P Q3=A): advance_turn은 LLM 비호출, ACTIVE Event만 적용. suggest_events는 별도 엔드포인트(매 턴 UI 트리거, CL2.2=B).

## 설계 질문 (FD-P2) — 각 `[Answer]:`에 A/B/… 또는 X) Other

### FD-P2 Q1 — distortion_delta(magnitude) 공식
Event magnitude(0~1)를 리전 distortion delta로 변환하는 공식은?

A) **선형 스케일** `delta = magnitude * MAX_EVENT_DELTA` (상수 `MAX_EVENT_DELTA=0.3`). 한 강한 이벤트가 한 턴에 최대 +0.3. 누적/클램프는 [0,1].
B) **직접** `delta = magnitude` (강도 그대로, [0,1] 클램프) — 한 이벤트로 급변 가능.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P2 Q2 — 토폴로지 전파 임계값
주 대상=base_delta, 이웃 = `base_delta * best_path_weight[neighbor]`. 어디까지 전파하나요?

A) **임계값 `min_weight=0.15`**(consensus rumor_min과 동일) 이상인 이웃에만 전파. 그 미만은 무시(원거리 차단).
B) 모든 도달 가능 이웃에 전파(임계값 없음).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P2 Q3 — one_shot 효과의 영속성
`one_shot` 이벤트(예: 재해/축제)는 1회 적용 후 RESOLVED 됩니다. 그 distortion 효과는?

A) **영구 bump** — 1회 적용분이 리전에 남음(복원 없음). 자연 감쇠는 이번 범위 밖(별도 baseline-decay 없음). persistent만 해소 시 복원.
B) **일시 충격** — 적용한 다음 턴에 자동 복원(decay)되어 사라짐.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

> 참고: persistent는 활성 동안 매 턴 `delta` 재적용(누적, clamp 1.0), 해소 시 누적분 복원(CL1.2=A) — 확정. Q3은 one_shot만.

### FD-P2 Q4 — support 자동 진화 상수 & 영향 집합
advance_turn마다 support 증감 규칙은? ("영향 리전" = 그 턴 distortion delta를 받은 리전 = 주 대상 + 전파 이웃)

A) **영향 리전 소문 `support += 0.1`(강화), 그 외 `support -= 0.05`(감쇠)**, [0,1] 클램프 → 이후 promotion.evaluate(threshold 0.6 재사용)로 승격/강등.
B) 비율형(예: 영향 `*1.2`, 그 외 `*0.9`).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P2 Q5 — 주 대상 리전 소문 처리 (FR-P4.1 / CL3.1=B)
Event 적용 후 주 대상 리전 소문을 "보존+갱신"하는 구체 방식은? (기존 소문/support 보존, 전체 wipe 아님)

A) **추가 생성(append)** — 기존 소문/ support 그대로 두고, 갱신된 distortion 기준으로 새 소문(체인)을 추가 생성(기존 `_generate_for_region` 재사용, wipe 없음). 소문 수는 턴마다 증가.
B) **기존 텍스트 갱신(in-place)** — 기존 소문의 distortion_degree/confidence를 새 값으로 갱신(필요 시 LLM 재왜곡), support 유지. 소문 수 불변.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-P2 Q6 — EventSuggester 출력 & 트리거
LLM 제안(suggest_events)의 동작은?

A) **`suggest_events(session_id, n=1)`** — LLM이 리전/소문/턴 컨텍스트로 최대 n건 `EventDraft` 제안 → 서비스가 `status=SUGGESTED`로 영속(provenance llm). graceful: LLM 실패 시 빈 리스트. 별도 엔드포인트(UI가 매 턴 호출).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 산출물 계획 (답변 후 생성) — `aidlc-docs/construction/P2-dynamic-engine/functional-design/`
- [x] `domain-entities.md` — EventDraft, TurnResult 확장 필드, dynamics 함수 시그니처/상수.
- [x] `business-logic-model.md` — advance_turn 통합 시퀀스 상세(의사코드), dynamics 순수 함수, EventSuggester, resolve 복원, approve.
- [x] `business-rules.md` — BR-P2-*: 공식·임계값·누적/복원·support 진화·influenced 집합·graceful·결정론·회귀.
