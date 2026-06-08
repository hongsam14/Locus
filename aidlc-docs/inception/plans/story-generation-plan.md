# Story Generation Plan — Locus

User Stories 단계 **Part 1: Planning** 입니다. 아래 질문에 답해 주시면(각 `[Answer]:` 뒤 보기 문자), 그 결정에 따라 **Part 2**에서 `stories.md` + `personas.md`를 생성합니다. 각 질문에 권장(Recommended) 기본값을 표시했습니다. 끝나면 "완료"라고 알려주세요.

---

## Planning Questions

## Question SP1 — 스토리 분해(breakdown) 접근법
요구사항(FR-A~I)을 스토리로 어떻게 묶을까요?

A) **Epic 기반 (capability별)** — FR 그룹을 Epic으로, 각 Epic 아래 세부 스토리 (Recommended — 기능군이 뚜렷하고 Units 분해로 자연 연결)
B) 페르소나 기반 — 기획자 스토리 / NPC 런타임 스토리로 그룹
C) 사용자 여정(journey) 기반 — "자료 입력 → 그래프 생성 → 검토·보강 → 쿼리"의 흐름 순
D) 하이브리드 — Epic(capability) 기반을 기본 골격으로 하되, 각 스토리에 페르소나·여정 단계 태깅 (Recommended 대안)
X) Other (please describe after [Answer]: tag below)

[Answer]: D

## Question SP2 — 페르소나 세분도
페르소나를 어느 정도로 나눌까요?

A) 2개 — 기획자/내러티브 디자이너(1차) + NPC 런타임 시스템(2차 소비자) (Recommended — 요구사항과 일치, 단순)
B) 3개 — 1차를 "내러티브 디자이너"와 "월드/레벨 디자이너"로 분리 + NPC 런타임
C) 4개 — 위 3개 + 운영/통합 개발자(파이프라인·API 연동 담당)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question SP3 — 수용 기준(Acceptance Criteria) 형식
각 스토리의 AC를 어떤 형식으로 작성할까요?

A) Given/When/Then (BDD 스타일) — 테스트·검증에 직접 매핑 (Recommended — PBT/테스트 단계 연계)
B) 체크리스트 형식 (불릿 조건 목록)
C) 혼합 — 핵심 시나리오는 Given/When/Then, 부가 조건은 체크리스트
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SP4 — 우선순위 체계
스토리에 우선순위를 부여할까요? (MVP 범위 식별용)

A) P0(필수)/P1(권장)/P2(차기) (Recommended)
B) MoSCoW (Must/Should/Could/Won't)
C) 우선순위 없이 스토리만 (Units 단계에서 순서 결정)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SP5 — 스토리 입도(granularity)
스토리 크기를 어느 정도로 할까요?

A) 중간 입도 — Epic당 3~6개, 구현 가능한 단위로 (Recommended — INVEST의 Small/Estimable 균형)
B) 굵은 입도 — capability당 1~2개의 큰 스토리 (빠른 개관, 분해는 Units에서)
C) 세밀한 입도 — 작은 태스크 수준까지 (스토리 수 많아짐)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question SP6 — 상식 Wiki / 지식 보강의 스토리화 비중
신규 핵심 기능(상식 Wiki, 지식 보강 Q&A)을 MVP에서 어느 비중으로 스토리에 반영할까요?

A) 1차 핵심으로 본격 반영 — 두 기능 모두 전용 Epic + 상세 스토리 (Recommended — 사용자가 핵심이라 명시)
B) 기본만 반영 — 상식 Wiki는 토폴로지 가중·고증 최소 스토리, 보강 Q&A는 단일 루프 스토리
C) 골격만 — 인터페이스/자리만 잡고 상세는 차기
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Story Artifacts (Part 2에서 생성)
- [x] `stories.md` — INVEST 기준 사용자 스토리 (수용 기준 포함)
- [x] `personas.md` — 사용자 페르소나(특성·동기)
- [x] 스토리 ↔ 페르소나 매핑
- [x] 스토리 ↔ 요구사항(FR/NFR) 추적성
- [x] (SP4 선택 시) 우선순위 부여 (P0/P1/P2)

## Execution Checklist (Part 2)
- [x] 1. 승인된 접근법(SP1~SP6)에 따라 Epic/스토리 구조 확정 (9 Epic)
- [x] 2. 페르소나 작성 (`personas.md`) — P1/P2/P3
- [x] 3. Epic별 스토리 + AC 작성 (`stories.md`) — 30 스토리
- [x] 4. 페르소나·요구사항 추적성 매핑 추가
- [x] 5. INVEST 점검 및 우선순위 부여
- [x] 6. 상태/감사 갱신 후 승인 게이트 제시
