## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (unit plan) — U7 GM 모드·안정화
**Reviewed artifact:** aidlc-docs/construction/plans/U7-gm-mode-hardening-code-generation-plan.md
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-01T02:16:09Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U7-gm-mode-hardening-code-generation-plan.md > 실행 원칙 vs Step 3.1 / 3.3 / 6.1 / 7.3, Step 6.3 / 6.5 / 6.9 | 플랜의 두 원칙("각 단계는 그 단계의 테스트가 GREEN으로 끝낸다", "시그니처를 바꾸는 하위 단계는 호출처 전부를 같은 하위 단계에서 고친다")을 플랜 스스로 어긴다. (a) 3.1이 `RegenerateResult.deleted_ids`를 `deactivated_ids`로 바꾸고 3.3이 `delete_rumor` 구현을 지우지만, 호출처 `locus/play/rumor/service.py:151`(`u.rumors.delete_rumor`)·`:166`(`deleted_ids=`), `api/routers/gm.py:158`, `tests/play/test_deed_turns.py:312`, `test_player_mode.py:940`는 6.1·7.3에서야 고친다(실측: 위 줄이 그대로 존재). 그 사이 재생성 경로와 그 테스트는 붉다. 플랜은 3.3의 "프로토콜 검사 테스트"만 붉은 구간으로 밝히고 이 구간은 밝히지 않는다. (b) 6.3이 `DistortionService` 생성자를, 6.5가 `PlayService`의 `params`를 바꾸지만 두 호출처 `locus/play/wiring.py:129/133`은 6.9에서 고친다. `compose_play`(tests/play/helpers.py)가 `assemble_play`를 거치므로 6.3~6.9 사이 거의 모든 play 테스트가 조립 단계에서 실패한다. 테스트는 6.10에서야 돌린다. | 붉은 구간을 없애거나 선언한다. 권장: `delete_rumor` 제거·`deleted_ids` 개명을 6.1(재생성 전환)·7.3(라우터)·관련 테스트와 같은 단계로 합치거나, 제거를 맨 끝(6.1 뒤)으로 옮긴다. 생성자·`params` 변경은 `wiring.py` 수정과 같은 하위 단계에 둔다. 어쩔 수 없는 붉은 구간은 3.3처럼 "어디서 붉고 어디서 다시 GREEN인지"를 적는다. | New |
| R-02 | Minor | Step 6.7 / 이월 표 U6 C5 | `appraise(session, player, npc, snapshot, *, budget)`로 바꾸는 호출처를 "`advancer._prepare`와 `test_dialogue.py`"로만 적는다. 실측: `tests/play/test_dialogue.py`에 `gm.dialogue.appraise(session.id, "n1", budget=…)` 호출이 482·506·525·528·541·544·552·554·570·573·601·626·649 열세 곳이고, `locus/play/turn/advancer.py:417`이 하나다. 테스트가 `Session`·`Player`·`NPC`·`WorldSnapshot`을 어떻게 만들어 넘길지(헬퍼 도입 여부)는 적혀 있지 않다. | 호출처 수(13+1)와 테스트 쪽 처리 방식(헬퍼 하나로 모을지)을 6.7에 적는다. | New |
| R-03 | Minor | Step 6.5 / Step 7.4 / NFR §4 C-4·C-6 | 기존 동작을 단언하는 테스트가 "의도된 변경" 목록에서 빠졌다. `tests/play/test_player_mode.py:681` `test_gm_start_session_writes_no_timeline_entry`(`list_timeline(s.id) == []`)와 `tests/api/test_play_gm_api.py:40`(GM 세션 타임라인 `== ["session_closed"]`)은 R-02(`session_started` 기록)로 반드시 깨진다. 플랜은 C-6을 "타임라인 줄 수를 세는 테스트"로만 받고 파일·줄을 적지 않는다. C-4("제안·승인 타임라인을 보는 테스트")도 마찬가지다. | 두 테스트를 6.5·7.4에 이름과 줄로 올리고 `# U7 intended change: BR-U7-11`을 단다. C-4의 해당 테스트도 찾아 적는다. | New |
| R-04 | Minor | Step 5.2 / 유닛 컨텍스트 "바뀌는 내부 계약" | "`event/dynamics` 세 함수의 키워드 인자"를 더한다고 하나 실측으로는 `propagate_delta(..., min_weight=PROPAGATE_MIN_WEIGHT)`(locus/play/event/dynamics.py:37)와 `evolve_support(..., reinforce=SUPPORT_REINFORCE)`(:85)에 이미 해당 인자가 있다. 새로 필요한 것은 `distortion_delta(m, *, max_delta)` 하나이고, 나머지는 `advancer.py:886/887/645`가 tuning 값을 넘기는 일이다. 호출처는 맞지만 변경 범위를 과장해 개발자가 시그니처를 중복 추가할 수 있다. | 5.2를 실제 변경(`distortion_delta`만 신규 인자, 나머지는 호출부 배선)으로 고쳐 적는다. | New |
| R-05 | Minor | Step 5.4 / 이월 표 "U6 #1 남은 결정" | `_scene`에 "`build_context(…, rumors, lineage)`의 facts·rumors"를 쓰라고 한다. 실측: `build_context`(locus/play/npc/scope.py:92)는 `npc`·`recent`·`limits`가 필수이고 `NpcContext`를 돌려주므로 장면 조립(`advancer.py:465` `_scene`: `pick_facts`/`pick_rumors`)에 그대로 쓸 수 없다. 필요한 것은 `shadowed_sources(picked_rumors, [*src.rumors, *src.lineage])`와 `pick_facts(..., hidden=)`다. 개발자가 추측해야 한다. | 어느 함수를 어떻게 부르는지(`pick_rumors` → `shadowed_sources` → `pick_facts(hidden=)`, `src.lineage` 사용)를 5.4에 적는다. | New |
| R-06 | Minor | Step 1.2 vs Step 4.5 | `locus/play/event/suggest_context.py`가 4.5에서 처음 나오지만 1.2의 "새 파일" 목록에 없다. 새 경로는 새것이라고 선언해야 한다. | 1.2 목록에 더한다(또는 4.5에 "새 파일"을 명시). | New |
| R-07 | Minor | 이월 표 NFR R-01 vs Step 6.2 "이름으로 지역 찾기" | 프롬프트의 지역 이름을 60자로 자르면서, 제안 결과는 LLM이 돌려준 지역 "이름"으로 지역을 되찾는다. 60자를 넘는 이름은 프롬프트에 잘린 채 나가므로 LLM이 잘린 이름을 돌려주면 매칭이 실패한다. 어떤 폴백(접두 일치·id 병기·무시)인지 플랜이 말하지 않는다. | 잘린 이름 처리 규칙을 6.2에 적고 4.7 테스트에 한 사례(61자 이름)를 더한다. | New |

