# U3 월드 에디터 — Code Review 01

**원하시는 것**: 세계관 자료로 월드를 만들고, 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG. U3는 그 월드를 사람이 다듬는 화면을 맡는다.
- 지도에서 지역·연결을 고치고, 지역마다 지식·스코프·NPC를 편집하며, 지역을 정리해서 지운다(US-2.2~2.5).
- 보강 Q&A로 빈틈과 끊긴 참조를 메우고 되돌리며, wiki 근거를 본다(US-2.6·2.8).
- 자료로 빌드하고, World File로 저장·불러오며, `/`에서 월드를 고르고 세션을 시작한다(US-2.1·6.2~6.4).

**이 리뷰가 하는 것**: 승인된 U3 코드(`git diff 9228861..bc1bd3a`, 커밋 12개, 코드 104파일 +6044/−1197, 테스트 28파일 +3810/−252)가 그 편집 경험과 승인된 규칙(BR-U3-*)을 실제로 지키는지 버그 위주로 확인한다. 코드는 고치지 않았다(리뷰 전용).

**대상**: `locus/shared/storage/{base,neo4j_repo,opensearch_repo}.py`, `locus/shared/{text.py, models/reports.py, config/*}`, `locus/world/{editor/*, refs.py, npc_drafts.py, build.py, wiring.py, wiki/*, augmentation/*, topology/weights.py}`, `locus/play/**`(U7 이월), `api/{uploads,main,errors,schemas}.py`·`routers/{world,world_editor,play}.py`, `web/src/**`(`features/editor/*`, `routes/{EditorPage,HomePage,GmPage,PlayPage}.tsx`, `MapOverlay.tsx`, `api/*`, `i18n.ts`, GM·플레이 이월), 테스트. 바뀐 파일과 같은 함수 안의 손대지 않은 줄도 함께 봤다.
설계 기준: `functional-design/*`, `nfr/nfr-light.md`, `plans/U3-world-editor-code-generation-plan.md`(〔실행 메모〕 포함), `code/code-summary.md`(§6 이탈·알려진 한계), `operations/operations.md`의 "World editor".
**방법**: `/code-review` max(재현율 우선).
- 탐색 각도 15개를 병렬로 돌렸다.
  - 줄 단위 여섯: 저장소·편집·wiki / 보강 / API / play 이월 / 웹 에디터 / 웹 GM·플레이 이월
  - 제거된 동작, 호출처 추적, 언어 함정, 래퍼·어댑터
  - 재사용, 단순화, 효율, 고도(altitude), CLAUDE.md 규약
  - 이 세션도 직접 후보를 찾았다.
