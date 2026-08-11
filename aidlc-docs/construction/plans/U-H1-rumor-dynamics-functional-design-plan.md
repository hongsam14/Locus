# U-H1 Rumor Dynamics — Functional Design 계획

> CONSTRUCTION / U-H1. Application Design(CH1-CH9)의 **열린 파라미터·공식·순서**를 확정합니다.
> 각 `[Answer]:` 뒤에 문자(A/B/…), 없으면 `X` + 설명. 끝나면 "완료".

**현행 상수 참고**(Phase 1/2): support 기본 0.0, 승격 임계 `DEFAULT_PROMOTION_THRESHOLD=0.6`,
이벤트 support 강화 `SUPPORT_REINFORCE=0.1`, 감쇠 `SUPPORT_DECAY=0.05`, distortion 기본 0.3,
`MAX_EVENT_DELTA=0.3`, `PROPAGATE_MIN_WEIGHT=0.15`, 체인 분수 [1/3,2/3,1.0].

핵심 통찰: **support(공신력)** 는 루머의 "살아있음"을 나타내는 핵심 변수 — 생존(prune)과
증식(자격)을 모두 좌우(명확화2=C). 아래 값은 "월드가 다이나믹하되 폭주하지 않도록" 정합니다.

---

## FD-H Q1 — 감쇠 정책: empty-turn 포함 여부 (FR-H1, [3] 재결정)
Phase 2 [3] 수정은 "이벤트 없는 빈 턴엔 support 감쇠 금지"였습니다. 하드닝은 support를
생존 지렛대로 승격하므로 재결정이 필요합니다. 강화되지 않은 루머의 support는 언제 감쇠하나요?

A) **매 턴 감쇠**(빈 턴 포함) — support가 진짜 생존 지렛대가 됨. 강화(이벤트/피드백 영향) 없는
   루머는 매 턴 조금씩 줄다 바닥 미만이면 정리. 승격 루머는 prune 예외(Q7=A)라 강등돼도 삭제 안 됨.
   → 자연 선택이 항상 작동. (권장 — 명확화2=C 취지에 부합)
B) **이벤트/피드백이 있었던 턴만 감쇠** — [3] 보수 유지. 빈 턴엔 집합이 그대로(정체 가능).
X) 기타

[Answer]: A

---

## FD-H Q2 — 감쇠에서 "강화됨(reinforced)"으로 보는 집합 (FR-H1/H3)
어떤 루머가 이번 턴에 "강화되어" 감쇠를 면할까요?

A) **이벤트 influenced ∪ 피드백 지역**의 루머 — distortion이 움직인 지역(이벤트 전파 + 루머 피드백)의
   루머는 강화로 간주, 그 외는 감쇠. (권장 — 기존 evolve_support 의미 확장)
B) **이벤트 영향 지역만**(기존 Phase 2 동작 유지) — 피드백 지역은 강화로 치지 않음.
X) 기타

[Answer]: A

---

## FD-H Q3 — 파라미터 기본값 (FR-H4, settings 중앙화)
`RumorDynamicsParams` 기본값을 정합니다. (env로 오버라이드 가능; 순수 함수는 인자로 수령)

A) **권장 세트**
   - `support_decay = 0.05` (기존 SUPPORT_DECAY 계승)
   - `prune_floor = 0.05` (support가 이 값 **미만**이면 정리; 승격 예외)
   - `min_source_support = 0.3` (자동 증식 소스 자격; 기본 support 0.0 신생 루머는 즉시 증식 못함)
   - `feedback_weight = 0.1` (지역 피드백 distortion delta 스케일)
   - `high_support_threshold = 0.6` (피드백 집계 "강한 루머" 기준 = 승격 임계와 일치)
B) **보수 세트**(변화 완만): decay 0.03 / floor 0.02 / min_source 0.2 / feedback 0.05 / high 0.6
C) **공격 세트**(다이나믹 강함): decay 0.08 / floor 0.1 / min_source 0.4 / feedback 0.15 / high 0.5
X) 기타(값 직접 지정)

[Answer]: A

---

