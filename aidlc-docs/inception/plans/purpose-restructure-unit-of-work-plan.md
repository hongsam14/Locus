# Unit of Work Plan — Purpose Restructure Cycle (2026-09-29)

**원하시는 것**: 월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG로 Locus를 다시 짜는 것. 플레이어의 행적도 소문이 되어 퍼진다(포트폴리오·데모).
**지금 하는 것**: Units Generation Part 1 — 승인된 설계(경계 5개, 컴포넌트 S/K/W/P/L/A/F, 변경 P16~P19)와 스토리 48개를 **유닛**으로 나눈다. 유닛마다 Construction 루프(FD → NFR-light → CodeGen)가 한 번씩 돈다. 여기서 정한 유닛 수와 순서가 앞으로의 작업 단위가 된다.

**입력**: `execution-plan.md`(유닛 초안 U1~U7), `application-design/purpose-restructure/*`(승인, 행적 변경 포함), `user-stories/stories.md`(48), `requirements` §7 + 부록 A.

**단일 배포 모놀리스**이므로 유닛은 "서비스"가 아니라 **작업 묶음(Unit of Work)**이다. 팀은 한 사람(+AI)이라 병렬 소유권 질문은 두지 않는다.

답은 `[Answer]:` 뒤에 글자로 적어 주세요. 대화창에서 답하셔도 됩니다.

---

## Plan (답이 정해지면 생성)
- [x] `inception/application-design/purpose-restructure/unit-of-work.md` — U1~U8 정의·책임·컴포넌트·코드 위치·PBT·완료 기준
- [x] `inception/application-design/purpose-restructure/unit-of-work-dependency.md` — 의존 행렬·그림·실행 순서·조정 지점·테스트 체크포인트·되돌리기
- [x] `inception/application-design/purpose-restructure/unit-of-work-story-map.md` — 48 스토리 → 유닛(주·부), 유닛별 집계(P0 36 일치), FR/NFR 커버리지
- [x] 유닛 경계·의존 검증 — U3 ⟂ U4~U7, 사이클 없음, 미배정 스토리 0, 미배정 FR/NFR 0
- [x] `aidlc-state.md`·`audit.md` 갱신, 완료 메시지 (2026-09-29)

---

## Decomposition Questions (UOW-R)

## Question UOW-R1 — 유닛 수와 경계
**배경**: 실행 계획 초안은 유닛 7개였다(U1 경계 재정리 → U2 World File·기반 → U3 에디터 → U4 플레이어 → U5 NPC 대화·언어 → U6 GM·안정화 → U7 데모·문서). 그 뒤 Application Design에서 **행적·판단·전파**(P16 DeedService, P17 GmNarrator, P19 plan_spread, 턴 루프 두 단계, gm 행적 API, 선언 UI, 행적 패널)가 더해졌다. 이 묶음은 플레이어 행동(U4)·대화(U5)·턴 루프(U6)에 걸쳐 있고, 레거시와 갈라지는 핵심이라 자체 FD와 PBT(전파 불변식)가 필요하다. 이 답에 따라 유닛 수, 각 유닛의 크기, FD 횟수가 정해진다.

A) **8 유닛 — 행적·전파를 독립 유닛으로** *(권장)*:
   - U1 경계 재정리(동작 불변: 패키지 이동, 포트 분할, 파사드 제거, 조립 컨테이너, API 접두어, 용어, 조정값 집약, `test_boundaries`, Docker `api/` 포함)
   - U2 World File·캐노니컬 기반(NPC 모델, WorldFile 저장·로드, WorldCache, 관계 재독, 수집 결함 A1·A2·A7·A11, 재빌드 교체, 빌드 리포트)
   - U3 월드 에디터(편집 백엔드·UI, 업로드, NPC 배치·제안, 보강 통합·수리, wiki 근거, 월드 목록)
   - U4 플레이어 모드(Player, 이동, `TurnAdvancer.advance(action)` + 가드 + LLM 예산·소문 상한(E1), 현재 지역 화면, play 라우터, 지역 이름)
   - U5 NPC 대화·언어(NpcScope, 대화 서비스, localization 경계 분리·API 계층 번역, UI 라벨)
   - **U6 행적·전파**(Deed·판단·선언·씨앗·전파·gm 행적 API·선언 UI·행적 패널, US-6.5)
   - U7 GM 모드·안정화(GM 화면 5패널, 모드 전환, 사건 제안 컨텍스트, 세계 상태 오버레이, E2·E4~E6, 타임라인 이름)
   - U8 데모·배포·문서(TRPG 데모 월드, 원클릭, Docker·compose·메타, README, 진행 중 표시, P2 CI)
   — 유닛이 작아 승인 단위가 명확하고, 행적·전파가 자기 FD·PBT를 갖는다. **권장 이유**: 레거시와 갈라지는 기능이 다른 유닛 안에 묻히지 않는다.
