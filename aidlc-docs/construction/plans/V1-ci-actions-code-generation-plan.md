# V1 CI 시한 정리 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것.
**지금 하는 것**: Construction V1(실행 1/9), Code Generation 1부(계획). CI가 2026-10-19 Ubuntu 26 러너 전환 뒤에도 깨지지 않게 한다. 이 계획이 V1 코드 생성의 유일한 기준이다.

**근거**:
- 요구사항: `inception/requirements/follow-up-requirements.md` FR-T1, C-4.
- 유닛: `inception/application-design/follow-up/unit-of-work.md` V1.
- 결정: UOW-Q2=A(mypy 게이트는 V9), UOW-Q3=A(V1은 main에서 따로 작은 PR).
- 브랜치 결정(Workflow Planning, R-06): PR #4 병합 → `feat/follow-up`.

**단계**: FD SKIP · NFR SKIP(설정 파일 하나) · Code.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 요구사항 | FR-T1: 액션을 Node 24 대상 주 버전으로 올리고, Ubuntu 26에서 네 잡이 통과하는지 확인하거나 러너를 명시한다. 2026-10-19 전에 끝낸다 |
| 바꾸는 파일 | `.github/workflows/ci.yml` 하나 |
| 바꾸지 않는 것 | 잡 구성(backend·frontend·audit·images), Python 3.11, Node "22", 게이트 명령. mypy 단계는 넣지 않는다(V9) |
| 의존 | 없음(독립 유닛) |
| 계약 | 이후 모든 유닛의 PR이 새 액션과 러너에서 GREEN이어야 한다 |

### 조사한 사실 (2026-10-07, `gh api`로 확인)
- 최신 주 버전은 셋 다 v7이다: `actions/checkout` v7.0.1(2026-07-20), `actions/setup-node` v7.0.0(2026-07-14), `actions/setup-python` v7.0.0(2026-07-20). 세 `action.yml` 모두 `runs.using: node24`다. 그래서 Node 20 경고가 사라진다.
- 주 버전 사이에 우리에게 걸리는 변화는 둘이고, 둘 다 영향이 없다.
  - setup-node v5: `packageManager` 칸이 있으면 캐시를 자동으로 켠다. `web/package.json`에는 그 칸이 없고, frontend 잡은 `cache: npm`을 직접 적는다.
  - setup-python v7: `pip-install` 입력을 없앴다. 우리는 쓰지 않는다.
- 러너 라벨 `ubuntu-26.04`가 이미 있다(`actions/runner-images` README). 그 이미지에는 Python 3.11.16, Node 22.23.3, Docker Client/Server 29.4.2, Buildx 0.37.1이 있다. python-versions manifest의 3.11.17은 26.04용 빌드를 낸다.

### 러너 선택: `ubuntu-26.04`로 명시한다
- **까닭**: 10-19 전환을 기다리지 않고 지금 26.04에서 통과를 확인한다. 그 뒤로 러너가 말없이 바뀌지 않는다.
- **대안**: `ubuntu-latest`를 두면 전환일에 처음으로 26에서 돈다. `ubuntu-24.04`로 묶으면 26 확인을 미룬다.
- **되돌리기**: 한 줄만 바꾸면 된다. 26.04에서 실패하고 바로 고칠 수 없으면, `ubuntu-24.04`로 묶고 그 사실을 `next-cycle.md`에 남긴다(V9).

---

## 2. 단계

### Step 0 — 전제: PR #4 병합 (사람)
- [x] 사람이 `gh pr merge 4 --merge`를 실행한다. 그 뒤 Claude가 `gh pr view 4 --json state,mergedAt`로 병합을 확인한다.

### Step 1 — 브랜치 구성
- [x] 1.1 `git fetch origin`
- [x] 1.2 `feat/follow-up`을 `origin/main`에서 만든다(`git switch -c feat/follow-up origin/main`). 커밋하지 않은 이번 주기 문서(`aidlc-docs/**`: 역공학, 요구사항, 계획, 설계, 유닛, audit, state, 이 계획)는 작업 트리를 따라온다. 옮긴 뒤 `git status`로 빠진 것이 없는지 확인한다.
- [x] 1.3 `feat/follow-up`에 이번 주기 Inception 문서를 커밋한다(`docs(aidlc): follow-up cycle inception — RE rerun, requirements, plan, design, units`). **이 계획의 승인이 이 커밋의 허락이다.** 푸시는 사람이 한다.
- [ ] 1.4 `chore/ci-actions`를 `origin/main`에서 만든다(`git switch -c chore/ci-actions origin/main`). 작업 트리가 깨끗한지 확인한다.

