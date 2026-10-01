# U7 GM 모드·안정화 — NFR Requirements + Design (light) 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U7의 비기능 요구를 한 장으로 확정합니다.
- 다루는 것: 의도된 동작 변경과 회귀, PBT, `/state`·로그 응답성, 프롬프트 크기와 주입, 스키마 보존, 코드 품질(패널 분할), 문서
- 코드 생성 플랜이 지킬 수치와 방법을 정하는 단계입니다.

실행 계획 §NFR대로 플레이 유닛은 **light**다.
- `construction/U7-gm-mode-hardening/nfr/nfr-light.md` 한 장에 요구와 설계를 함께 적는다.
- 새 기술 스택 선택은 없다(C-3, C-4).
- Plan Review는 light 규칙대로 **advisory** 1회다.

## 플랜
- [x] 승인된 FD 산출물 분석(`construction/U7-gm-mode-hardening/functional-design/*`, 검토 01 R-01~R-09 Accepted risk)
- [x] NFR-1~9와 U7의 접점 정리; 질문 필요 여부 판단
- [x] `construction/U7-gm-mode-hardening/nfr/nfr-light.md` 작성
- [ ] Plan Review(architecture-reviewer, **advisory** 1회) → `construction/U7-gm-mode-hardening/nfr/reviews/nfr-light-review-01.md`
- [ ] 완료 메시지 + 승인 게이트 → 다음: U7 Code Generation Part 1(플랜)

## 질문
없다. U7에 걸리는 값은 FD에서 정해졌다.
- 되먹임 상한·복원량, 강한 소문 기준(Q2·Q4)
- 제안 상한 5·지역 30
- 조정값 env(domain-entities §5)

아래 가정은 값이 비어 있던 곳을 채운 것이다. 게이트나 코드 생성 플랜에서 바꿀 수 있다.

## 가정 (nfr-light.md에 반영)
| # | 가정 | 근거 |
|---|---|---|
| N7-1 | `/state`·`/distortions`·`/log`는 LLM 없이 로컬 p95 ≤ 100ms다(데모 규모). 오프라인 게이트는 구조 단언이다. `/state`는 저장소 질의 5회이고 지역 수에 비례하지 않는다. `npcs`는 메시지 수 질의 1회다 | NFR-3, U5 NFR-3 방식 |
| N7-2 | `/state`의 다섯 읽기는 한 트랜잭션으로 묶지 않는다. 턴 커밋이 사이에 끼면 한 번은 섞인 값이 보일 수 있다. 표시용이고 다음 읽기가 고친다(FD 검토 R-07 Accepted) | NFR-3, R-07 |
| N7-3 | 프롬프트로 들어가는 플레이어 글과 그 파생 글은 줄바꿈을 공백 하나로 바꾸고 상한으로 자른다. 대상은 선언, 대화 발언, 행적 텍스트, `retelling`, 사건 설명, 지역 설명이다. 이것이 U5가 넘긴 "줄바꿈 위조"와 U6 리뷰 #6을 닫는다. 화면에 보이는 원문은 그대로다 | NFR-6, U6 리뷰 #6·#7 |
| N7-4 | 제안 프롬프트 크기의 상한은 약 `30 × (이름 + 경로 + 설명 160자 + 지식 2)` + 사건 5 × 160자 + 행적 5줄이다. 대략 8k자 이하로 본다. 지금 LLM 호출 수는 그대로다(제안 1회) | NFR-5 |
| N7-5 | 플레이어 로그는 요청마다 세션 타임라인 전체를 읽어 거른다(O(줄 수)). 데모 세션(수백 턴, 수천 줄)에서 충분하다. 페이지 나누기는 범위 밖이다 | NFR-3, A-4 |
| N7-6 | 의도된 동작 변경 목록(NFR-1)은 nfr-light §4가 갖는다. 바뀌는 테스트는 코드 생성 플랜이 이름으로 적는다(FD 검토 R-05) | NFR-1 |
