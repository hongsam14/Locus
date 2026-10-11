## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (unit code plan) — V5 GM write correctness
**Reviewed artifact:** `aidlc-docs/construction/plans/V5-gm-write-correctness-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-08T06:38:23Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/V5-gm-write-correctness-code-generation-plan.md > Step 2.5 (`close_session`) vs TP-V5-14, BR-V5-14 | 2.5 puts the close inside `closing` + `short_write`, but does not say that the session is re-read inside the lock. Today `close_session` reads `current = self._require(...)` first (session_service.py:114) and writes the `session_closed` line when `current.status != CLOSED`. Two overlapping closes both read OPEN outside the lock and both write the line. TP-V5-14 requires "닫기 둘 모두 끝나고 줄 하나", so the Step 2 test would fail, or the developer must guess the fix. | State in 2.5 that the open/closed check and the "write the line once" decision use a status read taken inside the short write (or taken from `closed` returned by the store), and that the `_require` before the lock is only the 404 check. | New |
| R-02 | Major | Step 8.1 vs § 1.1 FD R-01 | § 1.1 R-01 promises that operations.md says how to find `interrupted_uncompensated` runs and what the operator then does (check player position and charge by hand). Step 8.1 lists only the worker paragraph, `GM_WRITE_WAIT_S`, line 124 and lines 273-276. The accepted finding has no step. The worker paragraph (operations.md ~l.116-120) also says a starting worker's `fail_stale_runs` marks another worker's live run failed. That function is removed in Step 7, and 8.1 does not list rewording the sentence. | Add a 8.1 item for the `interrupted_uncompensated` lookup and operator action (no new endpoint is needed; name the query or route used). Add an item to reword the `fail_stale_runs` and "turn in progress" sentences (l.113-120) to the new recovery and 409 codes. | New |
| R-03 | Minor | Steps 4.1, 5.1, 6.1, 6.2 ("guard와 tuning을 받는다(wiring)") | The plan does not say whether the new `guard` and `tuning` constructor parameters are required or default. Direct constructions exist: `EventService` 2, `RumorService` 4, `DeedService` 2, `DistortionService` 1, `SeedService` 1 (grep of locus, api and tests). `SessionService` and `TurnAdvancer` already default to a private `TurnGuard()`. A required parameter breaks those callers' commits; a private default silently gives overlap tests a different guard from the one under test. | Say which one it is. Suggested: default `None` for `tuning`; default private `TurnGuard()` for `guard` (the existing precedent), and overlap tests build through `assemble_play` or pass the shared guard. List the direct-construction sites per step. | New |
| R-04 | Minor | Step 2.8 / Step 5.2 vs TP-V5-15, TP-V5-4 | TP-V5-15 has two halves. The "GM 생성 중 월드 교체, 생성은 409 `session_closed`" half needs `generate_rumors` (Step 5), but 2.8 assigns the whole of TP-V5-15 to Step 2. 5.2 mentions world replace only under TP-V5-4. | Split TP-V5-15 explicitly: sessions_busy and lease-does-not-block in Step 2, the generation half in Step 5.2. | New |
| R-05 | Minor | Steps 4.3 and 5.2 (TP-V5-12) vs Step 3 | TP-V5-12 needs a repository whose timeline write fails inside the unit of work (for both adapters). Step 3 builds only `InterleaveGate`, `BlockingDrafts` and `threaded_repo`. The failing-timeline helper has no home. | Add a failing-timeline wrapper to Step 3.1, or say where it is defined. | New |
| R-06 | Minor | § 1.1 R-01, Step 7.1 vs BR-V5-19, domain-entities § 3, TP-V5-5 | The plan removes `fail_stale_runs`, while the approved BR-V5-19, domain-entities § 3 ("그대로 … 안전망으로 남는다") and the TP-V5-5 text keep it. The change is backed by the accepted FD review R-01, but the approved artifacts still say otherwise and code-summary § 5 (이탈) does not list it. | List this as a named deviation in 9.2 § 5 with the three artifact locations, so the next reader does not take the code for a defect. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| grep `is_running` | locus 3 files (guard, player/service.py:79, world.py:84); tests 20 (player_mode 14, turn_guard 5, play_api 1) | Matches § 1.2 R-03 and Steps 2.2/2.4/2.6 |
| grep `assert_idle` | guard 2, session_service.py:115, tests 3 (turn_guard 2, player_mode 1) | Matches; caller replaced in 2.5 in the same commit |
| grep `running_run_id` | guard 1, tests 2 (turn_guard) | Matches |
| grep `fail_stale_runs` | api/main.py:123, ports.py:112, memory_repo.py:384, postgres_repo.py 492 and 981-982, tests 3 (contract 2, postgres_repo 1) | Matches R-03 and the removal list in 7.1 (port, two adapters, lifespan, tests) |
| "turn in progress" asserts / `turn_running` asserts | 3 and 4-5 hits in tests/api and tests/play | Matches § 1.2 R-03 (Step 2.8 changes them in the same commit) |
| `PlayContainer.turns`, `.guard`, `gm.py _idle`/`hold`, `world_editor.py:128` lease | exist | Support § 1.1 R-06 and the lease/short-write split |
| Named new paths (`tests/play/{conftest,concurrency,test_guard_machine}.py`, `test_v5_*.py`, `tests/api/test_v5_busy_api.py`) | none exist; declared new | OK; 6 new test files as § 3 states |
| `any_repo` fixture in `test_repository_contract.py` | present (~l.366), SQLite in-memory | Fits the contract-test placement for `list_running_runs` (R-02 NFR) |
| Step green-ness | Step 2 changes guard methods with all callers and tests in one commit; Steps 4-6 add optional wiring only if R-03 is settled | GREEN plausible; R-03 is the open point |
| BR-V5-01..25 and TP-V5-1..15 coverage | every BR has a step; TP-V5-15 generate half and TP-V5-12 helper are the only loose ends | R-04, R-05 |
| operations.md lines 113-126, 270-278 | match the plan's line references | R-02 for the missing items |

### Summary

The plan is grounded: the call-site counts match the code, the step order keeps each commit self-contained, and the accepted FD and NFR findings are mostly settled. Two Major points remain, both cheap to fix in the plan (the stale session read in `close_session`, and the missing operations.md step for `interrupted_uncompensated`); four Minor points are clarity items. With two Major the verdict is READY, and fixing R-01 and R-02 is recommended before Part 2.