### Step 2 — `ci.yml` 수정 (`chore/ci-actions`에서)
- [ ] 2.1 `actions/checkout@v4`를 `@v7`로 바꾼다(네 잡 모두).
- [ ] 2.2 `actions/setup-python@v5`를 `@v7`로 바꾼다(backend). 입력(`python-version: "3.11"`, `cache: pip`, `cache-dependency-path`)은 그대로 둔다.
- [ ] 2.3 `actions/setup-node@v4`를 `@v7`로 바꾼다(frontend, audit). 입력은 그대로 둔다.
- [ ] 2.4 네 잡의 `runs-on: ubuntu-latest`를 `ubuntu-26.04`로 바꾼다.
- [ ] 2.5 파일 머리 주석에 한 줄을 더한다: 러너를 명시한 까닭(10-19 `ubuntu-latest` 전환 전에 26.04에서 확인함, 다시 바꿀 때는 이 줄)과 액션 주 버전(node24).

### Step 3 — 로컬 확인
- [ ] 3.1 YAML 파싱: `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`
- [ ] 3.2 남은 옛 버전이 없다: `grep -nE '@v[45]\b|ubuntu-latest' .github/workflows/ci.yml`의 결과가 비어야 한다(주석 안의 설명 문장은 예외로 확인한다).
- [ ] 3.3 바뀐 파일이 `ci.yml` 하나뿐이다: `git diff --stat`.

### Step 4 — 커밋과 CI 확인
- [ ] 4.1 `chore/ci-actions`에 커밋한다(`ci: move actions to v7 (node24) and pin ubuntu-26.04 ahead of the 2026-10-19 runner switch`). 푸시는 하지 않는다.
- [ ] 4.2 사람에게 명령을 드린다: `git push -u origin chore/ci-actions`, `gh pr create --base main --head chore/ci-actions …`. 사람이 실행한다.
- [ ] 4.3 Claude가 `gh run list --branch chore/ci-actions` → `gh run watch`(읽기 전용)로 지켜본다. 확인할 것은 셋이다: 네 잡이 GREEN인가, 주석에 Node 20 경고가 없는가, 러너가 `ubuntu-26.04`인가.
- [ ] 4.4 실패하면 원인을 적는다. ci.yml 안에서 고칠 수 있으면 고쳐 다시 커밋하고 4.2로 돌아간다. 이미지·러너 문제로 바로 고칠 수 없으면, 사람에게 `ubuntu-24.04` 묶음(되돌리기)을 여쭙는다.

### Step 5 — 병합 뒤 정리 (사람의 병합 뒤)
- [ ] 5.1 사람이 CI PR을 병합한다.
- [ ] 5.2 `feat/follow-up`으로 돌아와 `git fetch origin && git merge origin/main`으로 새 ci.yml을 받아 들인다(merge 커밋). 충돌은 없다고 본다(`feat/follow-up`은 ci.yml을 고치지 않는다).

### Step 6 — 기록
- [ ] 6.1 `aidlc-docs/construction/V1-ci-actions/code/code-summary.md`를 쓴다: 바뀐 줄, 조사한 사실, CI 실행 id와 결과, 남은 일(mypy 단계는 V9).
- [ ] 6.2 `aidlc-state.md`의 V1 진행을 갱신하고, `audit.md`에 남긴다.

---

## 3. 완료 조건
- 네 잡(backend, frontend, audit, images)이 `ubuntu-26.04`와 v7 액션에서 GREEN이다.
- CI 주석에 Node 20 경고가 없다.
- CI PR의 변경은 `.github/workflows/ci.yml` 하나뿐이다.
- `feat/follow-up`에 Inception 문서가 커밋되어 있고, 병합 뒤 main을 받아 들였다.
- 이번 유닛은 애플리케이션 코드를 바꾸지 않는다. 그래서 pytest·vitest 결과는 CI 실행으로 확인한다.

## 4. 추적
| 요구사항 | 단계 |
|---|---|
| FR-T1 액션 주 버전 | 2.1~2.3 |
| FR-T1 Ubuntu 26 확인 또는 러너 명시 | 2.4, 4.3 |
| C-4 시한 2026-10-19 | 4.2~5.1 |
| UOW-Q3 따로 작은 PR | 1.4, 4.1~4.2 |
| R-06 브랜치 결정 | 0, 1.2~1.3, 5.2 |
