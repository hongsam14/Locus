# Story Generation Plan — Purpose Restructure Cycle (2026-09-29)

**원하시는 것**: 월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG로 Locus를 다시 짜는 것(포트폴리오·데모).
**지금 하는 것**: User Stories **Part 1 — Planning**. 스토리를 어떻게 묶고, 어떤 형식으로 쓰고, 기존 스토리 30개를 어떻게 다룰지 정합니다. 답이 정해지면 Part 2에서 `stories.md`와 `personas.md`를 새로 씁니다. Units Generation이 이 스토리를 유닛으로 나누고, Build&Test가 수용 기준을 검증합니다.

**입력**: `inception/requirements/purpose-restructure-requirements.md`(승인됨), `inception/reverse-engineering/business-overview.md`, 기존 `inception/user-stories/{personas,stories}.md`(2026-06, 9 Epic · 30 스토리).

답은 `[Answer]:` 뒤에 글자로 적어 주세요. 대화창에서 답하셔도 됩니다.

---

## 이미 정해진 것 (질문하지 않음)
- **페르소나 집합**: 승인된 요구사항 §5를 따른다 — **P-Builder**(월드 제작자), **P-Player**(플레이어), **P-GM**(GM 모드), **P-Viewer**(포트폴리오 관람자). 기존 P3(NPC 런타임)은 "내부화"로 주석 처리하고 외부 계약 스토리 하나만 남긴다. 셋 다 사용자 본인이 맡는 역할이라 `personas.md`는 "역할(hat)"로 쓴다.
- **필수 산출물**: `stories.md`(INVEST, 수용 기준 포함), `personas.md`, 스토리 ↔ 페르소나 매핑, 스토리 ↔ FR/NFR 추적표, 우선순위.

## Planning Questions

## Question SP-R1 — 기존 스토리 30개 처리
**배경**: 기존 `stories.md`는 "기획자가 자료를 넣고 NPC 런타임이 질의한다"는 옛 목적으로 쓰여 있다(9 Epic, 30 스토리, 대부분 [x] 완료). 새 목적에서는 일부는 그대로 유효하고(수집·토폴로지·합의), 일부는 뜻이 바뀌며(쿼리 API → 내부 NPC), 일부는 새 스토리로 대체된다(검토·편집 UI → 월드 에디터). 이 답에 따라 파일 구조와, 관람자가 이력을 어떻게 읽을지가 정해진다.

A) **새 `stories.md`를 쓰고, 기존 30개는 처리표로 남긴다** *(권장)* — 새 파일 끝에 "기존 스토리 처리표"(유지 / 대체됨 → 새 ID / 보류)를 붙이고, 옛 파일은 `stories-2026-06.md`로 이름을 바꿔 보존한다. 잃는 것이 없음을 보이면서 새 파일은 새 목적만 담는다. **권장 이유**: 관람자와 다음 단계는 새 파일만 읽으면 되고, 이력은 남는다.
B) **기존 파일에 새 Epic을 덧붙인다** — 파일 하나에 옛 목적과 새 목적이 함께 남는다. 이력은 한 파일이지만, 첫 절이 옛 목적이라 "명료한 목적"과 어긋난다.
C) **기존 파일을 통째로 다시 쓴다(옛 스토리 삭제)** — 가장 깔끔하지만, 완료된 스토리 이력이 git에만 남는다.
X) Other (please describe after [Answer]: tag below)

[Answer]: C — 통째로 다시 쓰고 옛 것 삭제 (대화창 답변, 2026-09-29). `stories.md`·`personas.md`를 새 내용으로 덮어쓴다. 옛 내용은 git 이력(`ee61277` 이전)에만 남는다. 처리표는 두지 않는다.

## Question SP-R2 — 스토리 묶는 방식
**배경**: 이전 사이클은 "FR 영역별 Epic + 페르소나·여정 태그"(SP1=D)였다. 이번 요구사항에는 §6 "핵심 경험 흐름"(띄우기 → 월드 만들기 → 세션 시작 → 플레이 → 개입 → 다시 보기)이 있고, 이 흐름이 곧 데모 대본이다. 반면 FR-A(경계 재정리)·FR-E(안정화)·FR-I(미완성 기능 옮기기)는 사용자 여정이 아니라 내부 작업이다. 이 답에 따라 Epic 구조, 스토리 순서, Units 분해가 무엇을 따라가는지가 정해진다.

