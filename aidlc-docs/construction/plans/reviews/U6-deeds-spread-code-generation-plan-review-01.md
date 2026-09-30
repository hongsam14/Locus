## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (plan) — U6 행적·전파
**Reviewed artifact:** `aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-09-30T23:53:55Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > 이월 결정 "FD R-10" (b), Step 1.3(a), Step 4.1 | 이월 결정 (b)는 `SpreadTarget.weight = w(X) × edge(X,Y)`를 "소문이 실제로 지나온 경로의 곱"이라고 적고, 이 문구를 승인된 FD에 정정으로 써 넣게 한다. 그러나 승인된 BR-U6-17과 BLM §4.2는 `w(X)`를 "원점까지의 최대 곱 경로"(`wx = reach.get(x)`, `best_path_weights`)로 정의한다. 소문은 부모가 있는 지역 X에 어떤 경로로든 먼저 닿을 수 있어(예: A→X 직접 0.3이 A→B→X 0.64보다 한 턴 빠름) 실제 경로의 곱과 최대 곱 경로는 다르다. Step 4.1은 `w(X)`를 정의하지 않아 개발자가 경로 추적을 구현할 수도, 최대 곱을 쓸 수도 있다. 테스트 TP-U6-1(b)·EX-6도 둘을 가르지 못한다. 틀린 문구가 승인 산출물에 들어간다. | 이월 결정 (b)와 Step 1.3(a)의 문구를 BR-U6-17과 맞춘다. `w(X)`는 `best_path_weights(origin)[X]`(통행 가능한 양방향 연결)이고 기록 가중치는 `best[X] × edge(X,Y)`이며 `best[Y]` 이하라고 적는다. Step 4.1에 `w(X)`의 출처를 한 줄로 명시하고, X가 비최적 경로로 닿은 경우를 TP-U6-1 또는 예제 하나로 고정한다. | New |
| R-02 | Major | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 6.7, Step 6.8 (EX-2, NFR-3 구조 단언, R-01·R-04) ; locus/play/wiring.py:54-65 ; tests/play/helpers.py:33-59 | 6.7은 "`GmNarrator`(LLM이 있을 때)"라고만 쓴다. 현재 `assemble_play`는 `shared.llm`만 본다(`dialogue_llm`만 별도 주입 가능). 그런데 `compose_play`는 `SharedContainer(... llm=None)`로 조립하므로, 6.8의 서술 `structured` 정확히 1회, 준비 실패 → 차단, 예산 0/1 예제, `uow_depth == 0` 단언은 서술 LLM을 주입할 길이 없다. `assemble_play`·`compose_play` 시그니처 변경이 "바뀌는 내부 계약"과 6.7의 호출처 목록에 없다. `appraise`가 `dialogue_llm`을 쓰는지도 적혀 있지 않다. 계획만으로는 6.8 테스트를 쓸 수 없다. | 6.7에 서술·판단 LLM의 출처를 정한다(`narrator_llm` 키워드를 `assemble_play`·`compose_play`에 더하거나, `dialogue_llm` 하나로 서술·판단·대화를 모두 공급한다고 적는다). `assemble_play`/`compose_play` 시그니처와 이를 부르는 테스트 호출처(`test_dialogue_api.py:79`, `play_fixtures.py:96` 등)가 키워드 선택 인자로 그대로 도는지 적는다. | New |
| R-03 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 6.1 (`_start` 호출처) ; tests/play/test_player_mode.py:443 | "호출처 전수" 원칙이라고 했는데 `_start(session_id, action, lang)`의 호출처가 빠졌다. `tests/play/test_player_mode.py:443`은 `turns._start(session.id, MoveAction(to_region_id="b"))`를 직접 부른다. `lang`에 기본값이 없으면 깨진다. `advance`(advancer.py:126)·`begin`(:145)의 내부 호출 둘도 적혀 있지 않다. | `_start`의 `lang`은 키워드 기본 None으로 두고, 호출처(advancer 내부 둘, test_player_mode.py:443)를 6.1에 적는다. | New |
| R-04 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > 이월 결정 "U5 리뷰 C4", Step 4.3 ; locus/play/npc/dialogue.py:201-208, locus/play/player/movement.py:106-109, locus/play/turn/advancer.py:227-235 | C4를 "닫는다"고 했으나 플랜은 `npcs_here`·`find_npc` 두 헬퍼만 다룬다. U5 리뷰 C4의 처방은 문서화된 상태 코드(알 수 없는 NPC: start/say 404, EndTalk 400; 다른 지역: 400, BR-U5-28)를 각자 유지하고 advancer의 죽은 폴백을 지우며 `PlayService.params`와 중복 `_require_player`를 정리하는 것이다. 지금 `_require_npc_here`는 `snapshot.npcs`(전역)로 404/400을 가르고 `validate_action`은 `npcs_by_region`으로 400만 낸다. 플랜은 상태 코드 보존을 말하지 않아 세 곳을 한 헬퍼로 바꾸는 중에 U4·U5 계약이 조용히 바뀔 수 있다. | 4.3에 "각 호출처의 상태 코드(404/400)는 그대로"를 못 박고, 회귀 테스트(기존 U4·U5 상태 코드 테스트)가 4.3 끝에 GREEN임을 적는다. `params`·`_require_player`·죽은 폴백은 이번에 하는지 넘기는지 이월 표에 명시한다(넘기면 C4는 부분 종결). | New |
| R-05 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 5.4, Step 5.2 vs domain-entities.md §7 이탈 13 | 5.4는 `appraise(session_id, npc_id, *, budget, deeds: DeedService)`로, 5.2는 `narrate(..., player_name)`로 적었다. 승인된 이탈 13은 `appraise(session_id, npc_id, *, budget)`와 `narrate(*, declaration, scene, lang)`다. 5.4의 `deeds` 인자는 같은 절의 `NpcDialogueService.__init__(deeds=…)` 주입과 중복이다. 이 차이는 Step 1.3 정정 목록(a)~(f)에도 없다. | 생성자 주입 하나로 통일하고(`appraise`의 `deeds` 인자 삭제), `player_name`은 `SceneBrief`에 넣거나 Step 1.3/10.3의 "생성 중 정한 것"으로 기록한다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 1.2 ; locus/play/gm/__init__.py | 1.2는 `locus/play/gm/{__init__,narrator}.py`를 새 파일로 적는다. `locus/play/gm/__init__.py`는 이미 추적되는 빈 파일이다(`git ls-files`). `web/src/features/gm/` 디렉터리는 없으니 새로 만든다고 적은 것은 맞다. | `gm/__init__.py`는 기존 파일(빈 채 그대로 사용)로 고쳐 적는다. | New |
| R-07 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 6 (6.1~6.6 / 6.8) | 엔진 변경 6.1~6.6(시그니처, `_prepare`, `_fail`, `_one_turn`, `RumorService.seed/spread`, `EventService`)에는 자기 테스트가 없고 모두 6.8에서 한꺼번에 검증된다. "각 단계는 그 단계의 테스트가 GREEN"이라는 실행 원칙과 "테스트는 코드와 나란히"라는 계획 원칙에 못 미친다. 또 `deeds`가 None일 때의 선언 동작(서술 없이 행적 기록 없음? `ActionResult.declaration`?)과 `narrator`만 있고 `region_knowledge`가 None일 때의 동작이 정해져 있지 않다. `_prepare`가 `_require_open` 전에 도는지도 불분명하다. | 6.4~6.5(`RumorService.seed/spread`, `reserved`)는 `test_rumor_*`에 단위 테스트를 같은 하위 단계에 두거나 6.8을 6.4/6.5 뒤로 쪼갠다. `deeds=None`·`region_knowledge=None` 조합의 동작을 한 줄로 고정하고, `_prepare` 앞에서 세션 OPEN을 재확인한다고 적는다. | New |
| R-08 | Minor | aidlc-docs/construction/plans/U6-deeds-spread-code-generation-plan.md > Step 1.1, 이월 결정 "NFR R-05" ; CLAUDE.md Status | 플랜과 NFR의 기준선은 pytest 557 · vitest 64(=621)이지만 CLAUDE.md Status는 545 + 56 = 601이다. 1.1이 실측한다고 했으므로 막히지는 않는다. 다만 6.8/10.1의 "회귀 0"과 10.3의 테스트 수 갱신이 어느 값을 기준으로 하는지 1.1 결과에 묶여 있다는 점이 적혀 있지 않다. | 1.1에서 실측한 값이 기대와 다르면 NFR-1의 기준선 문구(621)를 Step 1.3(f)의 정정 대상에 넣는다고 한 줄 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| Line refs: wiring.py:93/:97/:114, advancer.py:450, router play.py:126, __main__.py:83, test_player_mode.py:425/:582/:641/:996, test_service.py:26, test_rumor_dynamics.py:45/51/57/63/123 | 모두 일치 | 플랜이 적은 호출처 줄 번호는 정확하다 |
| grep `TurnAdvancer(` / `SessionService(` / `EventService(` / `NpcDialogueService(` | 2 / 4 / 2 / 1 구성 호출(정의 제외) 모두 플랜에 있음 | 키워드 선택 인자 방식이면 기존 호출은 그대로 돈다 |
| grep `decay_support(` | 호출 1 + 테스트 5 | 플랜과 일치. `exempt_ids` 기본값으로 회귀 없음 |
| grep `append_for_turn(` / `build_context(` / `user_prompt(` | 테스트 다수가 기본값으로 호출 | `reserved=0`, `deeds=()` 기본값이면 안전. 플랜이 줄 번호를 나열하지는 않지만 기본값이라 문제 없음 |
| grep `_start(` / `_run_turns` / `_one_turn` | test_player_mode.py:443이 `_start`를 직접 호출 | 플랜에 없음 → R-03 |
| `compose_play` / `assemble_play` LLM 주입 경로 | `llm=None`, `dialogue_llm`만 주입 가능 | 서술 LLM 주입 경로 없음 → R-02 |
| BR-U6-17 / BLM §4.2 의 `w(X)` 정의 vs 이월 결정 R-10(b) | 최대 곱 경로 vs "실제 경로" | 모순 → R-01 |
| 새 경로 존재: locus/play/deeds, rumor/spread.py, turn/quota.py, gm/narrator.py, tests, web 파일 | 새 것으로 선언됨. `gm/__init__.py`는 이미 있음, `web/src/features/gm/`는 없음 | R-06 |
| 기존 경로 존재: storage/schema.py, ports.py, memory_repo.py, postgres_repo.py, npc/{dialogue,prompts,scope}.py, turn/advancer.py, routers/{play,gm}.py, web routes/GmPage·PlayPage, api/{gm,play}.ts | 모두 존재 | OK |
| import 순환: advancer → npc.dialogue → turn.budget, turn/__init__.py | `turn/__init__.py`는 비어 있음 | 순환 없음 |
| ensure_play_schema 현황 | PG 전용 `ADD COLUMN IF NOT EXISTS active`, SQLite 건너뜀 | 플랜의 inspector 방식과 열 7개(4+3) 산술이 FD §4.3과 일치 |
| TP-U6-1~8, EX-1~19의 테스트 배정 | 전부 4.6/5.5/6.8/3.4에 배정 | 누락 없음 |
| 이월 결정 표 닫힘: R-10, R-15, R-16, R-17, N6-2, N6-4, NFR R-01~R-05, U5 C1/C4 | 단계 배정 있음. R-10(b)는 문구 오류(R-01), C4는 부분(R-04) | 나머지는 닫힘 |
| 스토리 US-4.4/4.5/5.6/6.5/8.6 → 단계 | 5.x/6.x/7.x/8.x에 대응 | 고아 스토리 없음 |

### Summary

플랜은 호출처와 줄 번호를 정확히 집었고, 단계 순서(3.3의 붉은 구간을 명시)와 이월 결정 배정도 대체로 닫혀 있다. 고쳐야 할 것은 승인 FD에 틀린 가중치 문구를 써 넣는 Step 1.3(a)(R-01)와, 6.8 테스트가 기대는 서술 LLM 주입 경로가 6.7에 없는 점(R-02)이며, 둘 다 플랜 문장 수정으로 끝난다. Major 2건은 READY 한도 이내지만 사람이 게이트에서 함께 보는 것을 권한다.
