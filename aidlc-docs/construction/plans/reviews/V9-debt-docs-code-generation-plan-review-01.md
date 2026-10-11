## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — V9 부채·문서 마무리
**Reviewed artifact:** `aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-11T14:59:58Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > Step 4.5 / § 1.1 W-4 | `tests/shared/storage/fakes.py:64-75`의 `upsert_edges`를 병합으로 바꾸면 같은 파일의 `replace_edges`가 깨진다. 지금 `replace_edges`는 `self.upsert_edges(edges)`를 부르고 독스트링도 "the fake's upsert already replaces whole"이라 적는다. 병합이 되면 지운 속성(예: 지운 `wiki_prior_ref`)이 남아 `tests/shared/storage/test_port_contract.py:247`(`test_replace_edges_keeps_exactly_the_written_properties`)와 에디터 연결 시험이 틀어지거나, 더 나쁘게는 `replace_edges`가 Neo4j(`SET r = $props`)와 달라진다. 계획은 이 의존을 말하지 않는다. | 4.5에 `replace_edges`를 `upsert_edges`에서 떼어 전체 교체(`SET r = $props`와 같음)로 따로 구현한다고 적고, 병합 동작을 직접 시험하는 계약 시험(`test_port_contract.py`, 둘 다 구현에 돌아감)을 더한다. `tests/world/editor/helpers.py:66`의 계량 대역도 확인 목록에 넣는다. | New |
| R-02 | Major | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > Step 8.2, 8.4, 8.5 | FR-T4(follow-up-requirements.md)와 code-quality-assessment § G가 요구하는 항목 중 계획에 없는 것이 있다. README "NPC가 만들어집니다"(RE-W18), `operations.md:405` "두 번째 시작은 409", `operations.md:276` interrupted run 문장, `operations.md:402`의 "LLM을 부르지 않는다"(8.2는 README만 말함), docstring 중 `cache.py:4` "no TTL"과 `api/errors.py` 매핑 목록. unit-of-work 완료 조건은 "CLAUDE.md Status·Gates"만 걸지만 FR-T4는 P0이고 8.6 확인("문서가 말하는 수치·경로가 실제와 같은지")도 이 항목들을 못 본다. 8.4는 반대로 요구에 없는 "V1·V3 운영 메모"를 더한다. | 8.2·8.4·8.5에 빠진 항목을 넣거나, 고치지 않는 것을 이유와 함께 `next-cycle.md`(Step 9)에 올리고 § 3 요구 대응 표에 그렇게 적는다. FR-T4의 항목마다 한 줄씩 닫힘 표를 code-summary § 3에 둔다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > § 1.3 문서의 언어 표시, Step 5.3 | 계획은 `setLang`이 `document.documentElement.lang`을 바꾸게 "더한다"고 하지만 `web/src/i18n/index.ts`에 이미 있다(36행 처음 읽을 때, 46행 `notify()`). 실제로 틀린 것은 `web/index.html`의 `lang="en"` 정적 값뿐이다. 코드 사실이 거짓이라 5.3은 불필요한 변경이 되거나 중복 구현이 된다. | 5.3을 "이미 있음 — `index.html` 기본값만 ko로, 현 동작을 지키는 시험 한 개"로 고친다. 저장된 언어가 en일 때 깜빡임이 없는지는 현 코드 기준으로 적는다. | New |
| R-04 | Minor | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > § 1.2 FR-T7, Step 6 | 10a 방향 단언을 `/events?status=active`의 `contributions`로 한다고 했으나 `contributions`는 지역 id를 키로 하고 `/state`와 시나리오의 HARBOR·CRAG는 지역 이름이다(`scripts/live_scenario.py:_state`). 이름→id 대응을 어디서 얻는지 적혀 있지 않다. 또 poll 하한의 값과, `--poll 0`을 거부할지 올릴지가 정해지지 않았다. 가짜 서버(`tests/test_live_scenario.py`)는 지금 `/events` 경로가 없다. | 대응 출처(`/state`의 region_id 또는 `/regions`)와 하한 값·동작(오류 종료 또는 최소값)을 6.1에 적는다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > § 1.2 FR-T6, Step 4.1·4.2, 4.5 | 4.1의 "b_done이 짧은 시간 안에 오지 않음" 단언은 그 자체가 시간 의존 부정 단언이다. 한도 값(예: 0.2 s)과 A를 풀기 전에 단언한다는 순서, 실패 때 쓰레드가 매달리지 않게 하는 안전 대기(`join` 시한)를 정하지 않았다. 4.2는 `narration == ["C: 1 new rumor, event applied"]` 같은 현 리터럴이 실제 값인지 모른 채 "그대로 단언"한다. 4.5 `/health` 시험은 `do_assemble`가 거짓이라 늘 `ok`인 공허한 단언인데(`api/main.py:198`) 어떻게 실패할 수 있게 하는지 적지 않았다. | 한도와 순서, 4.2의 실제 값을 먼저 읽어 확정한다는 단서, 4.5의 구체 단언(예: 조립된 경계 하나를 `None`으로 두면 `degraded`)을 적는다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/V9-debt-docs-code-generation-plan.md > § 1.3 CI, Step 2·3.2 | 완료 조건은 "npm audit 전체 0"인데 CI `audit` 잡은 `--omit=dev`로 남는다. 의도된 것이면 그렇게 적어야 하고(전체 0은 일회성 확인), 아니면 회귀를 막지 못한다. `npm audit fix`가 `package-lock.json`(추적됨)을 바꾸므로 CI `npm ci`와 맞는지 `npm ci --dry-run`류 확인도 2.2에 없다. 한편 mypy 단계는 CI가 `pip install -e ".[dev]"`에 mypy를 포함하므로(`pyproject.toml`) 설치 면에서 실행 가능하다. | 전체 audit을 CI에 넣을지 일회성인지 한 줄로 정하고, 2.2에 lock 일관성 확인을 더한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `.venv/bin/mypy locus api` | 11 errors in 6 files; lines match § 1.2 table (reconciler:126, hierarchy:68, linker:51, neo4j_repo:46-47, opensearch_repo:98-99, openai_provider:28,72,92,111) | Plan's mypy facts are true; fixes are plausible and behavior-preserving |
| `cd web && npm audit` | 5 vulns (3 moderate, 2 high), all "fix available via npm audit fix"; vitest ^4.1.9 in range | FR-T2 baseline true |
| `ruff check scripts` / `black --check scripts` | clean now | W-3 adds `scripts` to CI without new fixes needed |
| `test_u4_uow_rollback...` (test_repository_contract.py:258-292), `or True` in test_player_mode.py:611-616 | both present as described | FR-T6 mechanism claim true |
| `locus/shared/llm/retry.py` | tenacity uses default sleep; no module-level `_sleep` | Step 4.3 implementable |
| `fakes.py` `replace_edges` -> `upsert_edges`; `neo4j_repo.upsert_edges` uses `SET r +=` | fake replaces whole, Neo4j merges | Confirms W-4 direction and R-01 coupling |
| `web/src/i18n/index.ts` lang handling | `documentElement.lang` set at init and in `notify()` | Contradicts Step 5.3 premise (R-03) |
| `web/index.html`, `web/public/` | title "Locus — Spatial Knowledge", `lang="en"`; no public/ | FR-D10 baseline true |
| `api/main.py:198` health, keyless test | `status` is `ok` when `do_assemble` false | #21 vacuous assertion real (R-05) |
| `.github/workflows/ci.yml` | no mypy step; ruff/black on `locus api tests`; audit job `--omit=dev` | Step 3.2 baseline true |
| FR-T4 bullets vs Step 8 | README NPC sentence, operations 405/276/402, cache.py:4, errors.py list absent | R-02 |
| `SessionEvent.contributions` via `EventOut`; `/events?status=` route | exists | Step 6 data source valid, id-vs-name gap (R-04) |
| unit-of-work V9 completion conditions (4) | each mapped to a step in § 3 | Covered, subject to R-02 |

### Summary

The plan's code facts (mypy lines, audit set, test defects, CI baseline) check out and the scope matches the human's answer A. Two Majors need fixing in Part 2 or the plan before approval: the fake `replace_edges` coupling to the merged `upsert_edges` (R-01) and the FR-T4 documentation items the steps omit (R-02); the rest are Minor corrections (the `setLang` premise is already true in code).