A) **여정 기반 Epic + 조력자(enabler) Epic** *(권장)* — Epic을 §6 흐름 순서(띄우기 / 만들기 / 세션·플레이 / NPC 대화 / 개입 / 다시 보기)로 두고, FR-A·E·I는 "관람자가 저장소를 읽는다"·"세계가 폭주하지 않는다" 같은 관람자·플레이어 가치로 표현한 조력자 Epic에 둔다. 각 스토리에 FR ID와 페르소나를 태그한다. **권장 이유**: 스토리를 위에서 아래로 읽으면 데모 대본이 되고, 목적이 곧바로 드러난다.
B) **FR 영역별 Epic(FR-A~I) + 여정·페르소나 태그** — 이전과 같은 방식. 요구사항과 1:1이라 추적은 쉽지만, 읽는 순서가 "경계 재정리"부터 시작해 목적이 늦게 보인다.
C) **페르소나별 Epic(Builder / Player / GM / Viewer)** — 역할별로 읽기 좋지만, 한 사용자가 세 역할을 오가는 흐름이 끊겨 보인다.
X) Other (please describe after [Answer]: tag below)

- **A와 B의 차이**: A는 스토리 순서가 데모 흐름을 따르고, B는 요구사항 절 순서를 따른다.

[Answer]: A — 여정 기반 Epic + 조력자 Epic (대화창 답변, 2026-09-29)

## Question SP-R3 — 형식 기본값 확인
**배경**: 이전 사이클은 수용 기준 = Given/When/Then, 우선순위 = P0/P1/P2, 입도 = Epic당 3~6개(중간)였다. 이번 요구사항도 FR에 P0/P1/P2를 붙였고, PBT Partial이라 Given/When/Then이 테스트로 이어지기 쉽다. 이 답에 따라 스토리 수(대략 25~35개)와 수용 기준 형식이 정해진다.

A) **이전과 같이 유지** *(권장)* — G/W/T + P0/P1/P2 + 중간 입도. 새로 익힐 형식이 없고 PBT·Build&Test로 바로 이어진다.
B) **입도만 굵게** — Epic당 1~3개 큰 스토리. 스토리 수는 줄지만(약 15개) 수용 기준이 길어지고 Units 분해가 스토리 안에서 다시 쪼개야 한다.
C) **입도만 세밀하게** — 태스크 수준(약 50개+). 추적은 촘촘하지만 읽는 데 오래 걸린다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 이전과 같이 유지 (대화창 답변, 2026-09-29)

---

## 답변 분석 (Step 9)
- SP-R1=C, SP-R2=A, SP-R3=A. 세 답 모두 단일 선택지이고 서로 어긋나지 않는다. 후속 질문 없음.
- SP-R1=C에 따라 아래 체크리스트 5번(처리표)은 **N/A**.

## 확정된 접근법
- **Epic 구조 (여정 기반 + 조력자)**: E1 띄우기·둘러보기(P-Viewer) → E2 월드 만들기(P-Builder) → E3 세션 시작·플레이어 이동(P-Player) → E4 NPC 대화(P-Player) → E5 살아 있는 세계·GM 개입(P-GM) → E6 다시 보기·저장(P-Player/P-Builder) → E7 조력자: 읽히는 구조(P-Viewer, FR-A·I) → E8 조력자: 폭주하지 않는 세계(P-Player, FR-E) → E9 조력자: 언어(FR-G).
- **형식**: 스토리 ID `US-<epic>.<n>`, 페르소나 태그, FR 태그, P0/P1/P2, Given/When/Then 수용 기준, 가정 A-1~A-5는 해당 수용 기준에 명시.
- **파일**: `inception/user-stories/stories.md`, `inception/user-stories/personas.md`를 새 내용으로 덮어쓴다.

---

## Execution Checklist (Part 2 — 승인 뒤 실행)
- [x] 1. SP-R1~R3에 따라 Epic 구조 확정 — E1~E6 여정 + E7~E9 조력자
- [x] 2. `personas.md` 재작성 — P-Builder / P-Player / P-GM / P-Viewer (+ NPC 런타임 내부화 주석), 역할 전환 흐름, 페르소나↔Epic 매핑
- [x] 3. `stories.md` 작성 — 43 스토리 (P0 32 · P1 10 · P2 1), ID·페르소나·FR 태그·우선순위·Given/When/Then
- [x] 4. 가정 A-1~A-5를 해당 스토리의 수용 기준에 반영 — A-1 US-4.1·9.2 / A-2 US-3.3 / A-3 US-3.1 / A-4 US-1.3 / A-5 US-3.3
- [x] 5. 기존 30개 스토리 처리표 — **N/A** (SP-R1=C: 옛 스토리는 덮어쓰고 처리표를 두지 않음)
- [x] 6. 스토리 ↔ 페르소나 매핑, 스토리 ↔ FR/NFR 추적표(FR·NFR 전부 커버), 우선순위 집계
- [x] 7. INVEST 점검
- [x] 8. `aidlc-state.md`·`audit.md` 갱신, 완료 메시지 (2026-09-29)
