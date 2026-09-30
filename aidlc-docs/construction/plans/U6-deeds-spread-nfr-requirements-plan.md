# U6 행적·전파 — NFR Requirements + Design (light) 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U6의 비기능 요구를 한 장으로 확정합니다. 다루는 것은 행동 응답성, 턴 LLM 예산과 프롬프트 크기, 주입, 스키마 보존, 회귀, PBT, 문서입니다. 코드 생성 플랜이 지킬 수치와 방법을 정하는 단계입니다.

실행 계획(`inception/plans/purpose-restructure-execution-plan.md` §NFR)대로 플레이 유닛은 **light**다. `construction/U6-deeds-spread/nfr/nfr-light.md` 한 장에 요구와 설계를 함께 적는다. 새 기술 스택 선택은 없다(C-3, C-4). Plan Review는 light 규칙대로 **advisory 한 번**이고 검토자는 architecture-reviewer다. 기록은 `construction/U6-deeds-spread/nfr/reviews/nfr-light-review-01.md`다.

## 플랜
- [x] 승인된 FD 산출물 분석(`construction/U6-deeds-spread/functional-design/*`, 검토 02의 R-10·R-15·R-16·R-17 disposition과 제안 셋)
- [x] NFR-1~9와 U6의 접점 정리; 질문 필요 여부 판단
- [x] `construction/U6-deeds-spread/nfr/nfr-light.md` 작성(요구 + 설계 + 수치 + 검증 방법 + 코드 플랜 입력)
- [ ] Plan Review(architecture-reviewer, **advisory** 1회) → `construction/U6-deeds-spread/nfr/reviews/nfr-light-review-01.md`
- [ ] 완료 메시지 + 승인 게이트 → 다음: U6 Code Generation Part 1(플랜)

## 질문
없다. U6에 걸리는 값은 FD에서 정해졌다.
- 턴 예산 순서는 Q2=A(준비 호출 예약 → 전파 → 캐노니컬)다.
- 서술 언어는 Q3=A다.
- 조정값 여섯(domain-entities §5)과 LLM 호출 위치(배경 실행 안, 이탈 3)도 FD에 있다.

아래 가정은 값이 비어 있던 곳을 채운 것이고, 게이트나 코드 생성 플랜의 질문에서 바꿀 수 있다.

## 가정 (nfr-light.md에 반영)
| # | 가정 | 근거 |
|---|---|---|
| N6-1 | 행동 요청(`act`)은 지금처럼 LLM 없이 202로 곧바로 답한다. 서술과 판단은 배경 실행에서 돌고, 서술은 실행 결과로 온다. 화면은 기존 진행 표시를 쓴다 | NFR-3, FD 이탈 3 |
| N6-2 | LLM 출력은 저장 전에 길이를 자른다. 기준은 서술 1,000자, 기록·요약·`retelling` 300자, `slant` 40자다. 자른 값만 다른 프롬프트(NPC 컨텍스트, 전파, 사건 제안)로 이어진다 | FD 검토 02 제안 (3), NFR-5 |
| N6-3 | 열 추가는 inspector 방식으로 두 방언 모두에서 한다(BR-U6-34). 요구 Q4=A는 "마이그레이션 코드 불필요"였다. 이것은 기존 세션 데이터를 지키려는 선택이고, 비용은 코드 약 40줄과 테스트 하나다. **이탈로 적고 게이트에서 확인받는다** | FD 검토 02 제안 (1) |
| N6-4 | 실패 보상이 지운 행적의 타임라인 줄(`ACTION_DECLARED`·`DEED_RECORDED`)은 감사 흔적으로 남긴다. GM 행적 패널은 이 줄을 쓰지 않으므로 끊긴 `deed_id`는 화면에 영향이 없다 | FD 검토 02 제안 (2) |
| N6-5 | 주입: 선언은 서술 프롬프트의 가드 문장이 막는다(FD §2.2). 대화 발언은 판단의 `summary`·`retelling`을 거쳐 다른 NPC 프롬프트와 전파 프롬프트로 이어질 수 있다. 막는 것은 길이 상한(N6-2)과 "자료이지 지시가 아니다"라는 프레이밍 문장이다. 남는 위험은 감수하고, GM 취소가 되돌리는 수단이다 | NFR-6, 로컬 1인 데모 |
| N6-6 | 규모(A-4 데모)는 지역 10~15개, NPC 지역당 1~3명이다. 행적은 세션당 수백 개, 판단은 행적 × 대화한 NPC 수다. 턴당 전파는 지역 수와 턴 예산 이하다. 색인은 `deeds.session_id`·`deeds.run_id`, `deed_appraisals.session_id`·`deed_id`, `session_rumors.origin_deed_id`에 둔다 | NFR-5, A-4 |
