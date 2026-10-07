# V1 CI 시한 정리 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것.
**지금 하는 것**: V1 코드 생성을 마쳤다(Step 0~6). CI가 2026-10-19부터 시작되는 Ubuntu 26 러너 전환 뒤에도 깨지지 않게 했다. 이 문서는 바뀐 것, 확인 결과, 실행 메모(리뷰 R-01~R-04), 남은 일을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V1-ci-actions-code-generation-plan.md`(승인 2026-10-07T10:26:05Z).
요구사항: FR-T1, C-4.

## 1. 바뀐 것

| 파일 | 변경 |
|---|---|
| `.github/workflows/ci.yml` (수정) | `actions/checkout@v4`→`@v7`(4곳), `actions/setup-python@v5`→`@v7`(1곳), `actions/setup-node@v4`→`@v7`(2곳), `runs-on: ubuntu-latest`→`ubuntu-26.04`(4곳), 머리 주석 3줄 |

- 바꾸지 않은 것: 잡 구성(backend·frontend·audit·images), Python 3.11, Node "22", 입력(`cache`, `cache-dependency-path`), 게이트 명령. mypy 단계는 넣지 않았다(V9).
- 애플리케이션 코드와 테스트는 바뀌지 않았다.

## 2. 브랜치와 커밋

| 순서 | 무엇 | 커밋 |
|---|---|---|
| Step 0 | 사람이 PR #4를 병합 | `dc8a947`(2026-10-07T10:43:37Z) |
| Step 1.3 | `feat/follow-up`에 Inception 문서 커밋(39파일) | `f34b52f` |
| Step 4.1 | `chore/ci-actions`에 ci.yml 커밋 | `c2a1077` |
| Step 4.2 | 사람이 푸시하고 PR #5를 염 | — |
| Step 5.1 | 사람이 PR #5를 병합 | `d570f00`(2026-10-07T11:27:22Z) |
| Step 5.2 | `feat/follow-up`이 main을 받아 들임(충돌 없음) | `3a13155` |

- 두 브랜치 모두 `origin/main`에서 만든 뒤 upstream을 지웠다. 첫 `push -u`가 같은 이름의 원격 브랜치를 잡게 하려는 것이다.
- `feat/follow-up`은 아직 원격에 없다. 푸시는 사람이 한다.

## 3. 확인

로컬(Step 3):
- YAML이 파싱된다. 네 잡 모두 `ubuntu-26.04`이고 액션은 v7이다.
- 옛 버전 grep(`@v[45]\b|ubuntu-latest`)에는 주석 한 줄(4행)만 걸린다.
- `git diff --stat origin/main`에서 바뀐 파일은 ci.yml 하나다(+14/−11).

CI(Step 4.3, 커밋 `c2a1077`):

| 실행 | 이벤트 | 결과 |
|---|---|---|
| [37612503032](https://github.com/hongsam14/Locus/actions/runs/37612503032) | push | success |
| [37612594534](https://github.com/hongsam14/Locus/actions/runs/37612594534) | pull_request | success |

- 여덟 잡(실행마다 audit·frontend·images·backend)이 모두 pass다.
- 경고 주석은 여덟 잡 모두 0건이다(`gh api repos/hongsam14/Locus/check-runs/{job}/annotations`). Node 20 경고가 사라졌다.
- 러너는 여덟 잡 모두 잡 로그 "Set up job"에 `Image: ubuntu-26.04`(Version 20260927.149.1)로 나온다.
- 테스트: pytest 948 passed, vitest 202 passed(9 files). 지난 주기와 같은 수다.
- images: Docker 29에서 app·web 이미지가 빌드되고, 설치본 `check_packaged()`와 `import api.main`이 통과한다.
- GitGuardian pass. PR #5는 MERGEABLE/CLEAN으로 병합되었다.

## 4. 실행 메모 (코드 플랜 리뷰 R-01~R-04, Accepted risk)

| 지적 | 어떻게 지켰나 |
|---|---|
| R-01 전환 시점 문구 | 주석에 "the ubuntu-latest switch to 26.04 starts 2026-10-19 and completes 2026-11-19 (actions/runner-images #14748)"라고 썼다 |
| R-02 확인 방법 | 경고는 check-runs annotations API로 확인했다. 러너는 잡 로그의 Image 줄로 확인했다(`gh api …/actions/jobs/{id}/logs`; `gh run view --log`와 같은 내용) |
| R-03 기록 브랜치 | audit·state 기록은 모두 `feat/follow-up`에서만 했다. CI 브랜치는 ci.yml 하나뿐이다. 커밋 직전에 `git diff --stat origin/main`을 확인했다 |
| R-04 병합 방식 대비 | 병합 뒤 `git diff --stat HEAD origin/main -- aidlc-docs`가 비어 있어 stash 없이 브랜치를 바꿨다 |

## 5. 이탈

- 사람이 입력한 명령 두 개가 처음에 실패했다. 하나는 브랜치 이름 오타(`chore/ci-action`), 다른 하나는 PR 명령이 줄바꿈에서 둘로 나뉜 것이다. 둘 다 다시 실행해 성공했다. 원격에는 영향이 없었다.
- Step 5.2의 병합 커밋 메시지에 공동 작성 줄을 더하려고 로컬에서 고쳐 썼다(`--amend`, 푸시 전).
- 계획에서 벗어난 코드 변경은 없다.

## 6. 남은 일

- **mypy CI 게이트**: V9에서 11건을 0으로 만든 뒤 켠다(UOW-Q2=A). 그때까지는 유닛마다 로컬에서 기준선 11이 늘지 않는지 본다.
- **러너를 다시 바꿀 때**: ci.yml의 `runs-on` 네 줄을 고친다. 머리 주석에 적어 두었다.
- **되돌리기**: 26.04에서 문제가 생기면 네 줄을 `ubuntu-24.04`로 바꾼다. 이번에는 필요 없었다.