### Checks Run

| Check | Command / method | Result |
|---|---|---|
| 기존 경로 존재 | `ls` locus/shared/config, locus/play/{rumor,event,player}, tests/shared, web/src/{features/gm,ui,api,routes} | 존재 확인(tuning.py, settings.py, feedback.py, event/dynamics.py, tests/shared/snapshots.py::StaticSnapshots, web/src/SessionPanel.tsx 518줄 등) |
| 새 경로가 아직 없음 | `ls tests/play tests/api web/src/__tests__` | test_feedback/test_player_log/test_world_state/test_gm_events/test_gm_mode_api/gm.test.tsx 없음(새 파일 맞음). `strategies.py`는 이미 있음(플랜도 "넓힌다") |
| `delete_rumor` 호출처 | grep | ports.py:56, memory_repo.py:228, postgres_repo.py:236/828, service.py:151, test_repository_contract.py:82, test_postgres_repo.py:97 — 플랜 목록과 일치 |
| `apply_feedback` 호출처 | grep | advancer.py:642, test_player_mode.py:358 — 일치 |
| `PlayService(params)` 호출처 | grep | wiring.py:133, test_player_mode.py:643/1024 — 일치 |
| `AppraisalOutcome` 호출처 | grep | dialogue.py:183/261, test_deeds.py:252/278, test_dialogue.py:514(`out.summary`) — 일치. deeds/service.py는 `summary`·`npc_id`를 쓰지 않음 |
| `deleted_ids` 호출처 | grep | service.py:166, models.py:494, gm.py:158, test_models.py:225/228, test_deed_turns.py:312, test_player_mode.py:940 — 일치. R-01 |
| `appraise` 호출처 | grep | test_dialogue.py 13곳 + advancer.py:417 — 플랜은 수를 적지 않음. R-02 |
| `compute_weight`/`Deduplicator` 호출처 | grep | builder.py:117, test_topology.py:34/39/47, ontology/builder.py:122, test_ontology.py:120/127 — 일치 |
| `high_support_threshold` 0.6 → 0.45 | grep | tuning.py:33, settings.py:65-66, test_rumor_dynamics.py:39 — 일치. 다른 0.6 하드코딩 테스트(:102/:140)는 인자를 직접 넘겨 영향 없음 |
| 이벤트 dynamics 인자 | read event/dynamics.py | `min_weight`·`reinforce`는 이미 있음. R-04 |
| `_scene`/`build_context` | read advancer.py:465, scope.py:92 | 시그니처 불일치. R-05 |
| GM 시작 타임라인 단언 | grep tests | test_player_mode.py:681, test_play_gm_api.py:40이 옛 동작을 단언. R-03 |
| ID 해소 | grep BR-U7-1/4/8/12/20/25/27, EX-1~15, TP-U7-1~8, nfr C-1~C-8, domain-entities §5·§6.3, frontend-components §3·§6, US-5.1~5.5·8.2·8.4·8.5 | 모두 해소됨 |
| 21,000자 계산 | 30×500+5×300+5×700+1,000 | 21,000, 플랜 값과 일치 |
| 스토리 추적 | 스토리 추적 표 vs unit-of-work U7 완료 기준(US-5.1~5.5, 8.2, 8.4, 8.5) | 누락 스토리 없음 |
| `feedback_share` 읽기 경로 | domain-entities §6.1 vs ports.py:66 | `list_region_distortions`가 몫을 싣는다(FD 6.1). 플랜 3.2는 `set`의 키워드만 적지만 모델(3.1)·어댑터(3.3)가 이를 받는다. 막힘 없음 |

