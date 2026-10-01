# U8 데모·배포·문서 — Code Summary (작성 중)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 코드 생성 중입니다. 이 문서는 단계마다 바뀐 것과 그 검증을 모읍니다(Step 16에서 마무리).

플랜: `construction/plans/U8-demo-deploy-docs-code-generation-plan.md` (17단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `589dc2b`) | 결과 (Step 16.1) |
|---|---|---|
| pytest | 857 | |
| vitest | 129 | |
| mypy (`locus api`) | 11 (6 파일) | |
| ruff · black · tsc | clean | |
| `npm ci` (깨끗한 설치) | 된다(202 패키지) | |
| `npm audit --omit=dev` | moderate 2 (react-router 6.30.6) | |

## 2. 단계별 기록
- **Step 1**
  - 1.1 기준선을 다시 쟀다(위 표).
  - 1.2 승인 산출물 정정(〔Step 1.2 정정〕).
    - FD BLM §7: 9a 기다리기(R-05).
    - FD frontend-components §3: `startSeed` 타입(R-12).
    - FD domain-entities §5.2·BR-U8-11: Ironcrag 전해 들음 목록(R-13).
    - FD BR-U8-35: react-router 7.18.x(사람의 결정).
    - Infra §1 web healthcheck 127.0.0.1(R-02), §3.1 package-data(R-04a), §3.2 nginx 49m(R-03), §5 설치본에서 확인(코드 플랜 R-02).
