# U4 플레이어 모드 — NFR Requirements + Design (light) 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG.
**지금 하는 것**: U4 플레이어 모드의 비기능 요구(응답성·LLM 비용·회귀·PBT·보안·품질)를 한 장으로 확정 — 코드 생성 플랜이 지켜야 할 수치와 방법을 정하는 단계.

실행 계획(`inception/plans/purpose-restructure-execution-plan.md` §NFR): 플레이 유닛은 **light** — 유닛별 `nfr/nfr-light.md` 한 장에 요구와 설계를 함께 적는다. 새 기술 스택 선택은 없다(C-3, C-4). Plan Review는 light 규칙대로 **advisory 한 번**(architecture-reviewer), 기록은 `construction/U4-player-mode/nfr/reviews/nfr-light-review-01.md`.

## 플랜
- [x] 승인된 FD 산출물 분석(`construction/U4-player-mode/functional-design/*`, 검토 기록 02의 R-09~R-15 disposition)
- [x] NFR-1~9(요구 §NFR)와 U4의 접점 정리; 질문 필요 여부 판단
- [x] `construction/U4-player-mode/nfr/nfr-light.md` 작성(요구 + 설계 + 수치 + 검증 방법 + 코드 플랜 입력)
- [x] Plan Review(architecture-reviewer, **advisory** 1회) → `construction/U4-player-mode/nfr/reviews/nfr-light-review-01.md`
- [x] 완료 메시지 + 승인 게이트 → 다음: U4 Code Generation Part 1(플랜)

## 질문
없음. 요구 §NFR의 수치(턴당 LLM ≤ 8, 지역·턴당 새 소문 ≤ 2)와 FD 답(Q1~Q6), 게이트 결정(지역당 활성 소문 상한)이 U4에 걸리는 NFR을 이미 정한다. 아래 가정은 값이 정해지지 않은 것에 기본값을 둔 것이고, 코드 생성 플랜의 질문에서 바꿀 수 있다.

## 가정 (nfr-light.md에 반영)
| # | 가정 | 근거 |
|---|---|---|
| N-1 | 지역당 활성 소문 상한 `max_active_rumors_per_region = 20` | FD 게이트 "지역당 상한으로"(값 미지정), R-15 |
| N-2 | 응답성 목표(LLM 없는 로컬 기준): `POST act` 202 ≤ 200ms p95, `GET region` ≤ 100ms p95(캐시 적중), 폴링 간격 700ms | NFR-3, FD Q4=A, frontend §2.1 |
| N-3 | 배경 실행기 종료 대기 30초; 워커는 데몬 스레드; LLM 호출 timeout은 provider 어댑터 설정에 의존(없으면 코드 플랜에서 추가) | R-08, R-14 |
| N-4 | 실패 기록에는 예외 클래스 이름만 남기고 본문은 서버 로그로 | NFR-6 "에러 응답에 내부 정보 노출 없음" |
| N-5 | 규모: 세션당 플레이어 1, 데모 월드 ≤ 15 지역, 지역당 활성 소문 ≤ 20 → 세션당 ≤ 300 소문; 단일 프로세스·단일 워커 | 요구 A-4, 운영 문서(`--workers 1`) |
