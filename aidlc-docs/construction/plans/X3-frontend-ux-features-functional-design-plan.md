# X3 Frontend UX Features — Functional Design Plan

## Plan (artifacts after answers)
- [x] `construction/X3-frontend-ux-features/functional-design/frontend-components.md`
- [x] `construction/X3-frontend-ux-features/functional-design/business-rules.md`
- [x] NFR-light 노트

## Context
- 컴포넌트: C10 i18n 사전 · C11 LocalizedText(원문 토글) · C12 전체 생성 · C13 지역 재생성 개선 · C14 NotificationCenter(지역별 턴 변동 알림) · C15 api/types.
- 확정: Q5=C(전체=빈지역만·덮어쓰기 별도확인) · Q6=B(프론트 병렬+진행률) · Q8=B(콘텐츠+UI라벨 한국어) · Q11=B(원문 토글) · Q12=A(한국어) · FR-UX2.6(지역별 알림) · F2a(타임라인=UI i18n) · X2 프리미티브(Toast/Modal 등) 사용.

---

## Functional Design Questions (FD-X3)

`[Answer]:`에 알파벳. 권장안 표시.

### FD-X3 Q1 — 턴 변동 알림 배치/수명 (FR-UX2.6)
A) **(권장)** 우상단 토스트 스택, 지역마다 1건, 자동 소멸(수초) + 수동 닫기
B) SessionPanel 내 인라인 알림 목록(자동 소멸 없음)
X) Other

[Answer]: A

### FD-X3 Q2 — 전체 생성 진행 표시 (Q6=B)
A) **(권장)** 버튼 옆 인라인 진행("N/M 완료") + 완료/부분실패 요약 토스트
B) 모달 진행 오버레이
X) Other

[Answer]: A + progress-bar

### FD-X3 Q3 — 전체 재생성(덮어쓰기) UX (Q5=C)
A) **(권장)** "전체 생성"(빈 지역만)과 "전체 재생성"(덮어쓰기)을 **별도 버튼**으로 두고, 재생성은 Modal 확인
B) 버튼 하나 — 빈 지역은 생성, 채워진 지역은 확인 후 덮어쓰기
X) Other

[Answer]: A

### FD-X3 Q4 — 타임라인 한국어화 (F2a: kind+payload)
A) **(권장)** i18n 사전으로 kind 라벨+요약을 한국어 템플릿 렌더(예: "승격: {id}", "이벤트 적용: {id}")
B) 타임라인은 영어 유지(정적 UI 라벨만 한국어)
X) Other

[Answer]: A

### FD-X3 Q5 — 원문(영어) 토글 방식 (Q11=B)
A) **(권장)** 항목별 "원문" 토글 버튼(클릭 시 번역↔원문 전환)
B) hover 툴팁으로 원문 표시
X) Other

[Answer]: A

### FD-X3 Q6 — 지역 재생성 개선 범위 (FR-UX2.5) ⚠ 백엔드 경계
현재 백엔드 `regenerate_region`은 **승격 포함 전체 삭제 후 재생성**(rumor_service.py:64). FR-UX2.5는 "승격 소문 보존"을 요구 → 완전 충족하려면 백엔드 소폭 수정 필요.

A) **(권장)** Modal 확인(프론트) + **백엔드 regen이 승격 소문은 보존**하도록 소폭 수정(X3에 백엔드 터치 포함, 오프라인 테스트 추가)
B) 프론트 Modal 확인만 — 백엔드 regen 동작 유지(승격도 재생성됨; FR-UX2.5 부분 충족)
X) Other

[Answer]: A

### FD-X3 Q7 — 전체 재생성 시 승격 보존도 동일 적용?
Q3=A 별도 "전체 재생성"(덮어쓰기)에도 승격 보존을 적용할까요?

A) **(권장)** 예 — 지역 재생성과 동일 규칙(승격 보존)
B) 아니오 — 전체 재생성은 완전 초기화(승격 포함 삭제)
X) Other

[Answer]: A
