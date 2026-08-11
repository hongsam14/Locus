# Rumor / Game-Session **Phase 2** — Clarification Questions

답변(Q1–Q13) 분석 결과, 일부 조합에서 **확정 전 해소가 필요한 모호함 4건**을 발견했습니다.
각 `[Answer]:` 뒤에 선택지를 적어주세요. 맞는 게 없으면 **X) Other**.

---

## Clarification 1 — Event 생애주기 메커니즘 (Q10=X "타입에 따라 다름")
Q10에서 *"이벤트 타입에 따라 일회성/지속성이 다르다"* 고 하셨습니다. Q2=B(카테고리 enum)와 결합하면 **각 카테고리가 lifecycle을 결정**하게 됩니다. 지속성(persistent) 이벤트의 **동작 방식**을 확정해야 데이터 모델(만료/지속 필드)이 정해집니다.

### Clarification 1.1
지속성(persistent) 이벤트는 **어떻게 끝나나요**?

A) **지속 턴 수(`duration`) 명시** — 생성 시 N턴 지정, 매 advance_turn마다 효과 적용, N턴 후 자동 만료.
B) **명시적 해소(resolve)까지 무기한** — GameMaster가 수동으로 종료할 때까지 매 턴 적용.
C) **A + B 둘 다 지원** — duration 지정 가능하되 수동 조기 해소도 가능.
X) Other (please describe after [Answer]: tag below)

[Answer]: X. B + 명시적 해소도 일종의 이벤트. 이벤트는 GameMaster가 생성할 수도, LLM이 생성할 수도 있음. 이벤트 생성 방식과 동일.

### Clarification 1.2
지속성 이벤트가 **매 턴 distortion에 미치는 효과**는?

A) **매 턴 동일 delta 재적용**(누적 상승) — 활성 동안 계속 distortion을 끌어올림(만료 시 그 누적분 복원/감쇠).
B) **1회 상승 후 유지(plateau)** — 활성 동안 목표 수준을 *유지*만, 만료되면 원래대로 감쇠.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification 1.3
어떤 카테고리를 어떤 lifecycle로 둘지 — **기본 매핑**을 어떻게 할까요? (개별 카테고리 enum/매핑은 Functional Design에서 확정)

A) **카테고리별 고정 기본값**(예: disaster/festival=일회성, war/plague=지속성) — 코드에 기본 매핑, 사용자는 생성 시 override 가능.
B) **항상 사용자가 생성 시 선택**(카테고리와 무관하게 one-shot/persistent + duration 직접 지정).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Clarification 2 — LLM Event 생성 모드 (Q4=C "수동 + LLM 둘 다")
Q4=C로 LLM 자동 생성을 포함했습니다. LLM이 만든 이벤트의 **확정 방식**과 **시점**을 정해야 UI/API가 정해집니다.

### Clarification 2.1
LLM이 생성한 Event의 **반영 방식**은?

A) **제안 → GameMaster 승인**(suggest-then-approve) — LLM이 후보를 제시, 사용자가 채택/수정/폐기.
B) **자동 커밋**(auto-commit) — LLM이 바로 Event로 등록(사후 삭제 가능).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification 2.2
LLM Event 생성을 **언제** 트리거하나요?

A) **사용자가 명시적으로 "이벤트 제안" 버튼**을 눌렀을 때만(on-demand).
B) **매 advance_turn마다 자동**으로 1건 이상 제안/생성.
C) **A + B 둘 다**(수동 트리거 + 턴마다 자동 옵션).
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Clarification 3 — support 자동 진화 × 이벤트 재생성 충돌 (Q7=B × Q9=B)
Q7=B(이벤트 시 소문 자동 재생성)와 Q9=B(support 강화↑/감쇠↓ 자동)가 **충돌 지점**이 있습니다.
현재 `regenerate_region`은 기존 소문을 **전부 삭제(승격 포함, support=0 리셋)** 후 재생성합니다. 그러면 그 리전의 support 진화 이력이 매번 초기화됩니다.

### Clarification 3.1
이벤트로 영향받은 리전의 소문 처리는?

A) **전부 재생성(기존 방식)** — 이벤트 발생 리전은 소문을 새로 굴림(support 리셋). support 진화는 *이벤트 없는* 리전에서만 의미.
B) **기존 소문 보존 + 추가/갱신** — 이벤트는 새 distortion 기반 소문을 *추가*하거나 기존 소문 텍스트를 갱신하되 support는 유지.
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Clarification 3.2
Q9=B의 **"강화(reinforcement)"** 판정 기준은? (support가 자동 증가하는 조건)

A) **그 턴에 이벤트가 영향을 준 리전의 소문** = 강화(support↑). 이벤트 없는 리전 소문 = 감쇠(support↓).
B) **distortion이 낮은(=사실에 가까운) 소문** = 강화, 높은 소문 = 감쇠.
C) **수동 조정된 소문**만 그 값 유지, 나머지는 일률 감쇠.
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Clarification 4 — 토폴로지 전파 리전의 소문 재생성 범위 (Q3=C/Q5=C × Q7=B)
Q3=C/Q5=C로 이벤트가 **이웃 리전에 거리 감쇠로 전파**(distortion delta)됩니다. Q7=B는 이벤트 리전 소문을 자동 재생성합니다.

### Clarification 4.1
**전파로 distortion만 바뀐 이웃 리전**도 소문을 자동 재생성하나요?

A) **주 대상 리전만 재생성** — 이웃은 distortion 수치만 갱신(다음 수동/이벤트 때 반영).
B) **전파 받은 이웃도 재생성** — delta가 임계값 이상인 이웃 리전도 소문 자동 재생성.
X) Other (please describe after [Answer]: tag below)

[Answer]: A
