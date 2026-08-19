# UX Improvement — Unit of Work Plan

## Plan (artifacts to generate after answers)
- [x] `inception/application-design/ux-improvement/unit-of-work.md` — 유닛 정의·책임·코드 조직
- [x] `inception/application-design/ux-improvement/unit-of-work-dependency.md` — 의존 매트릭스·빌드 순서
- [x] `inception/application-design/ux-improvement/unit-of-work-story-map.md` — FR→유닛 매핑(스토리 스킵 → FR 매핑)
- [x] 유닛 경계/의존 검증, 모든 FR 배정 확인

---

## Decomposition Questions (UOW-UX)

### UOW-UX Q1 — 유닛 개수/경계
컴포넌트 C1–C15를 어떻게 유닛으로 나눌까요?

A) **(권장)** 3 유닛 — **X1 Localization Backend**(C1–C8) · **X2 Frontend Design System**(C9) · **X3 Frontend UX Features**(C10–C15). 관심사 분리 명확(백엔드/디자인시스템/기능), SRP 정합.
B) 2 유닛 — **X1 Localization Backend**(C1–C8) · **X2 Frontend**(C9–C15 병합). 프론트를 한 번에(디자인+기능 동시 스타일링).
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### UOW-UX Q2 — 빌드 순서
유닛 실행 순서는? (AI-DLC per-unit 루프는 순차 — 한 유닛 완료 후 다음)

A) **(권장, Q1=A 기준)** X1 → X2 → X3 (X3는 X1의 ko 데이터 + X2의 디자인 프리미티브에 의존)
B) X2 → X1 → X3 (디자인 시스템 먼저, 그 다음 백엔드, 마지막 기능)
C) (Q1=B 선택 시) X1 → X2
X) Other (please describe after [Answer]: tag below)

[Answer]: A