### Summary

Grounding은 대체로 정확하다. 이월 결정 표는 FD R-01~R-09, NFR R-01~R-07, U6 #5~#15·C1~C16을 단계에 하나씩 매기고, 대부분의 호출처 줄 번호가 실측과 맞는다(`delete_rumor`, `apply_feedback`, `PlayService(params)`, `AppraisalOutcome`, `compute_weight`, `Deduplicator`). 새 파일은 실제로 없고 ID는 모두 해소된다. 21,000자 계산도 맞다.

막는 문제는 하나다(R-01). 플랜이 정한 "단계 끝 GREEN"·"호출처는 같은 하위 단계"를 3.1·3.3(→6.1·7.3)과 6.3·6.5(→6.9)가 어긴다. 개발자는 이 순서대로 가면 여러 단계 동안 붉은 트리에서 일하게 된다. 단계 순서를 바꾸거나 붉은 구간을 선언하면 닫힌다. Major가 1개라 판정은 READY다. 나머지 Minor 여섯은 호출처 수 누락(R-02), 깨질 테스트 누락(R-03), 변경 범위 과장(R-04), 잘못 가리킨 함수(R-05), 새 파일 선언 누락(R-06), 이름 자르기와 이름 매칭의 충돌(R-07)이며 모두 코드 생성 전에 문장 몇 줄로 고칠 수 있다.
