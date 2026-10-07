## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (plan) — U3 월드 에디터
**Reviewed artifact:** aidlc-docs/construction/plans/U3-world-editor-code-generation-plan.md
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-01T09:21:38Z

### Findings
| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Critical | U3-world-editor-code-generation-plan.md > Step 4.7 | 4.7이 `WorldEditor` 제거와 모든 코드 호출처(`world/__init__.py:13·19`, `wiring.py:19·28·49·82`, `apply.py:61·82`, `routers/world.py:231-259·442·449·452-456`)를 한 하위 단계에서 닫는다. 현재 코드와 줄이 일치한다. `Editors.delete_any`가 없던 `delete_node` 자리를 채운다. 코드 쪽은 해소. 테스트 쪽 빈칸은 R-14로 올린다 | — | Resolved |
| R-02 | Major | Step 3 ↔ 4·5·6 | wiki를 3으로 앞당겨 `PriorRefView`·`fallback=`·`llm=None`이 4~6보다 먼저 선다. 의존 방향 한 줄도 있다. 5.x·6.x의 NFR-5 단언은 이제 6 안에서 실행 가능하다 | — | Resolved |
| R-03 | Major | Step 9, 이월 표 C16 | 붉은 구간(9.2~9.8)을 선언했고 단일 커밋이다. 9.1은 타입 변경이 없다. HomePage(9.7)는 BuildPanel(9.6) 뒤이고 빈 목록의 `loadDemo`·BuildPanel이 적혔다(`api/world.ts:67` 존재). C16 호출처·fixture 줄이 열거됐고 `gm.test:136·263-265·418·431·443` 등은 현재 코드와 일치한다. 남은 작은 빈칸은 R-16 | — | Resolved |
| R-04 | Major | 4.7, 6.9, 8.6, 1.2 | `test_augment_api.py`(30-32, 16, 53-54, 63-65), `test_world_api.py`(47·161-170·212·345·351), `test_augmentation.py`(175·193·226), `tests/world/editor/__init__.py`가 호출처에 들어갔다. 다만 `test_augmentation.py`의 apply·revert 호출은 빠져 있다(R-14) | — | Resolved |
| R-05 | Major | 이월 표 FD R-08·R-08a, 1.3, 6.7, 6.9 | ignore는 답으로 센다, unignore는 open·converged에서만 받고 stopped는 409(`RunFinishedError`), 검사 순서 404 → AlreadyReverted → Order → Conflict가 정해졌고 1.3 정정과 6.9 테스트에 들어갔다. TP-U3-4의 단언이 모호하지 않다 | — | Resolved |
| R-06 | Major | 6.1·6.2·6.5·6.6, 이월 표 FD R-11 | `QuestionTarget.broken_id`, `Editors`(prior_ids·get_node 포함), `apply_answer(question, answer, *, world_id, editors)`, `revert(change, *, world_id, editors)`, LLM 없는 `wiki_conflict` 빈 결과(6.4)가 명시됐다. 구현자가 추측할 곳이 없다 | — | Resolved |
| R-07 | Minor | Step 1.3, 11.3, 바뀌는 외부 계약 | BLM §7, domain-entities §4.2·4.3·4.4·6·8, BR-U3-8, `deed_voided.region_names`, U7 frontend §2.2·§4 정정이 들어갔다 | — | Resolved |
| R-08 | Minor | 이월 표 NFR R-01, 4.3, 4.5, 4.6, 3.3 | ① 새 CONTAINS → parent_id → 옛 CONTAINS, ② LOCATED_IN 삭제 → 엔티티 교체로 선별 기준이 마지막에 바뀐다. 잔여 옛 엣지는 DETACH가 지운다고 적었다. 종류별 삭제(지식·NPC·엔티티·prior)가 검색 삭제 후 404 규칙을 공유한다. TP-U3-2a 가짜의 실패 방식(한 번만, meta 쓰기 포함, 두 단언)이 정해졌다 | — | Resolved |
| R-09 | Minor | 알려진 한계 절, 8.3 | 새 세션 시작·GM 쓰기 경합이 알려진 한계로 기록되고 code-summary 이탈 목록에 넣도록 했다(12.3) | — | Resolved |
| R-10 | Minor | 이월 표 NFR R-05·R-06, 8.1, 2.2 | 경로별 한도 표(World File 두 경로 20 MiB, 나머지 48 MiB)와 테스트가 있고 `replace_nodes`의 `ConstraintError` 번역이 2.2에 있다 | — | Resolved |
| R-11 | Minor | 이월 표 C2·C4·C14·NFR R-07, 2.5 | `advancer.py:247·564·467`, `dialogue.py:154·235`, `player/service.py:61`, `region_knowledge.py:87`, `narrator.py:13`, `test_gm_events.py:9`가 현재 코드와 맞는다. `MATERIAL` 호출처도 전수다 | — | Resolved |
| R-12 | Minor | 3.2, 7.3, 1.2 | `BuildReport`(`shared/models/reports.py`), `WorldState`(`play/models.py:641`, DTO는 `api/schemas.py:382`의 별칭이라 따라옴), `RegionInspector` 하위 컴포넌트 다섯이 선언됐다 | — | Resolved |
| R-13 | Minor | 이월 표 U7 §5 문서 행, 11.3 | U7 code-summary §4·§5 8.7 정정이 11.3에 들어갔다 | — | Resolved |
| R-14 | Major | U3-world-editor-code-generation-plan.md > Step 4.7 (테스트 호출처) ↔ 6.5·6.9. 근거 `tests/world/augmentation/test_augmentation.py:107`(`_Editor` 가짜), `:137-157`(`apply_answer(answer, …, editor=editor)`, `apply_revert(…)`) | 4.7이 `apply.py:61·82`를 `editors.delete_any`·`editors.knowledge.upsert_knowledge`로 바꾼다고 하면서 테스트 호출처로 `test_augmentation.py:226`(엔진 생성)만 적는다. 같은 파일 `:107`의 `_Editor`(`delete_node`·`upsert_knowledge`만 가짐)를 `:141·153·157`의 `apply_answer`·`revert`가 그대로 넘긴다. 4.7 뒤에는 `delete_any`가 없어 `AttributeError`이고 `:226`의 `_Editor`도 같다. 6.9는 이 파일에서 `:101·155·175·193`만 고친다고 적어 `:107-157`의 가짜 교체가 어느 단계에도 없다. 4.7이 GREEN으로 끝나지 않는다. `apply_answer`의 인자 이름(`editor` → `editors`)을 4.7에서 바꾸는지도 불분명하다 | 4.7 테스트 호출처에 `test_augmentation.py:107·137-157·225-226`을 더하고, `_Editor` 가짜를 인메모리 그래프 위의 실제 `Editors`(또는 `delete_any`·`knowledge.upsert_knowledge`를 가진 가짜)로 바꾼다고 적는다. 4.7에서 `apply_answer`·`revert`가 `editors` 인자명만 먼저 바꾸고 나머지 시그니처는 6.5·6.6이라는 경계를 한 줄 적는다 | New |
| R-15 | Major | U3-world-editor-code-generation-plan.md > Step 6.7·6.9 ↔ 8.4. 근거 `api/routers/world.py:467`(`response_model=ChangeSet`), `:477`(`status_code=204`), `tests/api/test_augment_api.py` | 6.7이 서비스의 `answer`를 `AnswerResult`, `revert`를 run으로 바꾸고 6.9가 `test_augment_api.py`를 `AnswerResult`·200 + run으로 고치는데, 라우터의 `response_model=ChangeSet`·204는 8.4에서야 바뀐다. 6.9~8.4 사이에 `answer`는 응답 검증 오류(`AnswerResult` ≠ `ChangeSet`)이고 `revert`는 204라 6.9의 새 단언이 붉다. 실행 원칙("각 단계 GREEN, 붉은 구간은 단계 안에 선언")과 어긋나는데 Step 6·7에는 붉은 구간 선언이 없다. 6.7의 `run.round` 제거도 같은 라우터·`api/schemas` 경로에 걸린다 | 보강 라우터 세 개(`answer`·`revert`·`unignore`와 `POST runs`의 LLM 없는 200)의 응답 모델·상태 코드 변경을 6.9 직전 하위 단계로 당기거나(8.4에는 priors·npc-drafts만 남김), `test_augment_api.py`의 새 단언을 8.4로 미루고 6.9에 "붉은 구간 6.9~8.4"를 선언한다 | New |
| R-16 | Minor | U3-world-editor-code-generation-plan.md > Step 9.1, 이월 표 C16. 근거 `web/src/api/http.ts:20-24·36`, `deeds.test.tsx:125`, `dialogue.test.tsx:250·293`, `play.test.tsx:169` | (1) `HttpError`의 `message`·`toString()` 모양을 정하지 않았다. `DialoguePanel.tsx:55·101`, `RegionPanel.tsx:43`, `SessionBar` 등은 `String(e)`를 화면에 찍고 `includes("404")`를 쓴다. 옛 모양(`"404 Not Found: body"`)을 유지한다고 적어야 `statusOf`로 바꾸지 않은 곳이 조용히 바뀌지 않는다. (2) 거절 fixture 목록(C16)에 `deeds.test:125`, `dialogue.test:250·293`, `play.test:169`는 없다. 문자열 출력만 쓰면 무해하지만 근거가 적혀 있지 않다 | 9.1에 "`HttpError.message`는 지금 형식 `${status} ${statusText}: ${body}`를 유지한다"를 적고 위 네 fixture는 변경 없음이라고 한 줄 적는다 | New |

