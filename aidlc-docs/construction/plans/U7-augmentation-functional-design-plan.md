# U7 Augmentation — Functional Design Plan

U7는 **인터랙티브 지식 보강 Q&A**(FR-F, US-6.1~6.3): 그래프 빈틈·모순(A) + 상식 Wiki 충돌(B) + 저신뢰 입력(C)을 탐지(CL5)해 기획자에게 질문 → 답변 적용 → 재탐지 루프(AD-CL1=A LangGraph). U1/U4/U5/U8/U9 재사용.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD7-Q1 — 이슈 탐지기(detector) MVP 범위 (CL5=A,B,C)
어떤 탐지기를 1차에 넣을까요?

A) **셋 다** — (A)그래프 빈틈/모순: 지식 없는 지역·인접인데 공유 0·끊긴 관계 / (B)Wiki 충돌: 지역 지형 vs 지식이 상식 prior와 모순(LLM 판정) / (C)저신뢰: confidence<임계 (Recommended — CL5 충실)
B) A + C 만(결정적), B(Wiki 충돌, LLM)는 차순
C) 직접 지정 (X)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD7-Q2 — 보강 루프 구현 (AD-CL1=A)
detect→ask→apply→재detect 루프는?

A) **LangGraph 그래프**(노드: detect/generate/await-answer/apply/check)로 구현, 탐지·질문·적용 코어는 순수 함수로 분리(테스트는 코어+얇은 루프) (Recommended — AD-CL1=A 결정 준수)
B) 순수 Python 상태머신(LangGraph 차순) — 단순·테스트 쉬움
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD7-Q3 — 보강 질문 생성
이슈→질문 변환은?

A) LLM 자연어 질문 생성(structured: question + 선택지) + 이슈 타입별 템플릿 폴백 (Recommended)
B) 템플릿만(결정적, LLM 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD7-Q4 — 답변 적용(apply_answer)
답변이 그래프를 어떻게 바꾸나?

A) 답변→그래프 변이(지식 추가/수정, confidence·스코프 조정, 모순 해소)로 매핑, **ChangeSet**(before/after) 기록 → 되돌리기(US-6.3). GraphEditor(U9) 재사용 (Recommended)
B) 답변을 신규 지식으로만 추가(수정/해소 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD7-Q5 — 세션/수렴
보강 세션 상태와 종료는?

A) **in-memory 세션**(ChangeSet 이력 보관, 되돌리기) + 수렴: 새 이슈 없음 또는 max_rounds 도달 (Recommended — MVP)
B) 영속 세션(DB 저장)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 나중에 postgresql로 변경할 가능성을 명시.

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — Issue/AugmentationQuestion/Answer/ChangeSet/Session 모델 + 탐지 규약
- [ ] `business-logic-model.md` — Detectors, QuestionGenerator, apply/revert, AugmentationEngine/Graph, API/CLI 연계
- [ ] `business-rules.md` — 탐지·질문·적용·수렴·되돌리기 규칙

## Execution Checklist
- [x] 1. FD7-Q1~5 반영 (all A; Q5 note: SessionStore 추상화로 PostgreSQL 교체 여지)
- [x] 2. 산출물 3종 작성
