# X2 Frontend Design System — Functional Design Plan

## Plan (artifacts after answers)
- [x] `construction/X2-frontend-design-system/functional-design/frontend-components.md` (디자인 토큰·프리미티브·restyle 매핑)
- [x] `construction/X2-frontend-design-system/functional-design/business-rules.md` (디자인/접근성/계약 보존 룰)
- [x] NFR-light 노트

## Context
- 대상: `web/src/` 전체 restyle — App, Toolbar, SessionBar, MapOverlay, RegionPanel, SessionPanel, AugmentPanel (현재 인라인 `style={{}}` + `data-testid` 존재).
- 결정(확정): Tailwind 도입(Q2=A), 앱 전체(Q3=A), 라이트 단일테마(Q4=A) + **Doodly**(Q9=C 로컬 폰트+CSS 스케치), 동작·`data-testid` 보존(FR-UX1.5).

---

## Functional Design Questions (FD-X2)

`[Answer]:`에 알파벳. 권장안 표시.

### FD-X2 Q1 — "Doodly" 폰트(로컬 번들, 외부 CDN 없음)
A) **(권장)** 손글씨 계열 디스플레이 폰트를 **제목/헤더**에, 본문은 가독성 좋은 산세리프(예: 제목=손글씨, 본문=system-ui)
B) 제목·본문 모두 손글씨 계열(강한 두들감, 가독성 다소↓)
X) Other

[Answer]: A

### FD-X2 Q2 — 색 팔레트 방향
A) **(권장)** 밝고 장난기 — 크림/화이트 배경 + 파스텔 포인트 + 잉크 블랙 테두리
B) 차분한 뮤트 톤(저채도)
C) 종이+잉크 모노(크림 배경 · 검정 스케치 위주)
X) Other

[Answer]: C

### FD-X2 Q3 — 스케치 요소 강도
A) **(권장)** 은은하게 — 둥근/살짝 삐뚠 테두리 + 부드러운 그림자 + 손그림 느낌 강조선
B) 강하게 — hand-drawn SVG 테두리·구분선, 손그림 아이콘 다수
X) Other

[Answer]: A

### FD-X2 Q4 — 공용 프리미티브 범위
A) **(권장)** `Button`·`Panel`·`Card`·`Badge`·`Toast`·`Modal(confirm)` 신설 후 기존 컴포넌트가 사용(구조 유지)
B) 최소(Button·Panel만) — 나머지는 유틸 클래스로
X) Other

[Answer]: A

### FD-X2 Q5 — 반응형 범위
A) **(권장)** 데스크톱 우선(지도 오버레이 중심), 패널은 접근 가능한 최소 반응형(가로 스크롤 방지·折り返し)
B) 완전 반응형(모바일 레이아웃 포함)
X) Other

[Answer]: A