B) **7 유닛 — 행적·전파를 U5(판단·선언)와 U6(전파·GM)에 나눠 넣음**: 초안 그대로. — 유닛이 하나 적지만 U5·U6이 커지고, 행적 메커니즘의 FD가 둘로 갈린다.
C) **6 유닛 — U2를 U1·U3에 흡수**(캐시·NPC 모델은 U1, World File·결함 수정은 U3): — U1이 "동작 불변"이 아니게 되어 회귀 검증이 흐려진다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 8유닛, 행적·전파를 독립 유닛(U6)으로 (대화창 답변, 2026-09-29)

## Question UOW-R2 — 빌드 순서
**배경**: AI-DLC 유닛 루프는 순차다. 의존은 U1 → U2 → {U3, U4}, U4 → U5 → U6 → U7, {U3, U7} → U8이다(U3 에디터와 U4~U7 플레이는 서로 독립). 순서에 따라 **핵심 스토리(US-6.1·6.5, "같은 사건·내 행적을 다른 지역에서 다르게 듣는다")가 언제 동작하는지**가 달라진다. 개발용 월드는 기존 Aldermoor(원자료 빌드)로 충분해서 에디터 없이도 플레이를 만들 수 있다. 이 답에 따라 유닛 실행 순서와, 시간이 부족할 때 무엇이 남는지가 정해진다.

A) **플레이 먼저** *(권장)*: U1 → U2 → **U4 → U5 → U6 → U7** → U3 → U8. — 핵심 스토리가 U6 끝에 동작한다(전체의 약 60% 지점). 시간이 모자라면 "에디터 없이 데모 월드 + 플레이"가 남는데, 이것만으로도 포트폴리오의 핵심을 보여 준다. 에디터(U3)는 데모 월드 콘텐츠(U8)를 만들 때 바로 쓰인다. **권장 이유**: 목적의 증명이 가장 빨리 나온다.
B) **초안 순서(월드 구성 먼저)**: U1 → U2 → U3 → U4 → U5 → U6 → U7 → U8. — 데모 흐름(만들기 → 플레이) 순서와 같아 읽기 좋지만, 핵심 스토리가 U6 끝(약 75% 지점)에야 동작하고 에디터(가장 큰 UI 작업)가 플레이를 늦춘다.
C) **U3와 U4를 번갈아**: U1 → U2 → U4 → U3 → U5 → … — 두 축을 고르게 진행하지만 컨텍스트 전환이 잦다.
X) Other (please describe after [Answer]: tag below)

[Answer]: A — 플레이 먼저: U1 → U2 → U4 → U5 → U6 → U7 → U3 → U8 (대화창 답변, 2026-09-29)

## 답변 분석 (Step 7)
- UOW-R1=A, UOW-R2=A. 단일 선택, 서로 일관(8유닛 + 플레이 먼저). 후속 질문 없음.
- 확정 실행 순서: **U1 경계 재정리 → U2 World File·캐노니컬 기반 → U4 플레이어 모드 → U5 NPC 대화·언어 → U6 행적·전파 → U7 GM 모드·안정화 → U3 월드 에디터 → U8 데모·배포·문서**. 번호는 의존 그림(U3가 U4보다 앞선 번호)을 유지하고, 실행 순서만 위와 같다.

## 질문 없이 정하는 것
- 프론트 구조(react-router 스켈레톤, `api/{world,knowledge,play,gm}.ts`)는 U1이 만들고, 각 화면은 해당 기능 유닛이 채운다(U3 editor, U4·U5·U6 play, U7 gm).
- 테스트 체크포인트는 실행 계획대로: U1 끝 305 GREEN + boundaries · U2 World File 왕복 PBT · U4 이동 단조성 PBT · U5 아는 범위 PBT · U6 전파 불변식 PBT · U7 소문 상한 시나리오 · U8 Build&Test 통합 + 라이브 시나리오.
- 유닛마다 커밋 하나(또는 PR). Q4=A라 마이그레이션 없이 스키마를 새로 만든다(`init-schema --play` 재실행).
