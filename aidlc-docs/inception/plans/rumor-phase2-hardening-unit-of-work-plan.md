# Units of Work — 계획 (루머 동역학 & Phase 2 하드닝)

> Application Design(AD-H Q1=B..Q7=A) 승인 후 **단위 분해**를 확정합니다.
> 실행 계획(`rumor-phase2-hardening-execution-plan.md` §2)의 기준 제안은
> **U-H1 Rumor Dynamics (CH1-CH9, FR-H1..H5) → U-H2 Fixes (CH10-CH12, FR-H6/H7/H8)** 2단위입니다.
> 아래 질문 3개의 `[Answer]:` 뒤에 문자(A/B/…)를 적어주세요. 없으면 `X` + 설명. 끝나면 "완료".

기존 참고: Phase 2는 **P1 Foundation → P2 Engine → P3 UI** 3단위였습니다. 이번 하드닝은
캐노니컬 빌드 조사(FR-H7/H8)까지 포함해 도메인이 둘로 갈립니다(세션 동역학 vs 캐노니컬 빌드/프론트).

---

## UOW-H Q1 — U-H1(루머 동역학)의 단위 세분화
CH1~CH9(모델·리포·설정 + 순수 엔진·서비스·API)를 **하나의 단위**로 둘까요, 아니면
**기반(Foundation) → 엔진(Engine)** 두 단위로 나눌까요?

A) **단일 단위 U-H1** — 모델(`active`)·리포(`upsert_rumors`)·설정·`rumor_dynamics`·`RumorFeedbackService`·
   `RumorService`/`TurnAdvancer` 확장·API를 한 번에. 서로 강결합(감쇠·prune이 배치·soft-flag에 의존)이라
   함께 테스트해야 의미 있음. (권장)
B) **2단위 분할** — U-H1a Foundation(CH5 `active` / CH6 `upsert_rumors`·`include_pruned`·컬럼 / CH7 Settings)
   → U-H1b Engine(CH1 rumor_dynamics / CH2 FeedbackService / CH3·CH4 서비스 확장 / CH9 API).
   Phase 2의 Foundation→Engine 패턴 계승, 중간 검증 지점 추가(단위 수 증가).
X) 기타

[Answer]: A

---

## UOW-H Q2 — U-H2(수정)의 그룹화
FR-H6(프론트 `Promise.all`) · FR-H7(orchestrator set_wiki 순서 조사) · FR-H8(barrier terrain 드롭 조사)를
어떻게 묶을까요? (셋은 상호 독립, 도메인이 다름: 프론트 vs 캐노니컬 빌드 파이프라인)

A) **단일 단위 U-H2 "Fixes"** — 소규모 3건을 한 단위로(실행 계획 기준안). 조사 우선(H7/H8),
   결함이면 수정. (권장 — 각 항목이 작아 오버헤드 최소)
B) **2단위 분할** — U-H2 Frontend(FR-H6) / U-H3 Canonical-Build Investigation(FR-H7·H8).
   프론트(vitest)와 캐노니컬 빌드(Neo4j/OpenSearch 경로)는 테스트·리스크 성격이 달라 분리.
X) 기타

[Answer]: A

---

## UOW-H Q3 — 빌드 순서 / 독립성
단위 실행 순서는?

A) **U-H1 먼저 → U-H2** (실행 계획 기준). U-H1이 핵심·고위험, U-H2는 독립 소규모라 이후 처리. (권장)
B) **U-H2(독립 수정) 먼저 → U-H1** — 저위험 항목을 먼저 정리해 회귀 스위트를 안정화한 뒤 동역학 착수.
C) 순서 무관 — 상호 의존이 없으니 편한 대로(문서엔 U-H1→U-H2로 기록).
X) 기타

[Answer]: A

---

## 생성될 산출물 (승인 후)
- `inception/application-design/rumor-phase2-hardening/unit-of-work.md` — 단위 정의·책임·컴포넌트·요구사항
- `.../unit-of-work-dependency.md` — 단위 의존 매트릭스
- `.../unit-of-work-story-map.md` — FR/NFR → 단위 커버리지 매트릭스(누락 0 검증)

## 참고 — 내 권장(사용자 코드스타일: DI·SRP 기준)
Q1=A(강결합·통합 테스트 단위), Q2=A(소규모 3건 단일), Q3=A(U-H1→U-H2). 즉 실행 계획 기준안 유지.

## Execution Checklist (생성 단계 — 승인 후)
- [x] 1. UOW-H Q1~Q3 반영해 단위 경계·순서 확정 (Q1=A/Q2=A/Q3=A → 2단위 U-H1→U-H2)
- [x] 2. unit-of-work.md 작성
- [x] 3. unit-of-work-dependency.md 작성
- [x] 4. unit-of-work-story-map.md 작성(FR-H1..H8 + NFR-H1..H5 전수 배정 검증 — 8/8, 5/5, 12/12)