### Checks Run
| Check | Result |
|---|---|
| 이전 R-01~R-13 해소 대조 | Pass — 11건 Resolved, R-01·R-04는 새 빈칸(R-14)으로 이어짐 |
| 4.7 코드 호출처 줄(`wiring.py:19·28·49·82`, `__init__.py:13·19`, `apply.py:61·82`, `world.py:442·449·454`) | Pass — 현재 코드와 일치. `WorldContainer(` 생성자 호출 3곳(wiring, test_world_api:163, test_augment_api:30)이 모두 다뤄짐 |
| 4.7 테스트 호출처 | Fail — `test_augmentation.py:107·137-157`의 `_Editor` 가짜가 누락(R-14) |
| Step 3 → 4 → 5 → 6 의존 순서 | Pass — `PriorRefView`·`fallback=`·`llm=None`이 앞 단계. `WikiAdmin.list_priors` 호출처는 테스트(`test_wiki_build.py:337-338`, 길이만 보므로 무해)뿐이고 라우터 호출처 없음 |
| Step 6 → 8 라우터/서비스 계약 | Fail — 6.9와 8.4 사이 라우터 `ChangeSet`/204가 서비스·테스트와 어긋남(R-15) |
| Step 9 붉은 구간 선언 | Pass — 9.2~9.8 선언, 9.10에서 GREEN, 단일 커밋. 9.1 단독 GREEN은 R-16(HttpError 모양)만 보완 |
| 이월 표의 단계 번호(3.x/4.x/6.x/7.x/9.x/10.x) 상호 참조 | Pass — NFR·FD 행의 단계가 재번호 뒤 실제 하위 단계와 일치(예: R-01→4.3·4.8, R-03→3.1·6.3·6.4·6.7, R-07→2.5·6.3·6.4, R-08→4.7·8.2·6.9) |
| Step 1.3 정정 목록 ↔ 새 계약(unignore, AnswerResult, broken_id, nodes_after, Editors, WorldContainer.editors/catalog, RevertOrder/Conflict) | Pass — 모두 포함 |
| 줄 번호(C2·C4·C14·MATERIAL, U7 #15 `models.py:641`, `schemas.py:382`) | Pass — `narrator.py:80`·`suggest_context.py:95`의 `cap` 위치는 미확인(Minor, 코드 생성 때 grep) |
| 각 하위 단계의 GREEN | Partial — 4.7(R-14), 6.9(R-15) |

### Summary
**Verdict: READY** — Critical 0, Major 2(R-14, R-15), Minor 1(R-16). 이전 13건은 모두 Resolved.

규칙상 Major 2건은 READY 범위지만, 둘 다 "단계가 GREEN으로 닫히지 않는다"는 실행 원칙 위반이라 코드 생성 전에 문장 몇 줄로 고치기를 권한다. (1) 4.7의 테스트 호출처에 `test_augmentation.py:107·137-157`의 `_Editor` 가짜와 apply·revert 호출을 더한다. (2) 보강 라우터의 응답 모델·상태 코드 변경을 6.9 앞으로 당기거나 6.9~8.4 붉은 구간을 선언한다. (3) 9.1에 `HttpError.message` 형식 유지를 한 줄 적는다. 나머지 구조(재번호 뒤 단계 번호, 의존 방향, 붉은 구간 선언, 삭제 순서와 TP-U3-2a, 호출처 전수)는 현재 코드와 일치한다.