- 후보를 중복 제거한 뒤 검증자 16명이 후보마다 CONFIRMED / PLAUSIBLE / REFUTED를 따로 판정했다. 큰 후보는 검증자 하나가 맡고, 작은 후보와 정리 후보는 검증자 하나가 4~12건을 맡았다. 승인된 설계가 고른 동작은 결함에서 빼고 설계 메모로 옮겼다(§4·§5).
- 마지막에 새 검토자 1명이 목록에 없는 틈만 찾았다(sweep). sweep이 찾은 5건은 §3에 있고, 그중 넷은 이 세션이 다시 돌려 확인했다.
- 재현 스크립트·vitest는 모두 세션 scratchpad에만 두었다. 저장소에는 이 기록 파일만 더했다. 다만 테스트를 돌리면서 git이 무시하는 `.hypothesis/`(반례 DB)와 `.coverage`가 바뀌었다. 그 반례 때문에 지금 이 사본의 `pytest`가 1 failed다(#7). 반례는 진짜 flaky를 가리키므로 지우지 않았다.
- 리뷰 중 작업 트리에 병행 세션의 U8 FD 작업(`aidlc-state.md`·`audit.md` 수정, U8 FD 플랜 파일)이 있었다. 범위 밖이다. 코드는 bc1bd3a와 같다(HEAD 9abd773은 문서만 바꿨다).

## 1. 지적 (상한 15, 심각도 순)
판정: C = CONFIRMED(입력·결과로 재현), P = PLAUSIBLE(기제는 실재, 발생 조건이 타이밍·설정에 달림). 괄호 안은 그 지적을 독립적으로 찾은 탐색 각도 수다. "검증 중 발견"은 검증자가 다른 후보를 보다가 찾은 것이다. 15건 모두 C다.

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `web/src/features/editor/RegionInspector.tsx:57-62·149-150`, `RegionForm.tsx:71-72`, `routes/EditorPage.tsx:70-76·140` | 인스펙터는 지역을 고를 때(`[worldId, regionId, lang]`)와 자기 쓰기 뒤에만 지역 보기를 읽는다. 지도 끌기(`move`), World File 불러오기, 다시 빌드는 페이지의 export만 다시 읽는다. 그런데 RegionForm 저장은 `{...view.region, name, level, parent_id, description}`를 보내는 교체 쓰기(BR-U3-1)라서 낡은 보기의 `position`·`attributes`가 저장된 값을 덮는다. 그래서 지역을 끌어 놓고 설명을 고쳐 저장하면 끈 위치가 조용히 되돌아간다. 같은 id로 World File을 불러온 뒤 저장하면 불러오기 전 필드(`attributes.terrain_kind` 포함)를 다시 쓰고, 다시 빌드한 뒤(새 id) 낡은 최상위 지역을 저장하면 지운 지역이 되살아나 같은 이름이 둘이 된다. FC §2.3은 지도 쓰기 뒤의 다시 읽기를 정하지 않았다 | C (5각도) | **medium** | 인스펙터에 `reloadKey={rev}`를 주거나 `onChanged`·`move` 뒤 다시 읽는다. 근본은 교체 쓰기에 낙관적 동시성(본문의 `updated_at`, 다르면 409)을 두거나, 끌기를 위치만 바꾸는 쓰기로 하는 것이다. 끌기 → 폼 저장 vitest를 더한다 |
| 2 | `web/src/routes/EditorPage.tsx:81·126-127·149-151`, `features/editor/AugmentPanel.tsx:25`, `api/world.ts:158` | 보강 run이 AugmentPanel의 지역 상태에만 있고, 패널은 보강 탭일 때만 마운트된다. 탭을 바꾸거나, 늘 보이는 지도에서 지역·연결을 누르거나(끌기를 마치는 클릭 포함), 새 지역을 만들면 `setTab("region")`으로 패널이 내려가 run과 되돌리기 목록이 사라진다. run id를 어디에도 두지 않고 `api.getRun`은 부르는 곳이 없어서, 그 run의 답을 화면에서 되돌릴 길이 없다. 질문이 가리키는 지역을 지도에서 눌러 보는 것이 자연스러운 흐름이라 자주 생긴다. BR-U3-26·B2("화면은 run을 유지한다"), FC §2.5와 어긋난다. code-summary §6의 알려진 한계는 서버 재시작만 다룬다 | C (4각도 + 이 세션) | **medium** | run id를 EditorPage(또는 월드별 sessionStorage)에 두고, 패널이 다시 마운트되면 `GET runs/{id}`로 읽는다(404면 "lost"). 또는 패널을 늘 마운트하고 숨긴다. 지도 클릭 뒤 돌아오는 vitest를 더한다 |
| 3 | `api/routers/world_editor.py:154-162`, `locus/world/editor/connections.py:22-31·33-50·63-69` | `previous_kind`가 있으면 라우트가 `change_connection_kind`(가중치·근거·prior·출처를 옮긴 새 쌍을 먼저 쓰고 옛 쌍을 지움)를 부른 뒤 `upsert_connection(본문)`을 또 부른다. 뒤의 호출이 방금 쓴 쌍을 지우고 본문으로 다시 쓰므로 BR-U3-11·BLM §1.4·`ConnectionSave` docstring의 "옮긴다"가 지켜지지 않는다. (a) code-summary §8의 운영자 확인 본문(근거·prior 없음)을 aldermoor에 보내면 blocked→route가 되면서 rationale·`wiki_prior_ref`가 null, 출처가 input/designer가 되고 prior 인용이 1→0이 된다. (b) 웹은 근거·prior를 다시 보내지만 `ConnectionView`에 출처가 없어 늘 PROV를 보내므로 출처가 바뀐다. (c) 둘째 단계는 지운 뒤 쓰므로 그 사이 저장소 오류면 연결이 통째로 사라지고, 같은 PUT을 다시 보내면 404다. (d) 종류 바꾸기 한 번이 포트 호출 17번(중간에 월드 전체 다시 읽기)이다. NFR-3 ②는 "종류 바꾸기도 delete 1 + upsert 1"이다 | C (7각도 + 이 세션) | **medium** | `previous_kind`면 옮긴 쌍만 쓰고(본문의 weight는 받아도 됨) 뒤의 `upsert_connection`을 뺀다. API 테스트로 근거·prior·출처가 남는지 본다 |
| 4 | `locus/world/augmentation/apply.py:81-87·64-77·185-188` | 연결이 대상인 답(dangling `wiki_prior_ref` 고침·지움)은 `_watched`가 노드를 돌려주지 않아 `nodes_before`·`nodes_after`가 비고, 되돌리기의 run 밖 편집 검사는 `nodes_after`만 돈다. 그래서 그 뒤 연결을 다른 곳에서 고쳐도 되돌리기가 200으로 옛 쌍을 다시 쓴다. 가중치·근거 편집은 조용히 사라지고, 그사이 지운 연결은 끊긴 prior와 함께 되살아나며, 종류를 바꿨으면 옛 종류 쌍이 새 쌍 옆에 하나 더 생긴다(route를 blocked로 막았다면 지나갈 수 있는 route가 되살아난다). 지도 연결 도구는 탭을 바꾸지 않으므로 한 탭에서도 생긴다. 스코프만 바뀌는 unscoped/edit도 같은 빈틈이다(피해는 작다). BR-U3-27과 `apply.py` 머리말("after checking nobody edited the target since")에 어긋난다. 이 경로(84-85·173-175)는 어느 테스트도 돌지 않는다 | C (4각도 + 이 세션) | **medium** | 기록한 뒤 상태 전체를 검사한다. `edges_added`가 같은 속성으로 아직 있고 `edges_removed`의 identity가 아직 없을 때만 되돌린다(`_edges` 키를 그대로 쓴다). 연결 대상 되돌리기 + run 밖 편집 테스트를 더한다 |
| 5 | `web/src/features/editor/ConnectionList.tsx:39-45` | 가중치 칸은 blur 때 `const w = Number(e.target.value)`로 저장한다. 칸을 비우거나(다시 치려고) number 입력이 못 읽는 값("abc")을 넣고 나가면 `Number("") === 0`이 `w >= 0` 검사를 지나 두 방향 모두 가중치 0으로 저장된다. 가중치 0이면 이동이 막히고(`movement.py:27` `edge.weight > 0.0`), 행적 전파·전해 들음·사건 전파도 그 연결에서 멈춘다. 열린 세션에도 바로 적용되고 경고는 없다. 1.5는 조용히 무시되고, 거절된 저장은 친 값을 칸에 남긴다 | C (3각도 + 이 세션) | **medium** | 빈 문자열·NaN·범위 밖은 저장하지 않고 원래 값으로 되돌린다. controlled input이나 `ui/Range`를 쓴다. vitest를 더한다 |
| 6 | `web/src/routes/HomePage.tsx:93-97·107`, `features/editor/BuildPanel.tsx:52·99` | `/`의 [자료로 만들기]는 월드가 있어도 보이는데 BuildPanel을 `exists={false}`로 연다. BuildPanel은 늘 `replace=true`를 보내고 "교체할까요?"는 `exists`일 때만 묻는다. 그래서 목록에 있는 id(예: aldermoor)를 치고 만들면 묻지 않고 그 월드를 교체한다(열린 세션이 있을 때만 세션 닫기 확인이 나온다). 성공하면 바로 에디터로 가서 리포트의 "교체함·백업" 줄도 보이지 않는다. BR-U3-35("같은 world_id가 있으면 교체 확인")와 어긋난다. 서버는 `replace=false`면 409 "world already exists"를 주는데 화면이 이것을 쓰지 않는다. 백업 파일은 남는다(운영자가 CLI로 되살림) | C (3각도 + 이 세션) | **medium** | HomePage가 목록으로 `exists`를 구해 넘기거나, 처음에는 `replace=false`로 보내 409면 교체 확인을 묻는다. vitest를 더한다 |
| 7 | `tests/world/augmentation/test_augmentation.py:184-244` (TP-U3-5) | 생성기가 연결의 `wiki_prior_ref`를 방향마다 따로 뽑아(:205-208) 한 쌍의 두 방향이 gone-1·gone-2를 따로 가질 수 있다. 신탁은 방향마다 세고, 탐지기는 설계대로 쌍마다 이슈 하나를 낸다(`detectors.py:136-149`). `max_examples=25`에 시드 고정이 없어 시드 20개 중 1개꼴로 실패하는 flaky 테스트다. 리뷰 중 한 테스트 실행이 반례를 git이 무시하는 `.hypothesis/examples`에 저장했다. 그래서 이 작업 사본에서는 이제 `pytest`가 매번 1 failed(849 passed)이고, CI라면 가끔 깨진다. CLAUDE.md의 "974 GREEN"도 이 사본에서는 맞지 않는다 | C (검증 중 발견 + 이 세션 재실행) | low–medium | 생성기가 쌍의 두 방향에 같은 ref를 주거나(쌍 불변식), 신탁을 쌍 단위로 센다. 고친 뒤 저장된 반례가 통과하는지 본다. `.hypothesis`를 지워 감추지 않는다 |
| 8 | `locus/world/augmentation/engine.py:86-103`, `questions.py:103-111`, `service.py` `_refresh`, `tests/world/augmentation/test_augmentation.py:650` | 다시 탐지할 때마다(답·되돌리기·unignore, 아무것도 쓰지 않는 ignore 포함) 아직 판정하지 않은 쌍 20개와 아직 다듬지 않은 질문 5개를 run 잠금 안에서 차례로 부른다. A-4 규모(지식 300, 지형 마을 12)에서는 시작 25 → ignore 한 번 +25 → 다음 +10으로 예산 60이 두 동작 만에 다 쓰이고, 그 뒤 고친 지식은 다시 판정되지 않는다. 같은 스냅샷에서 ignore+unignore가 +35, 새 run에서 지식 하나를 고치면 +25다. NFR-5의 확인 항목("같은 스냅샷에서 다시 탐지 → LLM 0회", "지식 하나를 고친 뒤 → 판정 ≤ 1회"), BR-U3-41("바뀐 지식만 다시 본다"), R-03 예산 근거("답마다 1회꼴")와 어긋난다. 테스트는 탐지를 5번 미리 돌려(warm-up) 이 비용을 감춘다. LLM이 호출당 1초면 답 한 번이 25초쯤 걸린다 | C (1각도) | low–medium | 정해야 한다. (a) 다시 탐지는 바뀐 쌍만 판정하고 따라잡기는 시작 때만 하거나, 바뀐 쌍 몫으로 예산을 남긴다. (b) 따라잡기를 남기면 NFR-5 확인과 R-03 근거를 고친다. 판정 호출은 서로 독립이라 작은 스레드 풀로 묶을 수 있다 |
| 9 | `locus/world/augmentation/engine.py:98-99` | 예산이 다 되면 `if not take(): break`가 처음 만나는 미판정 쌍에서 루프를 끝낸다(바로 위의 JUDGE_MAX는 `continue`다). 쌍은 지식 id 순이라 그 뒤 지식의 캐시된 충돌 판정이 더는 이슈가 되지 않는다. 미판정 쌍은 판정한 지식의 진술을 고치거나(충돌을 고치는 자연스러운 방법) 지형 지역에 지식을 더하면 생긴다. 그러면 run이 남은 충돌을 두고 "converged"가 되고 다음 답은 409다. A-4 규모에서 gap/add 한 번으로 캐시된 충돌 1~14개가 사라졌다(80번 중 8번). nfr §6-3("예산이 다 되면 wiki_conflict는 빈 결과")에도, BR-U3-41("결과는 run 안에 보관")에도 맞지 않는 부분 손실이다. #8 때문에 예산이 일찍 바닥나 자주 닿는다 | C (3각도 + 이 세션) | low–medium | `break`를 `continue`로 바꾼다(예산이 다 된 `take()`는 비용이 없다). 예산 소진 뒤 편집해도 캐시된 충돌이 남는지 보는 테스트를 더한다 |
| 10 | `locus/play/distortion_service.py:63-73` | Q6=A의 GM 설정이 ACTIVE 사건을 UoW 밖에서 읽고(:65) UoW 안에서 행 전체를 다시 쓴다(:73, PG `update_event`는 status·resolved_turn·contributions를 모두 쓴다). U7 #2 이후 GM 쓰기끼리는 리스를 나눠 쥐므로, 같은 세션의 "왜곡도 설정"과 "사건 해소"가 겹치면 해소된 사건이 ACTIVE로 되살아난다(타임라인에는 `event_resolved`가 있다). 남은 다른 지역의 기여는 다음 턴에 다시 적용되고, 다시 해소하면 그 지역이 기준 아래로 내려간다(b 0.30 → 0.06). 설정 둘이 겹치면 BR-U3-38이 비우라고 한 기여가 남는다. 실제 `PostgresPlayRepository`(SQLite)에서 동시에 200번 돌리면 101번 되살아났다. 해소 쪽의 같은 읽기-수정-쓰기는 U4부터 있었다 | C (2각도) | low–medium | 사건 읽기를 UoW 안으로 옮기고, PG에서는 `SELECT … FOR UPDATE`나 조건부 UPDATE(`WHERE status='active'`, contributions만)로 쓴다. 아니면 짧은 결정적 GM 쓰기(설정·해소)를 세션 단위 잠금으로 줄 세운다 |
| 11 | `locus/play/turn/advancer.py:219·223·236·249`, `api/routers/world_editor.py:112-141` | 턴 `_start`는 월드 스냅샷을 가드를 잡기 전에 읽는다(:219). 가드를 잡은 뒤(:223)에는 세션·플레이어만 다시 읽고, 이동은 그 낡은 스냅샷으로 검증·적용한다(:236·:249). 지역 삭제는 열린 세션의 GM 리스를 삭제하는 동안만 쥔다. 그래서 읽기와 acquire 사이에 삭제가 끝나면 이동이 통과해 플레이어가 지워진 지역에 선다. 그 뒤 `/region`과 모든 행동이 404 "player region no longer exists"라 그 세션은 화면에서 되살릴 수 없다. 라우트 docstring·BR-U3-16·BLM §2("그 사이 이동이 끼지 않는다")와 어긋나고, §6 알려진 한계(새 세션·GM 쓰기)와도 다른 경우다. 창은 ms 단위다 | C (3각도) | low–medium | `_start`가 acquire 뒤에 스냅샷을 읽는다(U6 #8의 세션 다시 읽기와 같은 꼴). 삭제는 리스를 놓기 전에 캐시를 무효화하므로 이것으로 닫힌다 |
| 12 | `api/routers/world.py:448·475`, `locus/world/editor/entities.py:20-21`, `web/src/features/editor/AugmentPanel.tsx:52` | 답을 적용하다 난 `LookupError`는 모두 404가 되고, 패널은 모든 404를 "보강 기록이 사라졌어요(서버 재시작)"로 보고 살아 있는 run의 질문·바뀐 것·되돌리기를 숨긴다. 서버의 이유 문장은 보이지 않는다. 계기는 셋이다. (i) 질문 대상이 그사이 지워짐 (ii) gap 지역이 지워짐 (iii) 신뢰도 < 0.5이면서 `located_in`이 끊긴 엔티티. (iii)은 확인·고침이 `update_entity`의 위치 재검사에서 "region not found: gone"(404)이 되어, 위치를 먼저 고치기 전에는 그 엔티티를 확인할 수 없다(US-2.6 넷째 기준). FC §2.5·§6은 "run을 다시 읽다가 404"일 때만 안내하게 했다 | C (5각도) | low–medium | 패널은 404면 `GET runs/{id}`로 run이 정말 없는지 확인하고, 있으면 서버 문장을 오류로 보인다. 엔티티 확인·고침은 위치를 바꾸지 않을 때 위치 재검사를 건너뛴다 |
| 13 | `locus/world/editor/npcs.py:24-39`, `connections.py:57-69` (`set_prior_ref`) | `EditorWrites` docstring의 "끊겨도 같은 요청을 다시 보내면 끝난다"(BLM §1.1, NFR R-01)가 지역 삭제 밖에서는 지켜지지 않는 쓰기가 둘 있다. (a) NPC 집 옮기기는 재시도 판단 기준인 노드의 `home_region_id`를 먼저 바꾸고 LIVES_IN을 나중에 쓴다. 그 사이 끊기면 재시도는 할 일이 없다고 보고 200을 주지만, 로더는 LIVES_IN을 따르므로 NPC는 옛 지역에 남는다(에디터·플레이·옛 지역 삭제 계획 모두). 나중에 다른 곳으로 옮기면 LIVES_IN이 둘이 되어 집이 엣지 순서에 따라 갈린다. 탐지기는 NPC 집을 보지 않는다. (b) `set_prior_ref`(dangling prior 답)는 쌍을 지운 뒤 다시 쓴다. 그 사이 끊기면 연결(가중치·근거)이 통째로 사라진다. 답이 예외로 끝나 ChangeSet도 없고, 다시 답하면 404이며, 새 run은 묻지도 않는다. 둘 다 그 자리에서 저장소 오류가 나야 하고, (a)는 API로만 집을 바꿀 수 있다(웹 폼에 집 칸이 없다). 지역 부모·엔티티 위치도 같은 꼴이지만, CONTAINS·LOCATED_IN 엣지를 읽는 곳이 없어 보이는 피해는 없다 | C (4각도) | low–medium | (a) 새 LIVES_IN → 노드 → 옛 LIVES_IN 순서로 쓰거나, 옛 값을 LIVES_IN에서 읽는다. (b) 새 쌍을 먼저 쓰고 옛 쌍을 지운다(같은 키라 교체 쓰기 `SET r = props`가 필요하다). 끊기 테스트(TP-U3-2a 방식)를 두 경로로 넓힌다 |
| 14 | `web/src/features/editor/BuildPanel.tsx:37·42·44·48·89-90` | 훅이 `if (!open) return null` 앞에 있어서, 패널을 닫으면 비제어 파일 입력만 내려가고 `files` 상태는 남는다. 다시 열면 파일 칸은 비어 보이는데 [만들기]가 켜져 있고, 메모만 쳐서 만들어도 숨은 옛 지도 이미지·컨셉 아트가 함께 올라간다. 에디터에서는 교체 확인 뒤 월드가 교체되고, 옛 이미지에 VLM 호출이 나간다. 부모(EditorPage·HomePage)는 패널에 key를 주지 않는다. 옛 리포트도 다시 열 때 그대로 보인다 | C (2각도) | low–medium | 닫을 때 파일·리포트 상태를 비우거나, 부모가 열 때마다 `key`를 바꾼다 |
| 15 | `web/src/routes/EditorPage.tsx:83-85`, `features/editor/MapCanvas.tsx:116-126` | 지도 [연결 긋기]로 같은 종류의 연결이 이미 있는 두 지역을 이으면, 폼이 "새 연결"(기본 route/0.60)로 열리고 경고 없이 저장된다. 서버 저장은 같은 키의 쌍을 교체하므로(BR-U3-10, 승인된 동작) 기존 연결의 근거·`wiki_prior_ref`·출처가 사라지고 가중치가 폼 값으로 바뀐다(prior 인용 1→0). MapCanvas는 `connections`를 보지 않는다 | C (2각도) | low–medium | 같은 쌍·종류가 있으면 폼을 그 값으로 채워 "고치기"로 열거나 경고한다. 저장 본문에 기존 근거·prior를 싣는다 |


### 지적별 재현 상황
1. **낡은 인스펙터의 교체 저장**: 실제 EditorPage를 그리고 api 모듈만 서버 상태를 들고 PUT을 교체 쓰기로 받는 가짜로 바꿨다. Riverton(0.2, 0.3)을 고르고 지도에서 끌면 PUT#1이 `{"x":0.5,"y":0.5}`를 저장하고 표식이 옮겨진다. 이때 `getEditorRegion` 호출 수는 1 그대로다. 설명을 고쳐 저장하면 PUT#2 본문이 `position {"x":0.2,"y":0.3}`이고 표식이 제자리로 튄다. 실제 앱(TestClient)에서도 저장된 위치가 0.2, 0.3으로 돌아간다. World File을 같은 id로 불러온 뒤에는 지도 이름표가 "Riverton Prime"인데 인스펙터는 "Riverton"이고, 단계만 바꿔 저장하면 불러오기 전 `name`·`attributes`·`position`을 다시 쓴다. 다시 빌드한 뒤 낡은 최상위 지역을 저장하면 200이고 "Aldermoor"가 둘이 된다(자식 지역은 부모가 없어 404). 탭을 바꿨다 오면 인스펙터가 다시 마운트되어 맞는 값을 보낸다.
2. **보강 run 잃음**: 실제 EditorPage·AugmentPanel(api만 mock)에서 빈틈 찾기 → gap/add 답 → `{"changes":1,"reverts":1}`. 지도에서 지역 표식을 누르면 지역 탭으로 바뀌고 패널이 사라진다. 보강 탭으로 돌아오면 `{"questions":0,"changes":0,"reverts":0,"getRun":0}`로 [빈틈 찾기]만 남는다. 새로 찾으면 run2라서 run1의 변경 c1은 화면에서 되돌릴 수 없다. 연결 선 클릭, wiki 탭 왕복, 10px 끌기 뒤 클릭도 같다. 답 뒤 페이지 다시 읽기(`onChanged`)로는 잃지 않는다.
3. **종류 바꾸기 PUT**: 패키지 aldermoor를 `POST …/demo/aldermoor`로 불러온 실제 앱에 code-summary §8 본문을 그대로 보냈다. 전: blocked ×2, 0.2, "The Spine Mountains block the pass most of the year.", `prior-mountain-barrier`, inferred/demo-author(note·refs 포함). 후(200): route ×2, 0.6, rationale null, prior null, input/designer, note·refs 없음. `GET prior-refs`에서 그 prior를 인용하는 연결이 1 → 0. `change_connection_kind`만 부르면 모두 남는다. 웹 본문은 `{"kind":"route","weight":0.2,"rationale":"…","wiki_prior_ref":"prior-mountain-barrier","provenance":{"source":"input","generated_by":"designer"},"previous_kind":"blocked"}`이라 출처만 바뀐다. 쓰기 순서는 `[upsert_edges, delete_edges, meta, delete_edges, upsert_edges, meta]`이고, 넷째 쓰기에서 끊으면 500에 엣지 0개, 같은 PUT을 다시 보내면 404 "connection not found … (blocked)"다. 일반 저장은 같은 자리에서 끊겨도 다시 보내면 200으로 되살아난다. 캐시가 찬 상태에서 일반 저장은 포트 호출 5번, 이 PUT은 17번(find_nodes 10, get_edges 1 포함)이다. 근거·prior·출처를 보는 API 테스트는 없고, `test_editors.py`의 종류 바꾸기 테스트는 라우트를 거치지 않는다.
4. **연결 대상 되돌리기**: 끊긴 `wiki_prior_ref`(gone-prior)를 가진 Riverton–Hollow route 0.5에 dangling 질문을 답한다(edit → prior P, `nodes_after: []`). 그 뒤 바깥에서 (A) 지도 연결 도구로 같은 쌍을 0.9로 다시 저장 (B) 가중치 0.95·근거 "paved now"로 저장 (C) 종류를 river로 바꿈 (D) 연결을 지움. 네 경우 모두 되돌리기가 200이다. (A)(B)는 0.5·"old road"·gone-prior로 돌아가고, (C)는 river 쌍 옆에 gone-prior를 가진 route 쌍이 되살아나 엣지 4개, (D)는 지운 연결이 gone-prior와 함께 돌아온다. 대조로 엔티티 `located_in`을 바깥에서 고치면 409이고 아무것도 쓰지 않는다. 실제 라우터로도 같다(답 200, `PUT /connections` 200, 되돌리기 200). 커버리지에서 `apply.py` 84-85·173-175(연결 대상)와 117(unscoped 고침)·165-168(parent_id 고침)을 도는 테스트가 없다. 무작위 TP-U3-4 생성기는 유효한 `wiki_prior_ref`만 뽑는다.
5. **가중치 빈칸**: 실제 ConnectionList에서 칸을 비우고 blur하면 `{"kind":"route","weight":0,"rationale":"old road","wiki_prior_ref":"p1",…}`가 나간다. "abc"도 jsdom과 HTML 규칙대로 `value=""`라서 0이 저장된다. "1.5"는 저장 0번이고 칸에 1.5가 남는다. 실제 PUT 뒤 `cache.get`으로 보면 가중치가 두 방향 모두 0.0이다. 이동 선택지가 `('Hollow', True, None, 2)`에서 `('Hollow', False, 'blocked pass', 0)`으로, 전파 엣지가 4 → 0, 전해 들음 도달이 0.6 → 없음이 된다.
6. **`/`에서 교체**: 실제 HomePage에서 목록에 aldermoor가 있을 때 [자료로 만들기] 버튼이 1개 보인다. id에 aldermoor, 메모를 넣고 만들면 `uploadBuild(aldermoor) replace=true confirm=false`가 바로 나가고 교체 대화는 0번 보인 뒤 `/editor/aldermoor`로 간다. 대조로 에디터에서는 "같은 id의 월드가 있습니다. 교체할까요?"가 먼저 뜬다. 실제 라우트와 WorldBuilder로 보면 `replace=false`는 409 "world already exists", `replace=true`는 200 `replaced=True backup_path=…`이고 지역 R0~R2가 R0 하나로 바뀐다.
7. **flaky TP-U3-5**: 리뷰를 시작할 때 전체 `pytest`는 850 passed였다. 리뷰 도중 한 실행이 반례를 찾아 `.hypothesis/examples`에 저장했고(20:20경), 그 뒤로 `pytest -q --no-cov`는 1 failed, 849 passed다. 반례는 지역 둘 사이 blocked 쌍의 두 방향이 `gone-1`·`gone-2`를 따로 가리키는 경우다. 탐지기는 `[(…|blocked, 'wiki_prior_ref', 'gone-1')]` 하나를 내고 신탁은 gone-1·gone-2 둘을 기대한다. 반례 DB가 없을 때 시드 20개 중 1개에서 실패했다. 탐지기의 쌍 단위 이슈는 설계대로라 고칠 곳은 테스트다.
8. **다시 탐지의 따라잡기**: 지식 303개(지형 마을 12)에서 실제 서비스(예산 60, 답 30)로 시작 +25(판정 20, 다듬기 5), ignore #1(쓰지 않음, 같은 스냅샷) +25, ignore #2 +10으로 60을 다 썼고 그 뒤로는 +0이다(고친 지식을 다시 판정하지 않는다). ignore #1은 10ms 가짜 LLM으로 261ms, 즉 잠금 안에서 차례로 25번 왕복했다. 새 run에서 지식 하나를 고치면 +25다. 테스트 자기 월드에서도 warm-up 없이 같은 스냅샷 두 번째 탐지가 +1이다(+6, +1, +0).
9. **예산 소진 뒤 충돌 손실**: 강 마을의 k000·k001이 충돌이고 지식 70개다. 기본 예산으로 gap/add 세 번이면 45 → 60(소진)이고 그때까지도 `wiki_conflicts=['k000','k001']`이다. 패널에서 k000의 진술만 고치면 `status=converged, wiki_conflicts=[]`인데 `state.verdicts[('k001',…,'river')]`는 여전히 충돌이다. 다음 답은 `RunFinishedError`(409)다. uuid id인 A-4 규모에서는 충돌 6개 중 셋째를 고치면 그 뒤 셋이 사라졌다.
10. **GM 설정과 해소의 겹침**: 실제 HTTP 라우트(동기 `def`, 스레드풀)에서 두 요청이 GM 리스를 동시에 쥔다(`[('AnyIO worker thread', 2, 'gm')]`). 창을 넓히는 sleep 하나만 넣고, 기여는 실제 턴이 만든 a:0.3·b:0.24다. 설정 a=0.5 ∥ 해소 E → 둘 다 200, 타임라인에 `event_resolved`가 있는데 E는 `active`, `{'b': 0.24}`다. 다음 턴에 다시 적용되어 a=0.8이고, 다시 해소하면 b=0.06(기준 0.30)이다. 설정 a ∥ 설정 b=0.45 → `{b:0.24}`가 남아 해소하면 b=0.21(EX-12 기대는 0.45)이다. 끼워 넣기 없이 Barrier로 동시에 200번 돌리면(SQLite 위 `PostgresPlayRepository`) ok 8, status=active 101, GM 값 유실 86, 기준 아래 5다. 인메모리 저장소는 200/200 ok라 오프라인 테스트로는 보이지 않는다.
11. **삭제 리스와 낡은 스냅샷**: 실제 스레드와 실제 `POST /act`·`DELETE /regions/{id}`, 실제 TurnGuard·WorldCache로 돌렸다. 턴 스레드를 `_start`의 스냅샷 읽기 직후에만 세웠다. 결과는 `DELETE town 200` → `POST /act 202` → run DONE → `player.region_id == 지운 town` → `GET /region 404 'player region no longer exists'` → 되돌아가는 이동·기다리기 모두 404다. 대조로 acquire 뒤에 세우면 DELETE가 409 "turn in progress"다. 캐시가 찬 `/act`에서는 창이 ms 단위라 드물다.
12. **404 → "lost"**: 실제 앱에서 신뢰도 0.2·`located_in="gone"`인 엔티티의 low_confidence 질문에 확인·고침을 보내면 둘 다 404 `region not found: gone`이다. 그동안 `GET run`은 200 open이고 기록도 남아 있으며, 앞 답 되돌리기도 200이다. 에디터에서 지식을 지운 뒤 그 질문에 답하면 404 `knowledge not found`, 지역을 지운 뒤 gap/add면 404 `region not found`다. 진짜 없는 run도 같은 404다. 실제 AugmentPanel에 이 404를 주면 "(서버 재시작)" 안내가 뜨고, 오류 줄은 비며, 질문·바뀐 것·되돌리기가 모두 0이고, `getRun`은 불리지 않는다.
13. **재시도가 끝내지 못하는 쓰기**: `tests/world/editor/helpers.py`의 Meter로 n번째 쓰기를 한 번 끊고 같은 호출을 다시 했다. NPC A→B는 LIVES_IN upsert에서 끊으면 재시도가 `['replace_nodes','index','upsert_nodes']`만 쓰고 끝난다. 노드는 B, LIVES_IN은 A이고, 스냅샷·에디터 보기·플레이 `npcs_here`·A의 삭제 계획·내보내기가 모두 A다. 그 뒤 C로 옮기면 LIVES_IN이 A·C 둘이고, 읽기 순서를 40번 섞으면 A 16번·C 24번이다. A로 읽힌 순서에서 A를 지우면 NPC도 지워진다. `set_prior_ref`는 upsert에서 끊으면 엣지 0개가 되고, 보강 답(remove·edit)으로 가면 500에 run 기록 0, 다시 답하면 404, 새 run은 묻지 않는다(가중치 0.3·근거 "mountain pass" 소실).
14. **BuildPanel의 남은 파일**: 실제 부모(EditorPage의 `file-build`, HomePage의 `home-build`)로 열고 [닫기]로 닫았다. 다시 열면 이미지 칸 파일 0개, 메모 "", [만들기] 켜짐이다. 메모만 쳐서 교체 확인 뒤 만들면 `images sent = ['old-map.png']`다. 빌드 성공 뒤 닫았다 열어 지도 JSON만 고르면 `concept_arts sent = ['concept-v1.png']`이고 옛 리포트가 그대로 보인다. HomePage의 빈 목록에서도 같다.
15. **연결 도구 덮어쓰기**: 실제 EditorPage → MapCanvas → ConnectionForm에서 기존 route 쌍(0.35, 근거·prior 있음)이 지도에 선 2개로 그려져 있다. 연결 도구로 Hollow → Riverton을 누르면 "새 연결: Hollow – Riverton" 폼이 기본 route/0.60으로 경고 없이 열린다. 저장 본문은 `{"kind":"route","weight":0.6,"provenance":{"source":"input","generated_by":"designer"}}`(근거·prior·`previous_kind` 없음)다. 서버에 남는 것은 `{'weight': 0.6, 'prov_source': 'input', 'prov_generated_by': 'designer'}`이고 prior 인용은 1 → 0이다. 반대 순서로 눌러도 같은 키다.

## 2. 상한 아래 — 정리(cleanup) 지적
모두 검증 CONFIRMED다. C1·C2는 low–medium, 나머지는 low다. 정확성 지적이 우선이라 상한 밖에 두었다.

| # | 위치 | 지적 | 권장 조치 |
|---|---|---|---|
| C1 | `web/src/routes/EditorPage.tsx:39-49·57-68·70-76` | 모든 쓰기 뒤 `reload()`가 월드 전체 export(데모 규모 271 KB, 지도가 쓰는 것은 12%)와 `/worlds`(월드마다 `find_nodes` 2회 + 세션 목록 전체)를 다시 받는다. 끌기 하나도 그렇다(U3 이전에는 지역 상태만 고치고 PUT 한 번이었다). 쓰기가 캐시를 비웠으므로 export는 월드를 처음부터 다시 읽고, `rev`가 바뀌어 열린 스코프 없음·wiki 탭도 다시 읽는다. `/worlds`는 열린 세션 수 하나를 읽으려고 부른다 | 끌기는 PUT만 하고, `listWorlds`는 마운트와 불러오기·빌드 뒤에만 부른다. 스코프 없음 수는 서버가 준다 |
| C2 | `web/src/features/editor/AugmentPanel.tsx:8·38-43·83-88·117-127`, `locus/world/augmentation/{apply.py:84·173, questions.py:66, service.py:75}` | 웹이 서버의 이슈 규칙을 다시 적었다. 이슈 종류는 `issue_key.split(":")[0]`으로 얻고, `_REF_KIND`(필드 → 대상 라벨)와 종류별 입력 규칙을 옮겨 적었다. 연결 대상 id `a\|b\|kind`는 한 곳에서 만들고 세 곳에서 다르게 푼다. 보이는 증상은 둘이다. 웹 gap/add로 더한 지식이 "바뀐 것"에 uuid로 보인다(`name=answer.title or nid`, 웹은 title을 보내지 않는다). 지역 id에 `\|`가 있으면(API·World File) 연결 대상 답이 400 "too many values to unpack"이고 이름도 틀린다 | 질문에 `type`과 필요한 입력(`needs`)을 싣고, 대상에 문자열 대신 `ConnectionKey`를 싣는다. 바뀐 것의 이름은 저장된 `k.title`로 짓는다 |
| C3 | `locus/world/editor/{knowledge.py:118-128, npcs.py:41-51, entities.py:36-44}`, `locus/world/wiki/admin.py:39-57·72-95` | "있나? → 노드 삭제 → 검색 문서 삭제 → LookupError"가 네 번 쓰였고 이미 갈라졌다. 에디터 셋은 404여도 `writing()`을 돌아 WorldMeta를 고치고 캐시를 비우며(다음 읽기는 전체 다시 읽기, 홈의 "마지막 수정"이 edit로 바뀜), prior 삭제는 노드가 있을 때만 그렇다. WikiAdmin은 EditorWrites의 노드 읽기·`written()`·스냅샷 읽기를 다시 구현했다 | `EditorWrites.delete_held(world_id, id, label)` 하나를 넷이 쓰고, WikiAdmin은 EditorWrites를 받아 쓴다 |
| C4 | `locus/world/editor/bundle.py:51-73`, `locus/world/augmentation/{apply.py:123-151·281-288, types.py:42}` | `Editors.prior_ids`는 부르는 곳이 없다(엔진은 집합을 직접 만든다). `delete_any`는 Knowledge·Entity만 닿고 NPC·Region·else 갈래는 죽은 코드다. Region 갈래는 리스도 `protected`도 없이 `delete_region`을 부르므로, 지역 대상 REMOVE가 생기는 날 BR-U3-16을 건너뛴다. TargetKind `"npc"`는 만들어지지 않아 `_doc`의 NPC 갈래와 `augment.target.npc` i18n도 닿지 않는다. `_confirm_or_edit`의 엔티티·지식 갈래는 거의 같은 복사본이고, 노드 읽기 길이 `apply.py` 한 파일에 셋이다 | `prior_ids`·`get_node`를 지우고, `delete_any`를 `{knowledge, entity}` 표로 좁히고, `"npc"`를 뺀다 |
| C5 | `locus/world/editor/knowledge.py:130-135`, `augmentation/detectors.py:158-171`, `web/src/routes/EditorPage.tsx:88-89` | "스코프 없음" 규칙(BR-U3-14)을 세 곳이 다시 계산한다. 로더가 이미 `WorldSnapshot.unscoped_knowledge_ids`로 준다. 무작위 편집 40번에서 셋 모두 같았지만, 규칙을 바꾸면 탭 배지·목록·질문이 갈라진다 | 백엔드 두 곳은 스냅샷 값을 읽고, export에 그 필드를 실어 웹도 쓴다 |
| C6 | `locus/world/npc_drafts.py:72-73·111-120`, `editor/regions.py:158-178`, `augmentation/apply.py:165-167` | `_path`는 `" > ".join(level_path(r, s)[:-1])`와 같다(2,000개 무작위 트리에서 차이 없음). `regions._connection_edges`는 같은 패키지의 `connections.edge_keys`와 출력이 같다. `require_region`을 두 곳이 손으로 다시 쓴다 | 기존 함수를 부른다 |
| C7 | `api/routers/world.py:69·264`, `locus/__main__.py:95·237-252`, `api/routers/world_editor.py:46-49·296-299`, `locus/play/session_service.py:136-137` | U3가 `SessionService.open_sessions()`를 더했는데, 같은 `str(s.status) == "open"` 필터가 world.py 두 곳(264는 U3가 고친 함수)과 CLI에 남았다. CLI `world list`는 `WorldCatalog`와 같은 반복을 따로 돈다. `_editors`·`_wiki`는 world.py의 `_need`와 같다. 또 `SessionStatus`는 plain `(str, Enum)`이라 `str()` 비교는 두 저장소가 문자열 "open"을 넣을 때만 맞는다(멤버면 "SessionStatus.OPEN"이고, 그러면 지역 삭제가 리스도 보호도 없이 돈다). U7 #13이 사건에서 고친 꼴이다 | 모두 `open_sessions()`를 쓰고 그 안을 `SessionStatus(s.status) is SessionStatus.OPEN`으로 비교한다. CLI는 `WorldCatalog`를 쓰고, `_need`는 `api/deps.py`로 옮긴다 |
| C8 | `web/src/features/editor/{BuildPanel.tsx:38·51-66·104-115, WorldFileBar.tsx:31·62-77·104-118}`, `MapCanvas.tsx:142` | "교체 → 열린 세션 N개 닫기" 두 단계 확인(상태·409 해석·Modal)이 두 컴포넌트에 글자까지 같게 있다. 둘 다 N을 `/"open_sessions":\s*(\d+)/.exec(String(e))`로 꺼내는데, U3가 더한 `HttpError.body`는 아무도 읽지 않는다. 이름이 `RegionForm`인 컴포넌트가 둘이다(지도의 새 지역 폼과 인스펙터의 편집 폼) | `http.ts`에 `openSessionsOf(err)`(body 파싱)와 `useReplaceConfirm` 훅을 두고, 지도 쪽 폼은 `NewRegionForm`으로 바꾼다 |
| C9 | `locus/world/wiki/admin.py:64-70`, `api/routers/world_editor.py:312` | `GET /prior-refs` 한 번이 `prior_refs()`·`broken_refs()`를 차례로 불러 그래프에서 prior를 두 번(`find_nodes` WorldMeta·WikiPrior 각 2회) 읽고 인용 맵을 두 번 만든다. 스냅샷의 `kg.priors`가 이미 같은 목록이다 | 스냅샷 한 번으로 usages·broken을 함께 만드는 `WikiAdmin.refs(world_id)` 하나로 바꾼다 |
| C10 | `locus/world/augmentation/apply.py:60·75·244-257` | 답마다 `_edges`가 월드의 모든 엣지를 두 번 읽고 주시 id에 닿은 것만 남긴다(데모 규모 1,224개 중 지식 4개·마을 54개). Neo4j 쿼리는 라벨이 없어 색인을 못 쓴다 | 주시 id로 거른 엣지 읽기 하나(`WHERE a.id IN $ids OR b.id IN $ids`)로 바꾼다 |
| C11 | `locus/world/editor/writes.py:66-77` | 편집 쓰기가 글이 그대로여도 다시 임베딩·색인한다(신뢰도만 바꾼 확인, repoint, NPC 집·엔티티 위치 옮기기). 지식·NPC·엔티티 문서를 검색하는 곳은 없다(nfr §2). 다시 색인 자체는 BR-U3-2가 요구한다 | 옛 노드를 이미 읽으므로, 문서 글이 같으면 임베딩을 건너뛴다 |
| C12 | `web/src/features/editor/UnscopedPanel.tsx:35-38·45-46` | 지정·삭제 한 번에 목록을 두 번 읽는다(`run`의 `load()`, 그 뒤 `onChanged` → `reloadKey` 효과의 `load()`) | `run`에서 `load()`를 빼고 `reloadKey`에 맡긴다 |
| C13 | `api/schemas.py:57-66·414-421`, `locus/world/{editor/models.py:70-76, npc_drafts.py:48, augmentation/types.py:78-81}` | `WorldInfo`는 `WorldSummary`의 필드 여섯을 다시 선언하고, `EditorRegionViewOut`은 `EditorRegionView`의 필드를 다시 선언한 plain BaseModel이다. 둘 다 `**model_dump()`로 만들어서, 도메인 모델에 필드가 늘면 응답에서 조용히 빠진다. 아무도 읽지 않는 필드도 있다(`NpcDraftResult.llm_calls`, `QuestionTarget.region_id`·`broken_id`) | `class WorldInfo(WorldSummary)`, `class EditorRegionViewOut(EditorRegionView)`로 상속한다 |
| C14 | `web/src/i18n.ts` | 어디서도 쓰지 않는 키가 21개다. U3가 더하고 안 쓴 8개(`home.newWorldId`, `editor.{connection,knowledge,npc}.delete`, `editor.saved`, `wiki.{condition,effect,domains}`), U3가 Toolbar·옛 AugmentPanel·옛 EditorPage를 지워 고아가 된 12개(`toolbar.*`, `editor.{enterWorldId,working,noWorld,emptyWorld,replace*}`, `augment.{start,none}`), U3 이전부터의 `deed.appraisals` 하나다. `augment.target.npc`는 닿지 않는다. 머리말은 "~150 keys"인데 지금 315개다 | 두 사전에서 지운다. wiki 라벨 셋은 FC §4 키 표에 있으니 패널이 쓰는 것도 방법이다 |
| C15 | `api/routers/world.py:195-225` | `build_world_upload`가 모든 파일을 읽고 확인하고 base64로 바꾼 뒤에야 열린 세션 409를 낸다(이미지 6개·42 MiB에 약 290ms). 화면의 409 → 확인 → 재전송 흐름은 FC §2.7대로다 | 개수 검사 바로 뒤에 열린 세션을 확인한다 |
| C16 | `locus/play/event/service.py:85·99·127-150·197-229`, `play/base.py:61-62`, `play/turn/advancer.py:570·716·912` | U7 리뷰 C4의 "서비스 호출마다 스냅샷을 한 번 읽고 이름을 UoW 전에 한 번 구한다"가 일부만 들어갔다. `resolve_event`는 PG 트랜잭션 안에서 스냅샷을 두 번 읽고(운영의 WorldCache는 그때마다 Neo4j로 버전을 확인), `create_event`는 2번, `suggest_events`는 2+n번 읽는다. 엔진은 턴마다 이름표를 여러 번 만든다 | create는 `require_region`이 돌려준 지역의 이름을, resolve는 트랜잭션 전에 이름을 한 번 구한다. `names`를 넘겨 쓴다 |
| C17 | `web/src/features/editor/KnowledgeList.tsx:111` | 제목을 비운 지식 추가에서 클라이언트가 `statement.trim().slice(0, 60)`으로 제목을 만든다. 서버의 `fallback_title`(공백 접기, 단어 경계, "…")과 다른 둘째 규칙이라 같은 진술이 인스펙터와 보강에서 다른 제목을 얻는다(줄바꿈이 든 제목, 단어 중간 자름). 외톨이 서로게이트로 500이 되는 경우는 §3에 따로 적었다 | 클라이언트는 `title.trim()`만 보내고, 서버의 create·upsert가 빈 제목을 `fallback_title`로 채운다 |

테스트 적정성 메모(검증 없이 목록만):
- 연결 대상 dangling 답(`apply.py` 84-85·173-175), unscoped 고침(117), parent_id 고침(165-168)을 도는 테스트가 없다. TP-U3-4 생성기는 유효한 `wiki_prior_ref`만 뽑아서 이 경로에 닿지 않는다(#4).
- TP-U3-5 생성기는 연결 ref를 방향마다 뽑아 쌍 불변식을 깬다(#7).
- NFR-5 "같은 스냅샷 → LLM 0회" 테스트는 탐지를 5번 미리 돌린 뒤에 단언해 따라잡기 비용을 보지 못한다(#8).
- 종류 바꾸기 API 테스트는 상태 코드만 본다. NFR-3 ② 구조 단언은 일반 저장만 센다(#3).
- 끊기 테스트(TP-U3-2a)는 지역 삭제에만 있다. NPC 옮기기·`set_prior_ref`·종류 바꾸기 라우트는 끊어 보지 않는다(#13·#3).
- 웹 테스트에 "끌기 → 인스펙터 저장", "탭 왕복 뒤 run 유지", "가중치 칸 비우기", "`/`에서 있는 id로 빌드", "BuildPanel 닫았다 열기", "대화 중 닫힘 + readOnly"가 없다(#1·#2·#5·#6·#14, §3).
- 동시 GM 쓰기(설정 ∥ 해소)는 인메모리 저장소에서는 일어나지 않아 오프라인 테스트로 볼 수 없다(#10).
- 브라우저 동작(같은 파일 다시 고르기, 지도 밖에서 놓기)은 jsdom이 재현하지 못한다(§3).

## 3. 상한으로 뺀 정확성 지적
검증을 통과했지만 상한(15) 밖으로 밀린 정확성 지적이다. 따로 적지 않으면 심각도는 low다.

| 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|
| `web/src/routes/AppNav.tsx`(U3가 고치지 않음), `features/editor/WorldFileBar.tsx:90`, `i18n.ts:73·114` | 앱 어디에도 `/`로 가는 링크가 없다("Locus" 글자는 링크가 아니다). U3는 `/`를 월드 목록과 [세션 시작]의 자리로 만들고 에디터의 Toolbar(세션 picker 포함)를 지웠다. 그래서 열린 세션이 0이면 에디터에서는 세션을 시작하거나 고를 길이 없고, 닫힌 세션은 GM 화면이나 URL로만 열린다. `play.noSession`·`gm.noSessionHint`는 여전히 "에디터에서 시작하세요"다. AppNav의 에디터 링크 기본값 aldermoor는 기존 것이다(U8 플랜 A8-11). low–medium | C | AppNav에 `/` 링크를 두고 두 문구를 고친다. U8 플랜 Q3(원클릭)과 함께 정한다 |
| `web/src/routes/PlayPage.tsx:185-200`, `locus/play/turn/guard.py:47` | `turn_running`은 GM 쓰기가 세션을 쥐었을 때도 참인데 GM 쓰기에는 TurnRun이 없다. GM이 생성·제안 중에 플레이로 돌아오면 화면이 두 번 읽고 멈춰, 쓰기가 끝난 뒤에도 버튼이 꺼진 채 남는다(새로고침 전까지). U3의 지역 삭제 리스도 같은 창을 만든다. U4 domain-entities의 정의("진행 중인 TurnRun이 있는가")와 다르다. 9228861에서도 같다(U3 이전부터). low–medium | C | 서버가 GM 보유를 `turn_running`에서 빼고 따로 알리거나, run이 없으면 짧게 다시 읽는다 |
| `locus/world/augmentation/{apply.py:185-211, service.py:95-96}` | 되돌리기가 그래프를 되돌린 뒤 검색 색인·WorldMeta 쓰기에서 실패하면 `reverted`가 서지 않는다. 다시 보내면 복원된 노드를 run 밖 편집으로 보고 409 "edited after this change"(틀린 이유)를 계속 낸다. 그 run의 앞 변경들도 순서 409로 묶여 되돌릴 수 없다. 첫 실패는 `ConnectionError`가 `_AUG_ERRORS`에 없어 500이다. low–medium | C | 검사를 통과하면 쓰기 전에 표시를 두고, 다시 보낼 때 지금 노드가 `nodes_before`와 같으면 이미 되돌린 것으로 본다 |
| `web/src/features/play/DialoguePanel.tsx:54·71-73·83·111-113`, `routes/PlayPage.tsx:293·300` | U7 #12 수정이 띄운 "세션이 종료되었습니다"를, 그 수정이 부른 `refresh()`가 지운다. `readOnly`가 바뀌어 불러오기 효과가 다시 돌고 `setError(null)`을 하기 때문이다(35ms에 보였다가 57ms에 사라짐). 그 뒤 입력·기다리기는 이유 없이 꺼져 있다. 저장소 테스트는 패널만 띄우고 `onClosed`를 mock으로 둬 이 조합을 보지 못한다 | C | 효과가 `readOnly` 변화만으로 오류를 지우지 않게 하거나, 닫힘을 페이지 알림으로 보인다 |
| `web/src/features/editor/{RegionInspector.tsx confirmDelete, ConfirmDelete.tsx:74}`, `api/routers/world_editor.py:132-139` | 지역 삭제 409(대화가 열린 사이 플레이어가 들어옴, 또는 다른 세션의 턴)가 `Error: 409 Conflict: {"detail":{"message":…,"session_ids":[…]}}` 원문으로 보이고, `session_ids`는 읽히지 않으며 확인 버튼도 켜진 채다. FC §5는 "세션 목록과 'GM 화면에서 세션을 닫거나 플레이어를 옮기세요'"를 보이라고 했다 | C | `HttpError.body`를 파싱해 `delete.region.blocked` 문구와 세션 목록을 보이고 확인을 끈다 |
| `web/src/features/editor/AugmentPanel.tsx:70-76·117-120` | 답이 진술·지역·참조만 보낸다. 그래서 low_confidence "고치기"로는 신뢰도를 올릴 수 없어 같은 질문이 바로 다시 나오고(답 하나 소모), 제목도 바꿀 수 없다. FC §2.5와 domain-entities §4.2는 고치기·추가에 진술·제목·신뢰도 입력을 적었다. 같은 본문에 `confidence=0.8`을 넣으면 풀린다 | C | 고치기·추가 카드에 제목·신뢰도 입력을 더한다 |
| `api/routers/world.py:204-215·352-359` | U3가 "고정 문구 422"로 고친 바로 그 줄에서, 객체가 아닌 지도 JSON(`[1, 2]`·`"a"`·`42`·`null`)은 `WorldInputs` 검증이 try 밖에서 실패해 500이다. 깊은 중첩(`"["*200000`)은 `RecursionError`라 지도·World File 업로드 모두 500이다(JSON `POST /file`은 400). 부작용은 없다 | C | 지도마다 `isinstance(…, dict)`를 확인하고 except에 `RecursionError`를 더한다 |
| `web/src/i18n.ts:850-852` | "채우지 못한 `{param}`" 검사를 채운 뒤의 문장에 한다. 그래서 이름에 `{word}`가 있으면(플레이어 `{ari}`, 지역 `Old {keep}`, NPC `{the_hermit}`) 다 채운 줄이 영어 summary로 떨어지고 지역 이름(FR-D3)을 잃는다. GM 타임라인과 플레이어 로그가 같다 | C | 템플릿의 자리표시자를 params와 대조한다 |
| `locus/world/augmentation/engine.py:116-127` | wiki 조회가 한 번 실패하면(검색·임베딩 시간 초과) `[]`를 run 끝까지 캐시해 그 (지형, 지역) 쌍을 다시 판정하지 않는다. 실패한 판정은 다시 하는 것과 다르다. 그 run은 충돌을 두고 converged가 될 수 있고, 새 run에서는 찾는다 | C | 예외는 캐시하지 않는다 |
| `locus/world/editor/bundle.py:63-64`, `api/routers/world.py:466-486` | 보강 "지우기" 답과 gap/add 되돌리기가 지식을 지우면서 번역 행은 지우지 않는다. BR-U3-3은 지식을 지우는 모든 경로가 번역을 지우라고 한다. 저장 공간만 남는다(읽기는 source hash로 거른다) | C | 답·되돌리기 라우트가 지운 지식 id로 `purge_translations`를 부른다 |
| `web/src/features/editor/KnowledgeList.tsx:111` | 제목 없이 지식을 더하면 `statement.slice(0, 60)`이 UTF-16 단위로 잘라 이모지를 반으로 가를 수 있다(59~60번째 단위). 외톨이 서로게이트 제목은 Neo4j 드라이버의 UTF-8 인코딩에서 실패해 500이다(인메모리 저장소는 노드를 저장한 뒤 export가 500). 드물다 | C | C17과 같이 서버가 제목을 채운다 |
| `locus/world/editor/{knowledge.py:122-128, npcs.py:45-51, entities.py:36-44}`, `wiki/admin.py:76-90` | 종류별 삭제는 "그 라벨로 있음"만 보고, 404여도 검색 문서를 지운다. 검색 삭제는 world·id로만 거르므로 다른 종류 노드의 문서가 지워진다. `DELETE /knowledge/{prior id}`는 404인데 그 prior가 검색에서 사라져 wiki 판정과 cross-world 탐색이 못 찾는다. API를 잘못 쓸 때만 생긴다 | C | 노드가 어떤 라벨로든 있으면 검색 삭제를 건너뛴다 |
| `web/src/features/gm/GmHub.tsx:88-95` | 서버의 제안 상한을 세션마다 한 번 읽고 실패는 버린다(다시 읽지 않음). `EVENT_SUGGEST_MAX`가 기본값이 아닐 때 마운트 읽기가 실패하면 U7 #15 증상(1~5 선택, 400 원문)이 돌아온다 | C | 실패하면 다음 GM 읽기(`generateAll`의 `/state` 등)에서 상한을 고친다 |
| `web/src/features/gm/PlayerStrip.tsx:35-46`, `routes/GmPage.tsx:135-141·186` | 404가 아닌 오류에서 마지막 플레이어를 남기는데, 띠가 세션별 key가 없어 s1 → s2로 바꿀 때 `getPlayer(s2)`가 500이면 s1의 플레이어·지역이 s2의 턴과 함께 보이고 지도 표식도 s1에 남는다 | C | `key={session.id}`를 주거나 세션이 바뀌면 상태를 비운다 |
| `locus/world/augmentation/service.py:66-78` | 답을 쓰고 기록·답 수를 올린 뒤 다시 탐지가 실패하면(그래프 읽기 오류) 옛 질문이 남아, 같은 답을 다시 보내면 두 번 적용된다(같은 지식 둘). 지우기는 두 번째가 404라 패널이 run을 잃었다고 본다 | C | 다시 탐지 실패를 따로 잡아 질문 목록을 비우고 run 상태를 다시 읽게 한다 |
| `locus/world/augmentation/apply.py:59-77` | 답의 변경 기록은 주시 노드에 닿은 모든 엣지의 앞뒤 차이다. 임베딩 호출(약 1초) 사이에 지도에서 저장한 연결·위치가 그 답의 변경에 들어가고, 그 답을 되돌리면 함께 지워진다. 제작자 한 명 전제(A-4) 안이지만 한 탭에서도 된다 | P | 기록을 그 답의 쓰기로 좁힌다(편집 클래스가 바꾼 것을 돌려주게 함). 아니면 A-4 문구에 이 결과를 적는다 |
| `locus/play/turn/advancer.py:445-453`, `play/gm/narrator.py:75` | U3 7.5의 서술 try 좁히기가 효과가 없다. 호출자 `_narrate`의 try가 `narrate()` 전체를 감싸서, 프롬프트 버그가 LLM 실패로 기록되고(`llm_calls=1`, 공급자 호출 0) 차단기가 켜져 그 턴의 소문 초안이 빠진다. 지금은 계기가 없다. code-summary 7.5와 다르다 | C | 프롬프트를 try 앞에서 만들고 `self._llm` 호출만 감싼다 |
| `locus/play/rumor/spread.py:91` (`rumor/service.py:279`) | 전파·씨앗으로 태어난 지지도가 `settle`을 거치지 않는다. 지지도 0.6인 행적 소문이 가중치 0.5로 퍼지면 자식이 0.44999999999999996으로 "0.45"로 보이는데 0.45 기준의 강한 소문이 아니어서 그 지역의 되먹임 올림이 두 턴 빠진다. U7 #9 이월이 덜 끝났다 | C | 지지도를 쓰는 곳(전파·씨앗·생성)에서 `settle`하거나, 기준 비교에 허용치를 둔다 |
| `api/routers/world.py:153-171` | JSON `POST /build`에는 칸 상한이 없다(메모 500개 → LLM 500회, 메모 하나 5,000,000자). NFR-5의 "업로드 상한이 호출을 묶는다(44회)"는 multipart에서만 맞는다. 라우트는 U3가 고치지 않았고 웹은 쓰지 않는다(설계 빈틈) | C | `WorldInputs`에 개수·길이 제약을 두어 두 경로가 같은 규칙을 쓴다 |
| `api/uploads.py:27-31·45·80` | uvicorn을 root path로 띄우면 `scope["path"]`에 그것이 붙어 World File 20 MiB 한도가 48 MiB로 바뀐다(이 저장소는 root path를 쓰지 않음). 또 요청 한도와 칸 한도가 둘 다 20 MiB라, 꽉 찬 World File을 multipart로 올리면 미들웨어의 일반 413이 먼저 난다(약 174 B 여유가 필요) | C | 미들웨어가 `root_path`를 떼고 비교하고, 요청 한도에 multipart 여유를 둔다 |
| `locus/world/editor/{regions.py:36-52, knowledge.py:19-25}` | 편집 쓰기는 월드가 있는지 보지 않아, 없는 world id로 지역을 만들면 WorldMeta 없는 월드가 `/` 목록에 생긴다. 에디터의 "월드 없음" 화면에도 지역 추가 도구가 켜져 있어 URL 오타 하나로 생긴다(U3 이전 PUT도 같았다) | C | 편집 쓰기 앞에서 WorldMeta(또는 스냅샷)로 월드를 확인한다 |
| `locus/world/npc_drafts.py:27-33·96-106` | KNOWN HERE(지식 제목·진술 최대 8 × 260자)와 EXISTING NPCS가 "material, not instructions" 머리말 밖에 있고, 시스템 문장은 "Everything under REGION is material"이다. NFR-6 N3-5와 모듈 docstring에 어긋난다. `one_line`·글자 상한과 구조화 출력이 피해를 줄인다 | C | 세 절을 하나의 MATERIAL 머리말 아래에 두거나 시스템 문장이 세 절을 다 가리키게 한다 |
| `web/src/MapOverlay.tsx:86-98·138-142` | 끌기를 svg의 pointerUp으로만 끝낸다. 지도 밖에서 놓으면 끌기가 남아 버튼 없이 커서를 따라가고, 다음 클릭(연결 도구 클릭 포함)이 위치를 저장한다. U3 이전부터 있었지만 U3가 이 경로를 다시 썼고, 도구 모드가 연결 도구 변형을 더했다(r1이 r2 위에 저장됨) | C | pointerdown에서 `setPointerCapture`하고 `onPointerCancel`·`onLostPointerCapture`로 끌기를 끝낸다 |
| `web/src/features/editor/WorldFileBar.tsx:51-60·84-88` | 숨은 파일 입력을 비우지 않아, 불러오기 성공·확인 취소·실패 뒤 같은 World File을 다시 고르면 change 이벤트가 없어 아무 일도 없다(Chrome 146 CDP로 확인). 실패 뒤에는 옛 오류가 남는다 | C | 고른 뒤 `e.target.value = ""`로 비운다 |
| `web/src/features/editor/ConfirmDelete.tsx:44-66` | 지역 삭제 확인이 자식·NPC·스코프 없음이 될 지식에는 이름을 보이고, 연결·스코프만 빠질 지식·위치가 비워질 엔티티는 수만 보인다. BR-U3-9·FC §5는 여섯 모두 "수와 이름"이다. 비워질 엔티티는 에디터 어디에도 이름이 나오지 않는다 | C | 계획에 이미 이름이 있으므로 함께 보인다(연결은 `regions`로 이름을 붙인다) |
| `tests/shared/storage/fakes.py:26·66-78`, `locus/shared/storage/neo4j_repo.py:76-77·136-137·177-178` | 그래프 가짜는 노드를 (world, id)로 잡아 라벨을 보지 않고, Neo4j는 라벨마다 id 유일 제약이라 같은 id의 다른 라벨 노드를 하나 더 만든다. 편집 쓰기는 자기 라벨만 확인하므로 `PUT /knowledge/{npc id}`가 가짜에서는 NPC를 덮어쓰고 Neo4j에서는 id가 같은 노드 둘을 만든다(이후 `get_node`가 둘 중 하나). API를 잘못 쓸 때만 생긴다 | C | 편집 쓰기가 id가 다른 라벨로 있는지 보고 400을 준다. 가짜를 라벨까지 키로 잡는다 |
| `api/main.py:35-43` | 새 422 처리기도 해석할 수 없는 바이트 입력(text/plain `b"\xff\xfe…"`)은 `jsonable_encoder`의 `decode()`에서 500이다. stock FastAPI와 같아 회귀는 아니고 웹은 늘 JSON을 보낸다 | C | `_finite`가 bytes를 `errors="replace"`로 푼다 |
| `web/src/features/editor/AugmentPanel.tsx:31·69·119-126`, `locus/world/augmentation/questions.py:113` (sweep) | 패널은 카드 입력(진술·지역·참조)을 `q.id`로 잡는데, 서버는 다시 탐지할 때마다(답·무시·되돌리기·unignore) 모든 질문에 새 id를 준다. 그래서 다른 카드에 쳐 둔 진술·고른 지역이 어떤 답 뒤에든 사라진다. 그 카드로 바로 [추가]를 누르면 진술 없이 가서 400 "an added fact needs a statement"다. low–medium | C | 입력을 `issue_key`로 잡거나, 서버가 같은 이슈 키의 질문 id를 run 안에서 유지한다 |
| `locus/world/augmentation/apply.py:123-151`, `editor/knowledge.py:19-25`, `locus/knowledge/consensus.py:100` (sweep) | 지역 보기의 신뢰도는 SCOPED_TO 엣지의 값이고, 그 값은 스코프를 만들 때 지식에서 복사된다. 보강 확인·고침과 `PUT knowledge`는 노드만 바꾸므로 엣지 값이 낡는다(0.3 → 확인 0.9, 보기는 0.3). 이 값이 GM 지역 패널, NPC 사실 고르기(`pick_facts`, 상한 12), 지역 brief 상위 3, 소문 출처 신뢰도에 쓰여서, 한 지식이 지역마다 다른 신뢰도를 보일 수 있다. U3 이전부터 같았고 다시 쓴 경로에도 남았다 | C | 신뢰도를 바꾸는 쓰기가 그 지식의 DIRECT 스코프 엣지 값도 고치거나, 보기가 노드 신뢰도를 읽는다 |
| `locus/world/editor/regions.py:94-97·224` (sweep) | 부모가 끊긴 지역(`parent_id="gone"`)을 지우면 자식들이 그 끊긴 id를 새 부모로 받는다. dangling 하나가 자식 수만큼 늘고, 삭제 계획은 `new_parent_id: "gone"`을 경고 없이 보인다 | C | 지운 지역의 부모가 월드에 없으면 `new_parent_id`를 None으로 둔다 |
| `web/src/features/editor/{RegionInspector.tsx:50-62, UnscopedPanel.tsx:28-38}` (sweep) | 표시 언어가 바뀔 때마다 다시 읽는데 마지막 읽기만 그리는 장치가 없다(U5 #11의 readSeq·active 규칙). en → ko → en에서 ko 응답이 늦게 오면 영어 화면에 한국어 제목·진술이 남는다 | C | 읽기 순번을 두고 마지막 것만 그린다 |
| `locus/world/editor/knowledge.py:27-42` (sweep) | `POST …/regions/{r}/knowledge`에 있는 id를 보내면 201로 노드를 통째로 바꾸고 스코프를 하나 더 단다. 지역·NPC 만들기는 같은 경우 400 "already exists"다. 웹은 id를 보내지 않아 API에서만 생긴다 | C | 지역·NPC처럼 있는 id면 400을 준다 |


## 4. 기각
| 위치 | 지적 | 기각 이유 |
|---|---|---|
| `locus/world/editor/connections.py:33-50` | 종류 바꾸기가 새 쌍을 쓴 뒤 끊기면 재시도가 400이고 두 종류가 남는다 | 승인된 BLM §1.4·플랜 4.4 그대로다("새 쌍 먼저, 같은 쌍이 있으면 400"). 잃는 것이 없고 옛 종류를 지우면 풀린다. Neo4j가 엣지마다 따로 커밋해 반쪽 쌍이 남을 수 있는 점은 §5 설계 메모 6에 적었다 |
| `locus/world/augmentation/apply.py:117·164-175` | 남은 질문이 에디터에서 이미 고친 것을 다시 바꾼다(고친 `located_in`을 지움, 두 지역 스코프를 하나로 바꿈) | 같은 제작자의 나중 쓰기다(nfr §2, A-4 last-write-wins). 기록되고 되돌리면 고친 값이 돌아온다. 한 탭에서는 생기지 않는다(다른 탭으로 가면 #2로 run이 사라진다). 답이 전제를 다시 확인하지 않는 점은 §5 설계 메모 3 |
| `locus/play/event/suggest_context.py:117-137` | 모든 지역에서 이름을 맞춰, 보인 지역의 이름과 같은 이름이 보이지 않은 지역에 있으면 초안이 빠진다 | 승인된 플랜 :171("이름은 모든 brief에서 같은 모호성 규칙")과 docstring 그대로다. LLM이 id 대신 이름을 쓸 때만 생긴다. 보인 지역 안에서 하나뿐이면 고르는 규칙은 설계 메모 7 |
| `web/src/features/gm/GmHub.tsx:130-153` | 전체 생성이 409를 이유 없이 실패 수로만 센다 | U7 리뷰 #2의 하위 권장("runBulk가 409를 따로 알리고")이 U7 §8 처리 결과에도 U3 이월 목록에도 없다. U3는 이 줄을 `mapLimit`으로 감쌌을 뿐이고, 숫자만 보이는 요약 알림은 X3 C12의 승인된 설계다. U7 #2의 남은 항목으로 따로 정한다 |
| `locus/world/augmentation/{engine.py:90-104, apply.py:139-150}` | "맞음"으로 답해도 wiki_conflict 질문이 끝나지 않고, 빈 변경이 기록에 쌓인다 | BLM:160(confirm은 신뢰도 `max(현재, 0.9)`만), 판정 캐시 키(신뢰도를 보지 않음), BR-U3-28(ignore만 다시 묻지 않음) 그대로다. 설계 메모 2. `changed=[target]`을 빈 변경에도 싣는 작은 코드 차이는 함께 정한다 |
| `locus/world/editor/{regions.py:139-143, knowledge.py:130-135}` | 전역 지식을 에디터 어디에서도 보거나 고치거나 지울 수 없다 | domain-entities §2.3(인스펙터는 DIRECT 지식만, "합의 보기 아님"), BR-U3-14(스코프 없음은 전역이 아닌 것), FC의 네 탭, BR-U3-33(GM ✕ 없앰)이 고른 동작이다. 다만 자리를 정한 문서가 없다(설계 메모 1) |
| `locus/shared/config/settings.py:66` | `RUMOR_SUPPORT_DECAY=inf`가 기동을 지나 모든 소문이 매 턴 가지치기된다 | 2.0도 같은 결과라 NaN/Infinity의 문제가 아니라 상한(`le`)이 없는 문제다. U3 diff 밖이고 U3 이월(표 env 둘, GM 필드 셋)에도 없었다. 설계 메모 8 |
| `api/routers/world.py` (`build/upload`·`file/upload`), `features/editor/{BuildPanel,WorldFileBar}.tsx` | 열린 세션 409 뒤 화면이 같은 파일을 다시 올린다 | FC §2.7의 흐름(409 → 확인 → `confirm=true`로 다시)이다. 서버가 파일을 먼저 읽는 순서만 정리 C15 |
| `locus/world/augmentation/types.py:78-81`, `api/routers/world.py` `GET /augmentation/runs/{id}` | 받기만 하는 `AugmentationAnswer.target_id`, 쓰이지 않는 run 다시 읽기 경로 | `target_id`는 U3 이전부터 있던 호환 필드다(`extra="forbid"` 아래에서 옛 클라이언트가 422를 받지 않게 함). `GET runs/{id}`는 BLM §4.3의 "화면 새로고침용"이고 테스트가 있다. 쓰이지 않는 것은 웹의 `api.getRun`뿐이다(#2) |
| `locus/world/wiki/base.py` `_query_key` | 이름 키가 `normalize_name`(lower)이 아니라 `casefold`다 | BLM :210과 플랜 :319가 `casefold` + 공백 접기를 정했다 |
| `api/uploads.py:48`, `api/routers/world.py` `GET /file` | PNG를 8바이트가 아니라 4바이트로 보고, 내보내기에는 20 MiB 상한이 없다 | 설계가 "앞 바이트로 판별"이라 했다. 데모 규모 World File은 0.6~1.1 MiB라 20 MiB와 거리가 멀다 |
| `web/src/features/editor/AugmentPanel.tsx`·옛 Toolbar·옛 EditorPage | NFR-1의 "같은 요소의 data-testid를 남긴다"를 어겼다 | Toolbar·EditorPage의 요소는 FD가 지우거나 다시 쓰기로 정했다(§1, 플랜 9.8). `augment-action-*`·`augment-revert`는 C-3이 다시 설계한 요소다. 같은 요소에서 이름만 바뀐 것은 `augment-start-btn` → `augment-find` 하나라 정리 메모로만 남긴다. 저장소에 이 id를 쓰는 e2e는 없다 |

## 5. 문서 정확도 메모
규약 각도에서 **인용할 수 있는 CLAUDE.md 규칙 위반은 없었다**.
- 경계 import는 `test_boundaries`가 통과한다. world → play, play → localization, `locus` → `api` import가 없고, 번역 정리·지역화는 `api/schemas.py`를 거친다.
- `neo4j`·`opensearchpy`·LLM SDK·`sqlalchemy`는 어댑터와 조립 루트에서만 import한다. 새 포트 메서드는 두 어댑터와 가짜 모두에 있다.
- 새 쿼리는 모두 `world_id`로 나뉜다(Neo4j `MERGE`·`MATCH`, OpenSearch term).
- `assemble_world`와 `WorldContainer`가 `editors`·`catalog`·`npc_drafts`를 조립하고, ruff·black(100)이 clean이다. TP-U3-1~6과 2a는 모두 hypothesis 테스트다.

사실과 다른 문장은 다음과 같다.
- `CLAUDE.md:11`의 "edit a region's knowledge, scopes, NPCs and entities in an inspector"와 `web/README.md:35-36`의 "…NPCs (with LLM drafts) and entities"는 틀렸다. 인스펙터에도 API에도 엔티티 편집이 없고, BLM §1.7도 "에디터 화면에서 엔티티를 직접 편집하는 일은 없다"고 적었다. 같은 줄의 "reached from the world list at `/`"도 앱 안에서 `/`로 돌아가는 링크가 없어 반만 맞다(§3).
- `CLAUDE.md`의 "974 offline tests GREEN"과 code-summary §1의 pytest 850은 리뷰를 시작할 때는 맞았다. 지금 이 사본에서는 #7 때문에 849 passed, 1 failed다.
- `operations.md:96`("Without `OPENAI_API_KEY` … build, augmentation and wiki routes answer 503")은 U3의 World editor 절("LLM: none needed")과 코드에 어긋난다. 보강은 늘 조립되고 wiki 읽기는 LLM이 없어도 된다.
- `operations.md` World editor 절의 세 문장은 사실과 다르다.
  - "changing the kind keeps them" (#3)
  - "Deleting knowledge also deletes … its translations" — 보강 지우기는 아니다(§3)
  - "Undo … refused (409) for … a target edited outside the run since" — 연결 대상은 아니다(#4)
- code-summary §8의 운영자 확인("연결 종류 바꾸기 … 무게·근거·prior 유지")은 그 본문 그대로 보내면 근거·prior가 사라진다(#3). U8이 이 결과를 배포 문서에 싣기로 되어 있다.
- code-summary Step 7.5의 "say·판단·서술의 try 좁히기"는 서술에서는 효과가 없다(§3).
- BLM §1.4:77("종류를 바꾸는 편집은 화면이 '옛 키 삭제 + 새 키 추가'로 보낸다")은 바로 아래 R-09 문장(`previous_kind`로 한 연산)과 어긋나는 남은 문장이다.
- nfr-light §3의 "리버스 프록시 설정은 로컬 데모에 없다"와 달리, compose의 `web`은 `web/nginx.conf`로 `/api`를 프록시한다(설계 메모 9).
- U4 domain-entities는 `turn_running`을 "진행 중인 `TurnRun`이 있는가"로 적었지만, 가드는 GM 쓰기에도 참을 준다(§3).
- nfr §2 동시성의 "에디터 두 개가 같은 노드를 고치면 나중 쓰기가 이긴다"는, 보강 답의 되돌리기가 그사이 들어온 다른 쓰기까지 지우는 결과(§3)를 담지 않는다.

설계 메모(결함으로 올리지 않음):
1. **전역 지식의 자리**: 빌더는 전역 지식에 스코프를 달지 않는다. 인스펙터는 DIRECT만, 스코프 없음 목록은 전역이 아닌 것만, GM 화면은 ✕를 뺐다(C-8). 그래서 aldermoor의 전역 지식 "Sunrise"는 에디터 어디에도 나오지 않고, 보강 탐지기도 그것을 묻지 않는다. 고치려면 World File을 손으로 고치거나 API를 직접 불러야 한다. 스코프가 있는 전역 지식도 스코프를 비우면 같은 처지가 된다. 전역 탭(또는 스코프 없음 목록에 전역 절)을 둘지 정해야 한다.
2. **"맞음"이 wiki_conflict를 끝내는 방법**: 지금은 맞음이 신뢰도만 올리고 판정 캐시 키는 신뢰도를 보지 않아, 같은 질문이 계속 나오고 빈 변경이 기록에 쌓여 앞 변경의 되돌리기를 막는다. 맞음을 그 (지식, 지형) 판정의 "확인함"으로 기억할지, 맞음을 wiki_conflict 선택지에서 뺄지 정한다.
3. **답의 전제 다시 확인**: 남은 질문에 답할 때 이슈가 아직 있는지 보지 않는다. unscoped/edit는 `set_scopes`로 스코프 전체를 바꾸는데, BLM §4.2 표는 "DIRECT 스코프 하나 / edges_added"다. 둘은 질문이 낡았을 때만 다르다.
4. **되돌리기의 "run 밖 편집" 정의**: BLM §4.3은 노드만 본다("지금 노드가 nodes_after와 다르거나 added_ids 노드가 없는 경우"). 그런데 BR-U3-23은 연결의 `wiki_prior_ref`를 대상에 넣었다. #4를 고칠 때 이 정의를 엣지까지 넓힌다.
5. **보강 예산 모델**: #8을 어느 쪽으로 고칠지(따라잡기를 시작 때만 할지, 바뀐 것에 예산을 남길지, NFR-5 확인을 고칠지)가 BR-U3-41·NFR-5 문구를 정한다.
6. **종류 바꾸기의 반쪽 쌍**: Neo4j 어댑터는 엣지마다 auto-commit 쿼리 하나라서, 종류 바꾸기의 새 쌍 쓰기 도중 끊기면 새 종류 한 방향만 남는다(BR-U3-10의 쌍 불변식이 깨짐). 재시도는 400이다. `upsert_edges`를 UNWIND 하나로 묶으면 함께 풀린다(NFR R-06이 데모 규모에서 받아들인 엣지별 왕복).
7. **보인 지역 안에서 이름 맞추기**: 이름으로 온 초안은 보인 지역 안에서 하나뿐이면 그것을 고르고, 아니면 월드 전체의 모호성 규칙을 쓰는 순서가 두 목표(U7 §3, 보인 지역 우선)를 다 지킨다.
8. **조정값의 상한과 NaN·Infinity를 막는 자리**: `RUMOR_SUPPORT_DECAY`에는 `le`가 없다. NaN·Infinity는 지금 필드마다(`allow_inf_nan=False`, `FiniteFloat`) 막는데, 지역 `attributes`의 NaN은 200으로 저장되었다가 내보낼 때 null이 되고, 구조화 지도의 NaN 위치는 `clamp01(NaN)=1.0`으로 들어간다(둘 다 U3 이전부터). JSON 파서(`parse_constant`)와 `clamp01`에서 한 번에 막을지 정한다.
9. **compose web의 요청 크기**: `web/nginx.conf`에 `client_max_body_size`가 없어 nginx 기본값(1 MiB)이 걸린다(실행하지 않음, P). 그러면 compose의 web(:3000)으로는 1 MiB가 넘는 지도 이미지(상한 8 MiB)·지도 JSON(2 MiB)·World File(20 MiB)이 앱 상한에 닿기 전에 nginx HTML 413을 받는다. U3의 업로드 상한 표(nfr §1.1)가 이 경로에서는 의미가 없다. U8의 배포·데모 문서에서 정한다.
10. **409 본문의 모양**: 409 본문이 문자열(`http_error`), `{message, session_ids}`(지역 삭제), `{open_sessions…}`(교체) 세 가지다. 웹은 `String(e)`에 정규식을 걸어 가른다. `HttpError.body`를 한 번 파싱하는 도우미(정리 C8)와 예외 종류마다 고정 `code`를 두면 `conflictKind`의 영어 문장 의존(U7 #12)도 함께 풀린다.

## 6. 확인한 것
| 검사 | 값 |
|---|---|
| 전체 `pytest -q --no-cov` | 리뷰 시작 때 850 passed. TP-U3-5 반례가 `.hypothesis/examples`에 저장된 뒤로는 849 passed, 1 failed(#7) |
| `npx vitest run` | 124 passed (8 files) |
| `ruff check` / `black --check --line-length 100` (`locus api tests`) | clean (263 files unchanged) |
| `npx tsc --noEmit` | clean |
| `mypy locus api` | 11 errors(6 파일, 기준선과 같음). U3가 더한 줄에는 0이다(`neo4j_repo`·`opensearch_repo`의 4건은 손대지 않은 `connect()` 줄) |
| 경계 import·포트 | `test_boundaries` 통과. 외부 클라이언트 import는 어댑터와 조립 루트에만 있다. 새 포트 메서드는 두 어댑터와 가짜에 모두 있고, 모든 새 쿼리가 `world_id`로 나뉜다 |
| Neo4j·OpenSearch 쿼리 모양 | `replace_nodes`는 라벨마다 `UNWIND … MERGE (n:L {id, world_id}) SET n = row.props`이고 id·world_id를 props에 합친다. `delete_edges`는 (종류, identity 모양)마다 UNWIND 하나이고, 두 끝점을 모두 `world_id`로 맞추며 빈 입력이면 0이다. OpenSearch `delete`는 keyword `world_id` term + `_id` ids, `refresh=True`다. 식별자는 모두 `_safe_ident`를 거친다 |
| 지역 삭제 | ①~⑥ 순서와 단계 안의 쓰기 순서가 BR-U3-8 〔Step 1.3 정정〕과 같고, 모든 쓰기 자리에서 끊어도 끊긴 id가 없으며 재시도가 끝까지 간다(TP-U3-2a). 리스는 동기 `@contextmanager`라 `ExitStack.enter_context`가 맞다. 바쁜 세션·쓰이는 지역·없는 지역·저장소 오류의 모든 길에서 놓인다(실제 uvicorn·TestClient). 지운 지역에 ACTIVE 사건·소문이 있어도 턴·이동·해소가 계속 돈다 |
| 보강 기록·되돌리기 | 무작위 월드 400개에서 (이슈, 행동) 쌍 전부를 섞은 답 약 1,190개를 적용하고 나중 것부터 모두 되돌리면 노드·엣지·검색 문서가 처음과 같다. 목록 속성 dangling 고침·지움과 되돌리기도 왕복이 같다. 검사 순서 404 → 이미 → 순서 → run 밖 편집, run마다 `threading.Lock`(동기 라우트), 예산 60의 호출 전 검사, ignore·unignore 전이가 맞다(빠진 곳은 #4·#8·#9) |
| 업로드 | 48 MiB `Content-Length`는 라우트 전에 413이고, 청크 본문은 세다가 413이다(FastAPI 0.141이 HTTPException을 다시 던진다). 비-HTTP scope는 통과하고 `http.disconnect`도 전달한다. `build/upload`의 칸 개수·크기·메모 글자·이미지 앞 바이트 검사가 맞다 |
| wiki 근거 | 정규화 질의 중복 제거, 빌드당 40, 토폴로지 → 온톨로지 → 지식 순 저장, `증류 ∪ 생성` 참조 필터, `broken_refs`, `delete_prior`의 그래프 → 검색 순서가 설계대로다. 빌드마다 wiki 인스턴스가 새로 생겨 `created_priors`가 빌드 사이에 새지 않는다 |
| 캐시 일관성 | 에디터·플레이·WikiAdmin·빌더가 같은 `knowledge.cache` WorldCache를 쓴다. `written()`은 finally에서 WorldMeta를 병합 upsert로 고치고 무효화한다. 버전 표지(`updated_at\|last_writer`)가 그 필드다 |
| U7 이월 | Q6=A가 두 어댑터에서 EX-12·롤백대로다(겹치는 GM 쓰기는 #10). `settle`의 경계·NaN, #13·#14·#15, 잎·깊이·이름 정렬, C2·C3·C5·C6·C9·C12, C17·C18, 7.1 설정, `say`·판단 좁히기가 맞다. 웹은 #6 `refreshRef`, C1 전체 생성(승격 포함 캐노니컬 수가 옛 계산과 같음), C8 `mapLimit`, CommitRange(C15·C19·#8, Chrome 146에서 입력 밖 놓기·터치에도 pointerup), ActionBar #7, EDGE_SPACE(퍼즈 402,234개 같음, 선형), §3 `act` gen, #10·A3-14(5eb3760의 실제 페이로드), GmPage `onDeedChanged`가 맞다 |
| i18n | ko·en 키 집합이 같고, 쓰는 키와 보간 필드가 모두 있다(안 쓰는 키는 정리 C14) |
| 웹 API 계약 | 경로·메서드·쿼리·본문 필드·multipart 칸·응답 타입이 라우트·`schemas.py`와 맞는다(`extra="forbid"` 본문, `stripKo` 포함). `HttpError` 메시지 형식이 그대로라 `conflictKind`가 맞다 |
| 제거된 동작 | 옛 WorldEditor의 캐시 무효화·WorldMeta 갱신·검색 다시 색인·404, 지역 삭제의 NPC 삭제, 지식 삭제의 번역 정리, 메모 `errors="replace"`, 409 열린 세션 흐름이 새 코드에 다시 있다. 지운 함수·상수(`_neighbour_weights`, `_where`, `default_base` 등)를 부르는 곳이 남지 않았다 |

## 7. 남은 결정 (사람이 고른다)
원하시는 것: 세계관 자료로 만든 월드를 에디터에서 다듬어 플레이에 넘기고, 그 월드에서 소문과 사건이 지형을 따라 퍼지는 솔로 TRPG를 데모로 보이는 것.
지금 하는 것: 승인된 U3 코드의 리뷰를 마쳤습니다(코드는 고치지 않음). 이 질문은 찾은 결함을 지금 U3 후속으로 고칠지, U8로 넘길지를 정합니다.

U3 코드는 승인됐다(9abd773). 아래 지적을 지금 고치면 **승인된 코드를 바꾸게 된다**. 세션은 지금 U8 데모·배포·문서 기능 설계 Part 1에 있다(작업 트리의 U8 FD 플랜, Q1~Q6).
- 지금 아는 것: 정확성 지적 15건이 모두 재현으로 확인됐다.
  - #1·#3·#4·#5: 에디터에서 평범하게 일해도 저장된 데이터가 조용히 바뀐다. 끈 위치가 되돌아가고, 연결의 근거·prior가 사라지고, 되돌리기가 나중 편집을 덮고, 빈 가중치 칸이 길을 막는다.
  - #2·#6: 지도를 한 번 누르면 보강의 되돌리기를 잃고, `/`에서 있는 월드를 묻지 않고 교체한다.
  - #7: 지금 이 사본에서 `pytest`가 1 failed다(flaky 테스트의 반례가 저장됨).
  - #9·#11은 한 줄로 고친다. 나머지는 low–medium 이하다.
- 왜 지금 정하나: U8 FD 플랜의 이월 목록과 데모 시나리오가 지금 쓰인다. U8 데모는 이 에디터(지도 끌기, 연결 고치기, 보강, `/`의 빌드)를 그대로 보여 주고, code-summary §8의 운영자 확인(#3)도 U8 배포 문서에 실린다.
- 이 답에 기대는 것: U3 후속 커밋을 할지, U8 FD 플랜 이월 목록의 범위, U8 데모·배포 문서(운영자 확인 명령, nginx 요청 크기).

선택지와 결과:
- **A. (권장) 섞는다. 저장 데이터를 조용히 틀리게 만들거나 주요 기능·게이트를 깨는 #1~#7과 한 줄짜리 #9·#11은 지금 U3 후속 커밋으로 고치고, 나머지는 U8 FD 플랜 이월 목록에 올린다.**
  - 까닭: #1·#3·#4·#5는 고칠 때까지 만들어지는 월드에 틀린 값을 남기고 U8 데모가 같은 화면을 쓰며, #7은 지금 게이트를 깬다.
  - 결과: 고칠 것은 다음과 같다.
    - 인스펙터 다시 읽기(`reloadKey`)와 끌기·폼 저장의 덮어쓰기 막기
    - run id 보관과 `GET runs/{id}` 다시 읽기
    - 종류 바꾸기 라우트에서 뒤의 `upsert_connection` 빼기
    - 되돌리기의 엣지 검사
    - 가중치 칸의 빈 값 거절
    - `/` 빌드의 `exists` 계산(또는 `replace=false` 먼저)
    - TP-U3-5 생성기의 쌍 불변식
    - `break` → `continue`, `_start`의 스냅샷 읽기를 acquire 뒤로
  - 테스트: vitest 4~5개(끌기 → 저장, 탭 왕복, 빈 가중치, `/` 교체, BuildPanel)와 pytest 3~4개(종류 바꾸기 API의 근거·prior·출처, 연결 대상 되돌리기 + 바깥 편집, 예산 소진 뒤 캐시된 충돌, 삭제와 이동의 경합)를 더한다. 게이트(pytest·vitest·ruff·black·tsc)를 다시 돈다. BR-U3-27·BLM §4.3의 "run 밖 편집" 정의를 엣지까지 넓히는 정정을 단다.
  - 비용·위험: 승인된 U3 코드를 다시 연다(audit에 후속 수정으로 남긴다). U8 FD Part 1이 그만큼 늦어진다.
  - 되돌리기: 커밋 단위라 쉽다.
- **B. 전부 U8로 넘긴다.**
  - 결과: U3 코드는 그대로 두고, 정확성 15건·§3 32건·정리 17건·설계 메모 10건을 U8 FD 플랜 이월 목록에 올린다. nginx 요청 크기(설계 메모 9), `/` 링크(§3), 데모 버튼은 원래 U8과 한 묶음이다.
  - 비용·위험: U8이 끝날 때까지 #1·#3·#4·#5가 남는다. 그동안 에디터로 고친 월드에 틀린 위치·사라진 근거가 쌓이고, 되살릴 기록이 없다. `pytest`는 이 사본에서 계속 1 failed다(#7을 먼저 고치거나 반례를 지워야 하는데, 지우면 flaky가 숨는다). U8 범위가 커진다.
  - 되돌리기: 쉽다(목록 문서만 바뀐다).
- **C. 감수 위험으로 기록하고 진행한다.**
  - 결과: operations.md "Accepted risks"에 적고 고치지 않는다.
  - 비용·위험: #1·#4는 BR-U3-1·BR-U3-27이 막으려던 덮어쓰기를 오히려 만든다. US-2.2(지도 편집)·US-2.6(보강 되돌리기)의 수용 기준이 실제 화면에서 깨지고 회귀 테스트도 없다. 게이트가 1 failed인 채 남는다.
  - 되돌리기: 나중에 고칠 수 있지만, 그사이 저장된 값은 남는다.
- X. Other (please specify)

어느 쪽을 고르든 설계 결정 셋은 따로 남는다. 보강 예산 모델(#8, 설계 메모 5), 전역 지식의 자리(설계 메모 1), "맞음"이 wiki_conflict를 끝내는 방법(설계 메모 2)이다. 셋 다 U8 FD의 범위가 아니므로 U3 후속이나 다음 주기에서 정한다.
