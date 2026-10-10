## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — V7 월드·지식 정확성
**Reviewed artifact:** `aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-10T15:25:49Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 3.2·3.3 ("EX-18·EX-19는 손대지 않는다") | 기존 `tests/knowledge/test_cache.py::test_hit_is_refreshed_when_the_world_version_changes` 끝부분이 새 규칙과 정면으로 부딪힌다. `loader.version_value = None`(메타 없는 월드)으로 `invalidate` 한 뒤 `again = cache.get("w"); assert cache.get("w") is again`로 "메타 없는 월드는 무효화만"을 단언한다. Step 3.2는 버전 `None`이면 캐시하지 않으므로 두 번째 `get`은 다시 불러와 다른 객체를 내고 이 시험이 실패한다. 계획은 "손대지 않는" 시험으로 EX-18·EX-19만 말하고 이 시험은 언급이 없다. Step 3 커밋의 게이트가 RED가 된다. | Step 3.3에 이 시험을 새 규칙(버전 `None` → 캐시 안 됨, `UNVERSIONED` → 캐시됨)에 맞게 고친다고 적고, code-summary § 4의 "바뀐 기존 시험"에 올린다. 이 시험이 하던 "메타 없는 월드는 무효화만"의 의미가 바뀌었음을 한 줄로 밝힌다. | New |
| R-02 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 3.2 | `check_version=False`일 때 미스 갈래의 `version`은 지금 코드에서 `None`으로 남는다(`version: str \| None = None`, `_current_version`을 부르지 않음). 계획의 "버전이 `None`이면 캐시하지 않는다"를 글자대로 옮기면 `check_version=False` 캐시가 아무것도 캐시하지 못한다. FD § 2.2 3항은 이 경우 "지금처럼 캐시"라고 정했다. `check_version=False`를 쓰는 시험도 코드도 없어(grep) 회귀가 드러나지 않는다. | 3.2에 "`check_version`이 꺼져 있으면 저장할 버전은 `UNVERSIONED`"를 명시하고, 3.3에 `check_version=False` 캐시가 캐시한다는 시험 하나를 더한다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 8.2·8.3 (R-09 "None을 돌려준다", `kept_keys` 조건) | (a) 지금 `_confirm_or_edit`는 `None`을, `_write`는 `[]`를 돌려주므로 `apply_answer`가 "바뀐 것 없음"을 알아낼 길이 계획에 없다(반환값·센티널·예외 중 무엇인지 미정). (b) 서비스의 조건 "확인 답이 WIKI_CONFLICT이거나 `change is None`"에서 `change is None`은 IGNORE에서도 참이라, 글자대로면 [두기]가 `ignored_keys`와 `kept_keys` 양쪽에 들어간다. 또 "확인 답이"가 `or`의 한쪽에만 걸리는지도 모호하다. 구현자가 추측해야 한다. | (a) 무변경 신호를 `_write`→`apply_answer`로 어떻게 전하는지 한 줄로 정한다. (b) 조건을 `action == CONFIRM and (kind == WIKI_CONFLICT or change is None)`처럼 행동까지 넣어 쓰고, IGNORE는 `ignored_keys`만이라고 단언하는 시험을 더한다. | New |
| R-04 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 1.2 | 게이트 스크립트를 "scratchpad의 `v5gate.sh`를 `v7gate.sh`로 복사"해 만든다고 했지만 그 파일은 어느 scratchpad에도, `git ls-files`에도 없다(`ls /tmp/claude-1000/.../scratchpad`는 빈 디렉터리·다른 세션의 `live_scenario.py`뿐). 지금 계획만으로는 게이트 명령을 재현할 수 없다. | 게이트 명령(`ruff check`/`black --check` on `locus api tests`, `mypy locus api`, `pytest` with pipefail)을 계획 § 1.3에 그대로 적거나 스크립트를 이 단계에서 새로 만든다고 선언한다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 4.4 (TP-V7-12), 4.1 | (a) TP-V7-12는 "대역이 받은 `label` 인자를 단언한다"고 하지만, 어느 대역이 인자를 기록하는지 정해져 있지 않다. 현재 `MeteredGraph`는 호출 이름만 기록하고 `_CountingGraph`는 `get_node`를 겹쳐 쓰지 않는다. (b) `neo4j_repo.py`의 라벨 갈래(`MATCH (n:{_safe_ident(label)} …)`)를 확인하는 시험·돌연변이가 없다. `test_port_contract.py`는 이미 `MagicMock`으로 Neo4j 질의 모양을 본다. | (a) 인자를 기록할 대역(예: `MeteredGraph`에 `calls_with`)을 지정한다. (b) Neo4j 어댑터의 라벨 있는/없는 질의 모양 시험을 4.4에 한 줄 더하고 돌연변이 목록에 넣는다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 6.4, 7.6 (`tests/api/test_world_api.py`) | 그 파일의 빌더·불러오기는 고정 리포트를 내는 스텁(`_Builder`, `_Importer`)이다. "옛 월드 읽기 실패·백업 실패 → `replaced=false`, 열린 세션 그대로" 시험은 V7이 바꾼 빌더 코드가 아니라 이미 있는 `_close_if_replaced`를 확인할 뿐이라 V7 회귀를 잡지 못한다. 계획은 이것이 TP-V7-9의 세션 쪽 증거인 듯 쓴다. | 이 시험이 기존 라우터 규칙의 고정(스텁 리포트 `replaced=false`)임을 밝히고, V7 동작의 증거는 `test_build.py`·`test_worldfile.py`의 실제 빌더·불러오기 시험이라고 적는다. 또는 실제 `WorldBuilder`를 쓴 시험으로 바꾼다. | New |
| R-07 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 6.2 | `BackupFailedError`를 던지는 `_backup`은 현재 `try:` 안(`if exists:` 갈래)에서 불린다. 그대로 두면 바깥 `except Exception`이 받아 `stage="commit"`·"commit failed after preparing…" 리포트를 만들고 `stage="backup"` 리포트는 나오지 않는다. 6.2는 `replaced=false`, `backup_path=None` 리포트를 말하지만 이를 어디서 잡아 반환하는지(예: 지우기 앞의 전용 `except BackupFailedError`, `finally`의 invalidate 유지) 쓰지 않았다. 7.4의 ① 오류 리포트도 같은 처지다. | 6.2·7.4에 두 중단 경로를 `try` 안에서 `BackupFailedError`·읽기 오류를 먼저 잡아 리포트를 반환하고 `finally`는 그대로 도는 형태로 쓴다. | New |
| R-08 | Minor | aidlc-docs/construction/plans/V7-world-knowledge-code-generation-plan.md > Step 10.1 | 완료 확인에 pytest 개수(기준선 1138 + 새 시험 수)와 vitest 개수 확인이 없다. 기준선은 Step 1에서 재지만, 끝의 기대 개수가 없어 "시험이 사라지지 않았다"를 검증할 수 없다. 돌연변이 결과는 code-summary에 적는다고만 되어 있다. | Step 10.1에 "pytest 개수 ≥ 기준선 + 새 시험, 줄어든 시험 0"과 `vitest`가 바뀌지 않았음을 검사 항목으로 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| Existing paths named in the plan (consensus, cache, loader, base, neo4j_repo, persistence, reports, build, import_, remap, writes, regions, bundle, apply, questions, service, types, detectors, region_knowledge, rumor/service, tests/**, README, operations.md) | all exist | OK |
| New paths declared new (carry_over.py, test_consensus_props, test_v7_order, test_persist_order, test_carry_over) | none exist yet, all marked 새 | OK |
| `get_node`/`delete_node` call sites in locus/ | 12 (writes 4, regions 3, apply 4, bundle 1); plan: 9 labeled + 3 unlabeled (own_label, delete_any, apply._nodes) | Matches FD "9곳"; unit-of-work "11곳" was already revised by FD |
| Test doubles overriding `get_node`/`delete_node` | fakes.py, test_services.py `_GraphRepo`, helpers.py `MeteredGraph`; `_CountingGraph`/`_SnapshotCache` do not override | Plan's three doubles are complete |
| `self.graph._nodes` readers outside fakes.py | helpers.py 100/116/119, `.values()` only | Key change to (world,label,id) is safe |
| Existing tests broken by Step 3 rule | `test_cache.py::test_hit_is_refreshed…` version=None tail | Confirms R-01 |
| `check_version` users | only cache.py; no tests | Confirms R-02 |
| Builder cache doubles that raise on `get` (`_NoCache`, `_Cache`) | builds are first builds on fresh graphs (distinct ids "w","w2") | Plan's claim holds; Step 7 gate unaffected |
| Boundary rule for `world/carry_over.py` → `locus.knowledge.loader` | `ALLOWED["world"]` includes knowledge; world already imports knowledge.cache | OK |
| Demo World File duplicate ids (`emberleaf.world.json`) | none across 7 sections | Step 5 will not reject the demo |
| API tests for build/import | stub builder/importer (`test_world_api.py`) | Confirms R-06 |
| `NEEDS` users | only questions.py:141; tests assert `needs` for knowledge LOW_CONFIDENCE (unchanged by the new table) | OK |
| BR-V7-01~22 / TP-V7-1~14 / PBT-V7-1~5 mapped to steps | all land in Steps 2–8 (§ 3 table and step bodies) | OK |
| Loader dangling messages `"{what}: dangling reference"`, item_id = NPC/seed id | prefix constants + `item_id` give the id R-10 decision needs | OK |
| FR-C6~C10, C12, NFR-6 and the six unit-of-work completion conditions | each has a step and a test | OK |

### Summary

The plan is executable and traceable: paths, call-site counts, the three doubles and the boundary rule check out, and every BR/TP/PBT lands in a step. The one blocking-class defect is that Step 3 turns an existing cache test RED without saying so (R-01, Major); with one Major and seven Minors the verdict is READY, and the Minors (the `check_version=False` path, the unchanged-confirm and `kept_keys` conditions, the missing gate script, the stub-based API tests, the commit-block error routing) are worth fixing in the plan before Part 2.