## FD-H Q4 — 루머→지역 피드백 집계식 (FR-H3)
지역별 루머 상태를 distortion delta로 어떻게 환산하나요? (delta = weight × 집계값)

A) **고-support 루머 밀도** — 지역 내 `support ≥ high_support_threshold` 루머 수 / 지역 루머 수
   (0~1) × `feedback_weight`. 강한 소문이 밀집할수록 지역이 더 왜곡. (권장 — 밀도 기반, 스케일 안정)
B) **승격 루머 수 비례** — 지역 내 promoted 루머 수 × `feedback_weight`(상한 clamp).
C) **평균 support 가중** — 지역 루머 평균 support × `feedback_weight`.
X) 기타

[Answer]: A

---

## FD-H Q5 — advance_turn 스텝 순서: 피드백 ↔ 감쇠 (FR-H3/H1)
피드백(distortion↑)과 감쇠+prune(support↓, 정리)의 순서는?

A) **피드백 → 감쇠 → prune** — 이번 턴 강한 루머가 지역을 먼저 왜곡(피드백)하고, 그 뒤 support 감쇠·정리.
   피드백 지역은 Q2=A에 의해 "강화됨"으로 간주돼 그 지역 루머는 감쇠 면제. (권장 — 강한 루머가 자신을
   보호·전파하는 일관된 루프)
B) **감쇠 → prune → 피드백** — 먼저 약한 루머를 정리한 뒤, 살아남은 루머로만 피드백 계산.
X) 기타

[Answer]: A

---

## FD-H Q6 — prune·피드백에서 승격/pruned 루머 취급 (FR-H1/H3, Q7=A 상세)
승격(promoted) 루머와 이미 pruned(`active=False`) 루머를 동역학에서 어떻게 다루나요?

A) **승격=prune 예외(삭제 안 함)이되 감쇠·피드백엔 정상 참여**; pruned 루머는 감쇠·피드백·소스·승격
   평가에서 **완전 제외**(활성 루머만 대상). 승격 루머가 계속 강등 임계 미만이면 강등만 되고 유지.
   (권장 — Q7=A와 정합, soft-flag 의미 명확)
B) 승격 루머는 감쇠도 면제(고정) — 승격되면 support 감쇠 정지.
X) 기타

[Answer]: A

---

## FD-H Q7 (후속 — 구현 중 발견) — 신생 루머의 birth support
신생 루머는 support 0.0(Phase 1 기본)이라 새 정책상 **바닥(0.05) 미만** → 이벤트/강한 이웃 없이
advance하면 **다음 턴에 즉시 prune**됩니다(유예 없음). 신생 루머를 어떻게 다룰까요?

A) **birth support 시드** — 자동 append/generate로 태어난 루머에 초기 support = `birth_support`(예: 0.2, 신규 파라미터)
   부여. 강화 없으면 몇 턴에 걸쳐 감쇠하다 정리(유예 있음). (권장 — "며칠 안엔 살아있다 서서히 소멸")
B) **즉시 사멸 유지** — 0.0 신생 루머는 이벤트/피드백/수동 support 없으면 다음 턴 정리(support=적극적 생존 조건).
   조용한 지역의 루머는 빨리 사라짐(가장 공격적 자연선택).
C) **prune에 최소 생존 턴(age) 도입** — `created_turn` 기준 N턴 지나야 prune 대상(스키마에 age/created_turn 필요).
X) 기타

[Answer]: A

## 생성될 산출물 (승인 후)
- `construction/U-H1-rumor-dynamics/functional-design/domain-entities.md`
- `.../business-logic-model.md` (advance_turn 확장 시퀀스 + 순수 함수 알고리즘)
- `.../business-rules.md` (BR-H1-*)

## 참고 — 내 권장
Q1=A(매 턴 감쇠) · Q2=A(이벤트∪피드백) · Q3=A(권장 세트) · Q4=A(고-support 밀도) · Q5=A(피드백→감쇠) ·
Q6=A(승격 예외+pruned 제외). support를 진짜 생존 지렛대로 만들되 승격 루머는 보호하는 균형.
