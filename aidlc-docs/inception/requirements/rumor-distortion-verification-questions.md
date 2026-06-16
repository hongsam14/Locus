# 소문 내용 실제 왜곡 — 요구사항 확인 질문

기능: Knowledge(또는 기존 Rumor)의 **내용(statement)을 LLM이 실제로 왜곡**해 `Rumor` 노드로 생성. 웹에서 버튼으로 트리거.
현황: `Rumor` 모델·영속화·`DISTORTED_FROM` 엣지·export·WorldLoader 로딩은 준비됨. 생성 서비스/API/웹 버튼이 없음. (consensus의 자동 소문 분류는 텍스트를 바꾸지 않는 별개 경로.)

각 `[Answer]:` 뒤에 선택지(A/B/C…)를 적어주세요. 맞는 게 없으면 마지막 "Other".

---

## 트리거 & 범위

### Question 1
"rumor 생성 버튼"은 어디에 위치하고 무엇을 대상으로 하나요?

A) **지식 항목별**(RegionPanel의 각 knowledge 옆 버튼) — 그 지식 하나에서 소문 1건 생성
B) **지역별**(RegionPanel 상단/지역 단위 버튼) — 그 지역의 지식들에서 소문 여러 건 일괄 생성
C) **월드별**(Toolbar) — 월드 전체에 대해 일괄 생성
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 2
소문의 원본(distorted_from)이 될 수 있는 것은?

A) **Knowledge만** — 사실에서만 소문 생성
B) Knowledge + 기존 Rumor — 소문의 소문(연쇄 왜곡) 허용 (`distorted_from_id`가 Rumor도 가리킴)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

### Question 3
한 번 누르면 소문을 몇 개 생성하나요?

A) 1건(고정)
B) 사용자가 개수 지정(예: 1~5)
C) 왜곡 강도별로 여러 단계 생성(예: 약/중/강 3건 체인)
X) Other (please describe after [Answer]: tag below)

[Answer]: C

---

## 왜곡 강도(distortion_degree) 제어

### Question 4
`distortion_degree`(0=원본 충실 … 1=심하게 왜곡)는 누가 정하나요?

A) **사용자가 UI에서 지정**(슬라이더/입력) → LLM이 그 강도에 맞춰 왜곡
B) 고정 기본값(예: 0.5)
C) LLM이 스스로 적절히 정함(자유)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. C의 일종인 "GameMaster"가 결정. 각 리전마다 distortion_degree가 다름. 이 수치는 추구 "이벤트", 혹은 루머 그 자체가 리전에 영향을 미친다는 개념을 통해서 동적으로 바뀔 예정. 그래서 추후 "이벤트, 루머 타임라인" 이라는 개념이 필요함.

### Question 5
왜곡 강도가 "내용"에 어떻게 반영되나요? (LLM 프롬프트 의미)

A) 강도↑ = 사실에서 점점 더 벗어남(세부 변경→과장→부분적 오류→거의 허구). degree를 프롬프트에 명시해 LLM이 조절
B) 강도와 무관하게 "그럴듯한 소문체"로만 변형(degree는 메타데이터로만 저장)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 그리고 Rumor에는 "지지도"라는 필드가 있어야 함. Rumor의 지지도가 일정 threshold를 넘어갈 경우 (direct) knowledge로 승격. 하지만 영속적이진 않음. (여기서 Game이라는 개념이 존재하고 새로운 게임이 시작될 경우 이전에 발생한 Rumor와 Event, Rumor에서 승격된 Knowledge는 사라짐. Game Session DB(postgresql)에 저장할 수도)

### Question 6
생성된 소문의 `confidence`는?

A) 원본 confidence × (1 − distortion_degree) (왜곡될수록 신뢰도↓)
B) 고정값(예: 0.5)
C) 사용자 지정
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 배치(어느 지역에 붙나) & consensus 연계

### Question 7
생성된 Rumor 노드는 어느 region에 scope(SCOPED_TO, is_rumor=true)되나요?

A) **원본과 같은 region** — 같은 지역에 사실과 소문이 공존
B) 사용자가 대상 region 선택 — 특정(보통 먼) 지역에 소문 심기
C) scope 없이 노드+DISTORTED_FROM만 — 쿼리 시 consensus가 알아서 노출
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 하지만 다시금 구분되어야 할 점은, npc는 propagated knowledge(자동 소문)는 직접 접근할 수 없고 Rumor로서만 접근할 수 있음.

### Question 8
기존 consensus 자동 소문(전파 거리로 분류, 텍스트 안 바뀜)과의 관계는?

A) **독립** — 명시적 Rumor 노드(왜곡 텍스트)와 자동 소문 view는 별개로 공존. 쿼리는 둘 다 반환
B) 자동 소문 분류 시 distortion_degree를 이 생성 기능의 기본 강도로 제안(연계)
C) 자동 소문 경로를 대체 — 이제 거리가 멀면 실제 왜곡 텍스트 Rumor를 만들어 붙임
X) Other (please describe after [Answer]: tag below)

[Answer]: A. Rumor는 Game Session마다 재생성되어 바뀌지만, 자동 소문은 아님.

---

## 영속화 & 검색

### Question 9
생성된 Rumor를 하이브리드 검색 인덱스에 넣나요? (현재 Rumor는 미인덱싱)

A) 예 — Rumor도 검색 인덱스에 넣어 NPC 쿼리/검색에 노출
B) 아니오 — 그래프 노드로만 보존(검색 인덱싱 안 함)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 그래프 노드로 보존 안하고 Game Session DB에 보관

### Question 10
생성된 소문의 되돌리기/삭제는?

A) 기존 `DELETE /worlds/{id}/nodes/{node_id}`로 노드 삭제(웹에 삭제 버튼 — 이미 knowledge엔 있음)
B) augmentation처럼 revert 가능한 ChangeSet으로 관리
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 위 내용 참조

---

## 웹 UI 범위

### Question 11
이번 사이클 웹 UI 변경 범위는? (지난 사이클은 백엔드만, 웹 제외였음)

A) **버튼 + 생성 흐름 + 소문 표시**(RegionPanel에 생성 버튼·distortion_degree 표시·생성된 Rumor 노출)까지 이번에 구현
B) 백엔드(API/서비스)만 이번에, 웹 버튼은 다음 사이클
C) 버튼/표시 최소 구현만(슬라이더 등 고급 UI는 다음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 과거 Game Session을 다시 열람할 수 있게.

### Question 12
(참고) 지난 사이클에서 `wiki/build` 엔드포인트를 제거했는데 `web/src/api.ts`에 `buildWiki()` 호출이 남아 404가 됩니다. 이번에 같이 정리할까요?

A) 예 — 죽은 `buildWiki` 호출/버튼 제거(겸사겸사 정리)
B) 아니오 — 이번 기능과 무관하니 손대지 않음
X) Other (please describe after [Answer]: tag below)

[Answer]: A.
