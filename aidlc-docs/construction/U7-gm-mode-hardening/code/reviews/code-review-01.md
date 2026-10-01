# U7 GM 모드·안정화 — Code Review 01

**원하시는 것**: 세계관 자료로 월드를 만들고, 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG. U7은 두 가지를 맡는다.
- GM 모드: 플레이 화면과 GM 화면을 오가며 월드를 보고, 사건을 제안·승인하고, 슬라이더로 조정한다(US-5.1~5.5).
- 안정화: 되먹임 복원·상한, 사건 상태, 소문 계보, 플레이어 로그, 지역 이름, 조정값(US-8.2·8.4·8.5)을 닫는다.

**이 리뷰가 하는 것**: 승인된 U7 코드(`git diff 5eb3760..83022bf`, 커밋 14개, 코드 96파일 +4421/−1135)가 그 체험과 승인된 규칙(BR-U7-*)을 실제로 지키는지 버그 위주로 확인한다. 코드는 고치지 않았다(리뷰 전용).

**대상**: `locus/play/rumor/{dynamics,feedback,service,generator,spread,promotion}.py`, `locus/play/event/{dynamics,service,suggester,suggest_context}.py`, `locus/play/turn/advancer.py`, `locus/play/{distortion_service,world_state,session_service,base,models,ports,errors,wiring}.py`, `locus/play/player/{log,movement,service}.py`, `locus/play/{npc,gm,deeds}/*`, `locus/play/storage/*`, `locus/shared/{text,config/*}.py`, `locus/world/{build,wiring}.py`·`topology/*`·`ontology/*`, `api/{errors,schemas}.py`·`routers/{gm,play}.py`, `web/src/**`(GM 화면 분할, `CommitRange`, 플레이↔GM 전환), 테스트. CLI 조립 루트 `locus/__main__.py`는 U7이 고치지 않았지만 새 조정값의 호출처라서 함께 봤다.
설계 기준: `functional-design/*`, `nfr/nfr-light.md`, `plans/U7-gm-mode-hardening-code-generation-plan.md`, `code/code-summary.md`, `operations/operations.md`의 "GM mode & hardening".
**방법**: `/code-review` max(재현율 우선).
- 탐색 각도 12개를 병렬로 돌렸다.
  - 줄 단위 셋: 엔진 / 저장소·서비스·설정·API / 웹
  - 제거된 동작, 호출처 추적, 언어 함정, 래퍼·어댑터
  - 재사용, 단순화, 효율, 고도(altitude), CLAUDE.md 규약
  - 이 세션도 직접 후보를 찾았다.
- 후보를 중복 제거한 뒤 후보마다 독립 검증자가 CONFIRMED / PLAUSIBLE / REFUTED 중 하나로 판정했다. 작은 후보와 정리(cleanup) 후보는 검증자 하나가 2~8건을 맡되 후보마다 따로 판정했다.
- 마지막에 새 검토자 1명이 목록에 없는 틈만 찾았다(sweep). sweep이 찾은 6건 중 넷도 따로 검증했고, 그중 #2(전체 생성과 GM 리스)는 medium이다.
- 재현 스크립트·vitest는 모두 세션 scratchpad에만 두었다. 저장소에는 이 기록 파일만 더했다.
- 리뷰 중 HEAD가 병행 세션의 U3 문서 커밋(e54c882, 문서 3개)으로 움직였다. 코드는 83022bf와 같다. 작업 트리의 `audit.md`·U3 FD 플랜 수정도 병행 세션의 것이다(U3 Q1·Q2 답). 둘 다 범위 밖이다.

## 1. 지적 (상한 15, 심각도 순)
판정: C = CONFIRMED(입력·결과로 재현), P = PLAUSIBLE(기제는 실재, 발생 조건이 타이밍·설정에 달림). 괄호 안은 그 지적을 독립적으로 찾은 탐색 각도 수이고, "sweep"은 마지막 틈 찾기가 찾은 것이다. 15건 모두 C다.

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `web/src/ui/CommitRange.tsx:18-43` | "같은 값이면 보내지 않는다"(BR-U7-24)는 비교가, 브라우저가 step(0.05)에 맞춰 반올림한 DOM 값과 반올림하지 않은 서버 값을 비교한다. 서버 값은 대개 step 밖이다. 되먹임(0.375), 사건(크기×0.3×경로 가중치), 전파, 행적 씨앗, 부동소수 오차가 그렇게 만든다. 그래서 Tab으로 슬라이더를 지나가기만 해도(blur), 손잡이를 끌지 않고 눌렀다 떼기만 해도(pointerUp) GM이 고르지 않은 값이 저장된다. 왜곡도는 저장되면서 되먹임 몫이 지워져(BR-U7-5) 한때의 몫이 영구 기준이 된다. 지지도는 승격(0.6)·강한 소문(0.45)·씨앗 기준을 넘길 수 있다. U7 이전에는 mouseUp만 저장했다 | C (2각도) | **medium** | 사용자가 값을 실제로 바꿨을 때만 저장한다(onChange에서 표시를 켜고 저장하면 끈다). 또는 렌더 뒤 브라우저가 보이는 값과 비교한다. step 밖 값(0.375)으로 반올림을 흉내 내는 vitest를 더한다 |
| 2 | `web/src/features/gm/GmHub.tsx:110-139` `runBulk`, `api/routers/gm.py:42-55` `_idle` | "전체 생성"·"전체 재생성"이 같은 세션에 GM 쓰기를 5개씩 동시에 보낸다. 그런데 GM 쓰기 경로는 모두 세션 단위의 배타 리스(`guard.hold`)를 쓰기가 끝날 때까지 쥔다(U4 코드 리뷰 02 #7). 그래서 한 묶음에서 첫 요청만 LLM을 부르고, 나머지 넷은 바로 409를 받아 실패로 세어진다. 15지역이면 3지역만 채워진다. U4부터 그랬고 U7이 그대로 옮겼다. U7 frontend §2.2는 여전히 "전체 생성·재생성(`mapLimit` 5)"을 적고, BR-U7-25는 전체 생성·재생성이 그대로 남기를 요구한다 | C (sweep) | **medium** | GM 쓰기끼리는 리스를 나누고 턴만 배타로 둔다. 가드가 GM 보유자 수를 세어, GM `hold`는 턴이 돌 때만 거절하고 턴 `acquire`는 턴이나 GM 보유자가 있으면 거절한다. 그러면 U4-2 #7과 FD R-06을 지키면서 설계의 동시 5개를 살린다. 가장 작은 고침은 일괄 쓰기를 하나씩 보내는 것이다(`mapLimit(ids, 1, op)`, 약 5배 느림). 어느 쪽이든 runBulk가 409를 따로 알리고, 5지역 동시 생성이 모두 200인 회귀 테스트를 더한다 |
| 3 | `locus/__main__.py:66` `_world_services` | CLI 조립 루트가 `WorldBuilder.from_factory(...)`에 `tuning=settings.world_tuning()`을 넘기지 않는다. `from_factory`는 `tuning or WorldTuning()`으로 조용히 기본값을 쓴다. 그래서 `locus world build`·`build-world`는 `TOPOLOGY_BASE_WEIGHTS`·`TOPOLOGY_DEFAULT_BASE`·`TOPOLOGY_TERRAIN_MODIFIERS`·`ONTOLOGY_DEDUP_THRESHOLD`를 무시하고, API 빌드(`assemble_world`)만 이 값을 따른다. BR-U7-19("env로 덮어쓴다")·BLM §7("설정을 바꾸면 그 값이 실제 계산에 쓰인다")·env.example·operations.md와 어긋난다 | C (5각도) | low–medium | `_world_services`에서 `tuning=settings.world_tuning()`을 넘긴다. `from_factory`의 `tuning`을 필수 키워드로 바꿔 빠뜨린 호출처가 바로 실패하게 한다. `test_cli`에 `world build` 조정값 사례를 더한다 |
| 4 | `web/src/ui/CommitRange.tsx:18-27`, `features/gm/GmHub.tsx:82-91·204-210` | `CommitRange`는 저장이 성공하기 전에 `saved.current = v`로 "저장됨"을 기록하고, `value` prop이 바뀔 때만 다시 맞춘다. GmHub의 `run`은 실패하면 오류만 보이고 다시 읽지 않는다. 그래서 409로 거절된 값이 손잡이에 남고(이름표는 서버 값), 같은 값으로 다시 놓아도 보내지 않는다. 409는 플레이어 턴이 GM 리스를 쥔 동안이나 GM 자신의 전체 생성 중에 생긴다. 왜곡도 슬라이더는 지역마다 key가 없어서, 서버 값이 같은 다른 지역을 고르면 그 낡은 값이 따라가고 그 지역에 같은 값을 저장하는 것도 막힌다. BR-U7-24·frontend §2.4("마지막으로 저장한 값")와 어긋난다. 옛 SessionPanel은 읽을 때마다 슬라이더를 다시 맞췄다 | C (6각도 + 이 세션) | low–medium | 왜곡도 패널에 `key={regionId}`를 준다. `onCommit`이 Promise를 돌려주게 해서(GmHub `run`이 성공 여부를 돌려줌) 성공했을 때만 `saved`를 옮긴다. 실패하면 `draft`·`saved`를 `value`로 되돌린다 |
| 5 | `play/player/log.py:65-92` `player_log`, `turn/advancer.py:491-532` `_fail` | 플레이어 로그는 "그때 있던 지역"을 `session_started`·`player_moved` 줄로만 정한다. 턴이 하나도 진행되지 않은 이동 실행이 실패하면 `_fail`이 플레이어를 출발 지역으로 되돌린다(`player.region_id = run.from_region_id`, :513). 그런데 로그가 읽는 줄은 남기지 않는다. TURN_RUN_FAILED에는 지역이 없고, PLAYER_MOVED는 감사 기록으로 남는다. 그래서 다음 이동까지 가 보지도 않은 목적지의 지역 줄이 보이고, 지금 있는 지역의 줄은 숨는다. BR-U7-12("그 줄이 쓰인 때 플레이어가 있던 지역")와 FD Q3=A에 어긋난다. BR-U7-13은 이 경우를 다루지 않았다 | C (6각도 + 이 세션) | low–medium | `_fail`이 위치를 되돌릴 때 TURN_RUN_FAILED 페이로드에 `restored_region_id`를 싣고, `player_log`는 그 줄에서 `here`와 `seen_events`를 다시 정한다. BR-U7-13을 고치고 EX(실패한 이동 → GM 턴 → a의 줄은 보이고 b의 줄은 없음)를 더한다 |
| 6 | `web/src/features/gm/GmHub.tsx:82-86·94-107·110-139` `run`·`advance`·`runBulk` | 쓰기 뒤의 `await refresh()`는 버튼을 누른 렌더의 `refresh`를 부르고, 그 클로저는 그때의 지역에 묶여 있다. 쓰는 동안 GM이 지도에서 다른 지역을 고르면, 그 낡은 호출이 가장 최신 `readSeq`를 받아 이전 지역의 소문 목록을 새 지역 머리글 아래에 그린다. 그 목록의 지지도 슬라이더는 이전 지역의 소문을 고친다. readSeq 가드(U5 #11)는 호출 순서만 본다. U7 이전부터 있었고 U7이 그대로 옮겼다 | C | low–medium | `refreshRef = useRef(refresh); refreshRef.current = refresh;`로 두고, 쓰기 뒤에는 `await refreshRef.current()`를 부른다. 쓰는 중 지역을 바꾸는 vitest를 더한다 |
| 7 | `web/src/features/play/ActionBar.tsx:75`, `routes/PlayPage.tsx:308` | 선언 상자가 요청 중뿐 아니라 턴이 도는 내내 잠긴다. textarea의 `disabled`에 `busy \|\| closed`가 들어가기 때문이다. U7 이전에는 버튼만 꺼졌고, 코드 플랜 U6 #12 행은 "요청 중에는" 잠그라고 했다. 그래서 플레이어는 서술·판단(LLM)이나 여러 턴짜리 이동이 끝날 때까지 다음 선언을 쓸 수 없다 | C | low | prop을 나눈다. textarea는 `closed \|\| sending`, 버튼은 `busy \|\| closed`로 끈다. 턴 중에도 입력할 수 있는지 보는 테스트를 더한다 |
| 8 | `web/src/features/gm/DistortionPanel.tsx:25` | 왜곡도 이름표가 끄는 값이 아니라 서버 값을 보인다. 초안은 CommitRange 안에만 있다. 그래서 GM은 놓기·저장·다시 읽기가 끝날 때까지 고르는 숫자를 볼 수 없다. U7 이전 SessionPanel은 이름표가 손잡이를 따라갔다 | C (2각도) | low | CommitRange가 초안을 알려 주게 하고(`onDraft`), 이름표는 초안을 보인다 |
| 9 | `locus/play/rumor/dynamics.py:109` `region_feedback` | U7이 강한 소문 기준을 0.6에서 0.45로 낮췄는데, 부동소수 지지도를 그대로 비교한다. 흔한 경로가 기준 바로 아래에 떨어진다. GM이 0.35(슬라이더 step 0.05)로 정한 소문에 사건 강화 +0.1이 더해지면 0.44999999999999996이고, 0.6에서 조용한 턴 3번을 지나도 같다. 화면은 "0.45"로 보이는데 강한 소문으로 세지 않아서, 그 턴의 되먹임 올림이 빠지거나 복원으로 바뀐다. 옛 기준 0.6은 이런 경로에서 정확히 맞았다 | C (sweep) | low | 지지도를 쓰는 곳(`evolve_support`·`decay_support`·`adjust_support`)에서 반올림하거나(`round(clamp01(x), 6)`), 비교에 작은 허용치를 둔다 |
| 10 | `web/src/i18n.ts:541-555` `timelineText` | U7 이전에 쓰인 `event_created` 줄 중 `suggested`·`approved` 표시가 있는 줄을 새 템플릿으로 보낸다. 그 템플릿은 `{category}`·`{region}`이 필요한데, 실제 지난 페이로드(`{event_id, region_id, suggested}`, `{event_id, approved}`)에는 category가 없고 승인 줄은 지역도 없다. `t()`는 없는 값을 `{category}` 그대로 남긴다. 그래서 U7 이전 세션의 GM 타임라인이 "r1에 {category} 사건이 제안되었다", "—의 {category} 사건을 승인했다"로 보인다. 전에는 요약("suggested war event in r1", "approved event e1")이 보였다. domain-entities §2.1("화면 템플릿은 두 형태를 다 읽는다")과 code-summary §5 8.7에 어긋난다 | C (3각도 + 이 세션) | low | 표시가 있는 줄은 `payload.category`가 있을 때만 새 템플릿으로 보내고, 아니면 요약을 쓴다. 채우지 못한 `{param}`이 남으면 요약으로 돌아가는 방법도 있다. gm.test.tsx의 지난 줄 fixture를 실제 모양으로 바꾼다 |
| 11 | `web/src/routes/GmPage.tsx:92-94` `onDeedChanged`, `features/gm/DeedPanel.tsx:56-61` | U6 #11이 절반만 고쳐졌다. 취소가 409 "session is closed"를 받으면 DeedPanel은 "세션이 종료되었습니다"를 보이고 `onChanged()`로 페이지가 세션을 다시 읽기를 기대한다. 그런데 GmPage의 `onDeedChanged`는 `deedRev`만 올리고 `loadSession()`을 부르지 않는다. 그래서 `session.status`가 open으로 남아 취소·턴 진행·생성·슬라이더 같은 GM 조작이 모두 켜져 있고, 누를 때마다 409를 받는다. 코드 플랜 "U6 #10·#11" 행("세션을 다시 읽는다")과 어긋난다 | C (3각도 + 이 세션) | low | `onDeedChanged`에 `loadSession()`을 더한다. GmHub의 `run`·`advance`도 `conflictKind`로 409를 갈라 "closed"면 `onChanged`를 부르게 한다. GmPage 수준 vitest를 더한다 |
| 12 | `web/src/features/play/DialoguePanel.tsx:65-67·96-104`, `web/src/api/http.ts:20-24` | 대화 중 세션이 다른 곳에서 닫히면(GM 탭, CLI `--force`, 월드 교체) `say`·`start`가 409 "session is closed"를 받는다. DialoguePanel은 503만 가르고 나머지는 원문("Error: 409 Conflict: {…}")을 보인다. 페이지에 세션이 닫혔다고 알릴 길이 없어 입력칸과 기다리기 버튼이 켜진 채다. U6 #10·#11의 `conflictKind`는 PlayPage `act`와 DeedPanel에만 들어갔다. `conflictKind`가 기대는 영어 문장("session is closed")을 고정하는 백엔드 테스트도 없다 | C | low | DialoguePanel의 `start`·`say` catch에서 `conflictKind`를 쓴다. "closed"면 `play.sessionClosed`를 보이고, 새 `onClosed` prop으로 PlayPage가 `refresh()`하게 한다. API 테스트로 409 본문을 고정하거나, 409에 안정된 code 필드를 둔다(U6 #11이 제안한 대안) |
| 13 | `locus/play/world_state.py:49`, `play/event/service.py:289·297` `_event_lines` | U7이 더한 두 곳이 사건 상태를 `str(ev.status) == "active"`처럼 손으로 비교한다. `approve()`·`resolve()`는 enum 멤버를 넣고(`validate_assignment` 없음), `str(EventStatus.ACTIVE)`는 "EventStatus.ACTIVE"다. 그래서 인메모리 저장소(오프라인 테스트가 모두 쓰는 쌍둥이)에서는 승인한 사건이 세계 상태의 `active_events`에 0으로 세어지고, 사건 제안 프롬프트에 "EventStatus.ACTIVE"가 찍힌다. PostgreSQL은 문자열로 다시 읽어서 맞다. models.py:203-205 주석이 이런 손 비교를 하지 말라고 적어 둔 자리다 | C (4각도) | low | `EventStatus(ev.status) is EventStatus.ACTIVE`(또는 `is_active()`)와 `not e.is_suggested()`로 비교하고 `EventStatus(e.status).value`를 찍는다. 인메모리에서 제안 → 승인 → 상태·프롬프트를 보는 테스트를 더한다 |
| 14 | `play/event/suggest_context.py:111` `suggestion_context`, `shared/config/settings.py:130` | 제안 맥락은 머리말 → 지역 → 최근 사건 → 최근 행적 순으로 이어 붙인 뒤 21,000자에서 자른다. `EVENT_SUGGEST_MAX_REGIONS`에는 하한(1)만 있다. 그래서 값을 크게 잡으면(글자 상한까지 찬 지역이면 32곳부터, 보통 길이면 60곳 남짓부터) BR-U7-9가 요구하는 최근 사건·행적이 소리 없이 잘리거나 빠지고, 마지막 줄이 중간에서 잘린다. operations.md는 "마지막 사건 5개와 행적 5개를 싣는다"고 적었다 | C (3각도 + 이 세션) | low | 지역 구역에 예산을 둔다. 머리말·사건·행적을 먼저 잡고, 남는 만큼 지역 줄을 통째로 더한다. 아니면 노브에 상한을 두거나 지역 수에서 상한을 구해 기동 때 검사한다(BR-U7-20) |
| 15 | `web/src/features/gm/ManualTurnPanel.tsx:16·52` | 사건 제안 개수 선택이 1~5로 고정되어 있고, GmHub는 `maxSuggest`를 넘기지 않는다. 서버 상한은 U7이 env로 연 `EVENT_SUGGEST_MAX`인데, 어떤 읽기도 이 값을 화면에 주지 않는다. 상한이 3이면 4·5를 고를 때 400 원문이 보이고, 8이면 6~8을 고를 수 없다. frontend §2.2의 "서버 상한과 같다"는 기본값에서만 맞다 | C (5각도 + 이 세션) | low | `max_event_suggestions`를 GM 읽기(세계 상태나 세션)에 실어 `maxSuggest`로 넘긴다(`RegionView.declare_max_chars`와 같은 방식). frontend §2.2·§4의 "1~5"를 "1~서버 상한"으로 고친다 |

### 지적별 재현 상황
1. **슬라이더가 고르지 않은 값을 저장**: Chrome 146 headless에서 `<input type=range min=0 max=1 step=0.05>`에 0.375·0.58·0.333·0.15000000000000002를 넣으면 `.value`는 "0.4"·"0.6"·"0.35"·"0.15"다. 실제 `CommitRange`를 묶어 CDP로 돌렸다. 서버 값이 0.375(왜곡도)·0.58(지지도)·0.2−0.05·0.45인 슬라이더 넷을 Tab 다섯 번으로 지나가기만 했더니 저장이 셋(0.4, 0.6, 0.15) 나갔다. 0.45는 보내지 않는다. 손잡이를 끌지 않고 눌렀다 떼도 0.4가 저장된다. 서버 쪽은 이렇다. EX-2 수열의 지역이 1턴 뒤 (0.375, 몫 0.075)일 때 Tab이 한 번 지나가면 `set_distortion` 줄(`degree 0.4`, `feedback_share_cleared 0.075`)이 생긴다. 그 뒤 지역은 (0.475, 0.075) → (0.425, 0.025) → (0.4, 0) → (0.4, 0)으로 간다. 손대지 않았으면 0.3으로 돌아갔을 지역이 0.1 높게 굳는다. 지지도 0.63인 소문(사건 없는 지역)은 손대지 않으면 다음 턴 0.58로 승격되지 않는다. Tab 한 번으로 0.65가 저장되면 0.6으로 승격된다. jsdom은 step 반올림을 하지 않고(form-controls.js), gm.test.tsx는 step 위의 값(0.3)만 써서 테스트가 이 경우를 보지 못한다.
2. **일괄 생성과 GM 리스**: 실제 단일 워커 uvicorn과 TestClient에서 15지역 세션에 0.3초 걸리는 가짜 LLM을 두고 5개씩 보냈다. 생성은 200이 3건, 409가 12건이고 재생성도 3/15다. 실패한 12지역은 하나씩 보내면 모두 200이다. 패키지 데모 월드(aldermoor, 5지역)에서는 클릭 한 번에 한 지역만 채워져서 다섯 번 눌러야 하고, 전체 재생성은 클릭마다 한 지역만 바꾼다. 알림은 "전체 생성 3/15 완료 · 12건 실패"이고 오류 줄은 비어 있다. 409 본문은 GM 쓰기끼리 부딪혀도 "turn in progress"라서 원인을 잘못 가리킨다. 일괄 생성은 X3(fbbff5c, GM 쓰기에 가드가 없던 때)에서 왔고, 리스는 U4 코드 리뷰 02 #7(07e4b04)이 턴과 GM 쓰기의 충돌만 보고 넣었다. vitest는 `api.generateRumors`를 mock하고 pytest에는 동시 GM 쓰기가 없어서, 둘 다 보지 못한다. LLM이 없으면 생성은 어차피 503이다.
3. **CLI 빌드의 조정값**: 같은 env(`TOPOLOGY_BASE_WEIGHTS={"adjacent":0.25,"route":0.35}`, `ONTOLOGY_DEDUP_THRESHOLD=0.95`)로 실제 `cli.main(["world","build",...])`을 돌렸다. 저장된 연결 가중치는 adjacent 0.8·route 0.6이고 dedup 기준은 0.86이다. 같은 입력을 `assemble_world(...).builder`로 빌드하면 0.25·0.35·0.95다. 값은 기동 때 검증되고(BR-U7-20) 그 뒤 무시된다. 가중치는 연결 엣지에 저장되어 합의·전해 들음·이동 비용·사건 전파·행적 전파에 쓰이므로, 잘못 빌드된 월드는 다시 빌드해야 고쳐진다. `world demo`·`world import`는 World File의 가중치를 쓰므로 해당하지 않는다. 두 조립 루트의 tuning을 보는 테스트는 없다. U7 diff는 `locus/__main__.py`를 건드리지 않았다(플랜 6.9는 `world/wiring.py`·`build.py`만 적었다).
4. **거절된 저장**: 지역 a·b가 0.3이다. a를 0.5로 끌어 놓았는데 PUT이 409("turn in progress")를 받는다. 손잡이는 0.5, 이름표는 "왜곡 0.30"이다. 0.5에서 pointerUp·mouseUp·touchEnd·blur·ArrowRight를 해도 PUT은 1번뿐이다. 그 뒤 턴을 진행해 다시 읽으면 오류 줄은 사라지는데 손잡이는 여전히 0.5다. b를 고르면 같은 DOM 노드가 b를 보이며 손잡이 0.5·이름표 0.30이고, b에 0.5를 저장해도 보내지 않는다. 거절이 없어도 a의 저장이 끝나기 전에 b를 누르면 같다. 지지도 슬라이더는 앞의 경우만 해당한다(소문마다 key가 있다). 서버 상태는 망가지지 않는다. 409는 흔하다. 플레이 화면에서 GM 모드로 넘어와도 진행 중이던 턴은 계속되고(frontend §2.1), 전체 생성 중에도 슬라이더는 `closed`일 때만 꺼진다.
5. **실패한 이동 뒤의 플레이어 로그**: a에서 b로 이동하는데 첫 턴의 `bump_turn`이 한 번 예외를 낸다. 실행은 FAILED이고 플레이어와 `/region`은 a다. a와 b에 지속 사건을 두고 GM 턴을 돌렸다. GM 타임라인에는 a·b의 `event_applied`가 모두 있다. 플레이어 로그는 `[session_started a, player_moved b, turn_run_failed, event_applied b]`다. a에서 기다리기를 해도 a의 줄은 계속 숨는다. 실행 제출이 거절되는 경로(`begin`의 executor 오류)도 같다. 로그는 append-only 타임라인에서 매번 다시 계산되므로 그사이의 줄은 계속 잘못 걸러진다. 실제 발생에는 이동 첫 턴의 저장소 오류가 필요하다(LLM 오류는 잡힌다). TP-U7-6 생성기에는 실패 복원이 없어서 속성 테스트가 이 경우를 보지 못한다.
6. **낡은 다시 읽기**: r1(Riverton)을 고른 채 생성(LLM 몇 초)을 누르고 그사이 r2(Highcrag)를 골랐다. 끝나면 머리글은 "지역 Highcrag 왜곡 0.60"인데 목록은 r1의 소문이다. 지지도를 0.9로 놓으면 `setSupport('s1','r1-x',0.9)`가 간다. r2 읽기가 더 늦게 도착하면 맞는 답이 버려진다. 턴 진행·전체 생성도 같다. 실제 GmPage에서도 다음 쓰기나 지역 전환까지 남는다. 지역을 고르지 않고 전체 생성을 시작한 뒤 채워지는 지역을 고르면, 끝난 뒤 그 지역의 목록이 빈다. 5eb3760의 SessionPanel에서도 재현된다(그때는 왜곡도까지 이전 지역 값이었다). U7은 왜곡도를 렌더에서 구하게 바꿔 증상을 줄였지만, 주석에서 "(or for the previous region)"을 지웠다.
7. **턴 중 선언 상자**: PlayPage에서 선언을 보내 202를 받고 실행을 계속 폴링하게 했다. 폴링 7번 내내 선언 상자가 꺼져 있고, 실행이 'done'이 된 뒤에야 켜진다. 같은 조건에서 U7 이전 ActionBar(5eb3760)의 textarea는 켜져 있다. 기다리기·이동 전에 쓰던 초안은 지워지지 않으니 글을 잃지는 않는다. 다만 다음 선언을 미리 쓸 수 없고 상자는 포커스를 잃는다. 대화 패널은 턴 중에도 말할 수 있다(BR-U5-27).
8. **왜곡도 이름표**: 왜곡도 0.30에서 슬라이더를 0.8로 끌면 손잡이는 0.8, 이름표는 "왜곡 0.30"이다. 0.65로 옮겨도 이름표는 0.30이고, 놓아서 저장과 다시 읽기가 끝나야 "왜곡 0.65"가 된다. U7 이전 SessionPanel은 끄는 동안 이름표가 따라갔다. 지지도 이름표는 U7 전에도 서버 값이었다.
9. **0.45 기준의 부동소수**: 실제 함수로 GM 0.35 → 사건 한 턴을 돌리면 지지도가 0.44999999999999996이고 화면에는 "0.45"로 보인다. 다음 턴 `region_feedback`은 {}이고, 같은 값을 0.45로 넣으면 {'r': 0.1}이다. 몫이 0.05인 지역은 올림(0.4) 대신 복원(0.25)이 된다. 8턴까지의 사건·조용 패턴을 모두 모델로 돌렸다. 값이 "숫자로는" 기준과 같은 검사 2,344번 가운데 530번이 강하지 않게 판정된다. 옛 기준 0.6에서는 256번 가운데 0번이다. 가지치기(0.05 미만)에도 U7 이전부터 같은 꼴이 있다(GM 0.15 + 조용 2턴 = 0.04999999999999999로 한 턴 일찍 가지치기).
10. **지난 타임라인 줄**: 5eb3760의 `event/service.py`가 쓰던 실제 페이로드로 새·옛 `timelineText`를 비교했다. ko에서 제안 줄은 "r1에 {category} 사건이 제안되었다", 승인 줄은 "—의 {category} 사건을 승인했다"이고, en도 "Approved the {category} event in —"다. U7 이전에는 event_created에 일부러 템플릿을 두지 않아(리뷰 #3) 요약이 보였다. gm.test.tsx:230의 fixture `{approved: true, region_id: "a", category: "war"}`는 실제로 쓰인 적이 없는 모양이라 이 결함을 잡지 못한다. 지난 승격·가지치기·해소 줄(지역 없음)도 "승격: rm1"에서 "소문 승격 · —"로 바뀐다. 이것은 FR-D3이 id를 화면에서 빼려는 설계의 빈틈이라 결함 수에 넣지 않았다(§5 설계 메모 2).
11. **GM 화면의 닫힌 세션**: GmPage(/gm/s1)를 열어 둔 채 세션을 다른 곳에서 닫았다. 취소를 확인하면 알림은 "세션이 종료되었습니다"이고 `getSession`은 더 불리지 않는다. 조작 9개(취소, 턴 진행, 사건 제안, 전체 생성, 전체 재생성, 생성, 재생성, 왜곡도 슬라이더, 사건 생성)가 모두 켜져 있다. 다시 취소하면 409를 또 받는다. `loadSession()` 한 줄을 넣은 사본에서는 `getSession`이 1번 더 불리고 9개가 모두 꺼진다. PlayPage 경로는 맞다(`refresh`가 세션을 다시 읽어 버튼이 꺼진다). U6 #11을 보는 테스트는 `conflictKind` 단위 테스트뿐이다. U7 이전의 `onDeedChanged`도 세션을 읽지 않았고, U7은 C1 때문에 `sessionRev` 올리기를 뺐다.
12. **대화 중 닫힌 세션**: 실제 `http()`에 fetch만 바꿔 끼운 vitest로 Mara와 대화하다가 서버에서 세션을 닫고 두 줄을 보냈다. 두 번 모두 원문 409가 보이고, 세션 읽기 수는 그대로이며, 입력칸과 기다리기 버튼은 켜져 있다. 기다리기를 한 번 누르면(`act` → `conflictKind` "closed") 그제야 잠긴다. `SessionClosedError` 문구를 "session closed: …"로 바꾸는 변이를 넣어도 백엔드 테스트 730개가 모두 통과한다. 그러면 `conflictKind`는 닫힌 세션을 모두 "busy"로 보고 U6 #10의 증상이 돌아온다. U5 리뷰 #7이 권한 "start가 409면 읽기 전용"도 반쪽만 들어가 있다.
13. **사건 상태의 손 비교**: compose_play와 인메모리 저장소로 제안 → 승인 → `WorldStateService.state` → 다시 제안을 돌렸다. `active_events`는 {'a': 0}이고, 프롬프트는 "- [Riverton] war m=0.5 EventStatus.ACTIVE: raid", 해소 뒤에는 "EventStatus.RESOLVED"다. SQLite 어댑터에서는 1과 "active"다. 같은 세션을 두 어댑터가 다르게 보이고, 이 경로(승인 뒤 상태·프롬프트 읽기)를 보는 테스트가 없다.
14. **제안 맥락 자르기**: 실제 `suggest_events` 경로에 사건 5개·행적 5개를 두고 지역 수만 바꿨다. 글자 상한까지 찬 지역이면 30곳은 20,197자로 모두 들어간다. 32곳이면 마지막 행적 줄이 483/700자에서 잘린다. 40곳이면 사건 줄 2개만 남고 행적 머리말이 없으며, 45곳이면 두 머리말이 모두 없다. 보통 길이(UUID id, 이름 12자, 설명 120자)면 58곳까지는 괜찮다. 62곳이면 행적이 2/5만 남고, 70곳부터는 사건·행적이 없으며 마지막 줄이 이름 중간에서 잘린다. `EVENT_SUGGEST_MAX_REGIONS=1000`으로도 기동된다. 기본값 30에서는 생기지 않는다.
15. **제안 개수 상한**: `EVENT_SUGGEST_MAX=3`으로 띄우면 `n=3`은 200이고 `n=4`·`n=5`는 400 "n must be between 1 and 3"이다. 화면의 개수 선택은 1~5를 보이고, 4를 고르면 GM 허브에 `Error: 400 Bad Request: {…}` 원문이 뜬다. `EVENT_SUGGEST_MAX=8`이면 서버는 8까지 받지만 화면에서는 5까지만 고를 수 있다. LLM 호출 전에 거절되므로 저장되는 것은 없다.

## 2. 상한 아래 — 정리(cleanup) 지적
모두 검증 CONFIRMED다. C1은 low–medium, 나머지는 low다. 정확성 지적이 우선이라 상한 밖에 두었다.

| # | 위치 | 지적 | 권장 조치 |
|---|---|---|---|
| C1 | `web/src/features/gm/GmHub.tsx:141-160` `generateAll` | "전체 생성"이 캐노니컬 소문 수를 세려고 지역마다 `listRumors`를 한 번씩 부른다. 이 GM 읽기는 번역 보강을 거친다. 그래서 표시 언어가 기본값 ko이면 모든 지역의 번역 안 된 소문마다 배경 번역 LLM 호출이 예약된다(8지역·14문장에서 14회). U7의 `GET /state`는 지역별 `active_rumors`·`deed_rumors`를 한 번에, LLM 없이 준다 | `api.getWorldState(sid)` 한 번으로 `active_rumors - deed_rumors === 0`인 지역을 고른다. X3 BR-X3-5의 "지역별 listRumors(Q6=B)" 문구도 고친다(새 엔드포인트를 더하지 않는다는 Q6=B의 까닭은 그대로 지켜진다) |
| C2 | `play/region_knowledge.py:76` `region_sources` | 지역 소스를 풀 때마다 비활성 소문까지 모두 읽는다(`include_pruned=True`). U7의 재생성은 지우지 않고 비활성화하므로(BR-U7-16) 재생성할 때마다 행이 쌓인다. 그런데 플레이어 `/region`과 세션 지역 지식은 활성 소문만 쓴다. 재생성 150번이면 `/region`이 453행을 읽어 3행을 쓰고, 1.28ms가 7.42ms가 된다 | `region_sources(lineage=False)` 인자를 두고, 계보가 필요한 대화·판단·서술 장면만 비활성까지 읽는다 |
| C3 | `play/rumor/spread.py:41-57·91` | 새 `neighbour_map`이 `_neighbour_weights`와 같은 규칙(이웃마다 가장 강한 간선, 자기 고리 제외)을 다시 쓴다. 엔진은 늘 `neighbour_map`을 넘기고, `test_spread.py`의 `plan_spread` 호출 9개(TP-U6-1·2 PBT 포함)는 넘기지 않아 `_neighbour_weights`만 시험한다. `neighbour_map`을 "마지막 간선이 이김"·"가장 약한 간선"·"자기 고리 유지"로 바꾸는 변이에도 730개가 모두 통과한다. 평행 간선·자기 고리 규칙은 어느 쪽에서도 테스트되지 않는다 | `_neighbour_weights`를 지우고 `near = (neighbours if neighbours is not None else neighbour_map(graph)).get(here, {})`로 쓴다. 평행 간선·자기 고리 예제를 더한다 |
| C4 | `play/rumor/service.py:81-84`, `play/event/service.py:263-266·285·308`, `play/turn/advancer.py:559·706·849·899·949`, `play/distortion_service.py:49-50` | FR-D3의 "이름, 없으면 id" 규칙이 다섯 가지로 쓰였다. `_region_name` 두 벌(본문이 같음), `_where`, 인라인 `names.get(x, x)` 16곳, `regions_by_id[x].name`이다. 한 턴에 이름표를 네 번 만들고(같은 함수 안에서 두 번), 제안 한 번에 두 번 만든다. BLM §6은 "이름표는 하나로 만든다"고 했다. 또 `_region_name`마다 `SnapshotSource.get`을 부르는데, 운영의 `WorldCache`는 그때마다 Neo4j로 월드 버전을 확인한다. 지지도 조정·왜곡도 설정은 2회, 생성은 3회이고, 해소는 2회를 PostgreSQL 트랜잭션 안에서 한다. 이름 폴백 갈래(사라진 지역)를 보는 테스트는 없다(RumorService 쪽만 바꾸는 변이에도 play·api 446개 통과) | `play/base.py`의 `require_region` 옆에 `region_name(snapshot, rid)`·`where(snapshot, rid)` 하나를 둔다. `require_region`이 지역을 돌려주게 해서 서비스 호출마다 스냅샷을 한 번 읽고 이름을 UoW 전에 한 번 구한다. 엔진은 `:559`의 `names`를 넘겨 쓴다 |
| C5 | `play/turn/advancer.py:800` `_draft_spread` | 행적 소문 부모가 있는 턴마다 세션의 모든 행적을 읽어, 부모의 원점 행적 몇 개만 찾는다(300행에서 3.59ms, `deed_ids=`로는 0.30ms). U6 리뷰 C3은 "행적 지도를 한 번 만들어 넘긴다"를 권했지만, U7 플랜의 C3 행은 소문 읽기만 다뤘다 | `list_deeds(session.id, deed_ids=sorted({p.origin_deed_id for p in parents if p.origin_deed_id}))` |
| C6 | `play/player/service.py:98`, `web/src/routes/PlayPage.tsx:180-196` | `/log`는 숨김 종류까지 전체 타임라인을 읽고, 거른 이력 전부를 돌려준다(3,007행에서 445줄·107KB). 화면은 30줄만 그린다. 플레이 화면은 마운트와 행동마다 `/log`를 두 번 읽는다. 서버 쪽 모양(읽기 2회)은 BLM §5·NFR R-05 그대로다 | `/log`에 선택 `limit`(player_log 뒤에 꼬리를 자름)을 두고 화면이 30을 넘긴다. 쉬는 마운트의 두 번째 읽기를 건너뛴다(C7과 함께) |
| C7 | `web/src/routes/PlayPage.tsx:180-196` | 마운트 때 `refresh`(4요청) → `listTurnRuns` → 아무것도 돌지 않으면 `refresh`를 한 번 더 한다(U4부터). U7의 GM 왕복이 플레이 화면을 매번 다시 마운트해서, GM에 다녀오면 18요청이다 | `listTurnRuns`를 첫 읽기와 함께 하고, 첫 화면이 `turn_running`인데 실행이 없을 때만 다시 읽는다 |
| C8 | `web/src/features/gm/GmHub.tsx:110-130` `runBulk` | 5개씩 묶어 묶음마다 가장 느린 작업을 기다린다. 같은 파일이 U7이 따로 뺀 `bulk.ts`의 `mapLimit`(작업자 풀)을 사전 조사에 쓴다. r0 하나가 늦으면 runBulk는 5개만, mapLimit은 10개 모두 시작한다 | `mapLimit(ids, BULK_LIMIT, ...)`으로 바꾼다. 동시 수는 #2를 고칠 때 함께 정한다 |
| C9 | `play/turn/advancer.py:591-593·628` | (b3)의 `events.distortions.get(region_id)` 뒤 저장소 폴백은 닿지 않는다. 사건 대상 지역은 늘 `events.distortions`의 키다(`propagate_delta`가 원점을 넣고 `apply_deltas`가 모든 키를 쓴다). 커버리지에서도 593행은 한 번도 돌지 않는다. U6 리뷰 C9이 같은 자리를 짚었는데, 플랜은 씨앗 쪽만 고쳤다. `:628`의 `if rid in events.distortions`도 늘 참이다 | `events.distortions.get(region_id, DEFAULT_DISTORTION_DEGREE)`로 쓰고, 늘 참인 조건을 지운다 |
| C10 | `world/topology/weights.py:15-17` | `BASE_WEIGHT`·`DEFAULT_BASE`·`TERRAIN_MODIFIER` 별칭을 아무도 읽지 않는다(U7 전후 모두). 표는 `WorldTuning`에 있어서, 별칭을 고쳐도 가중치는 바뀌지 않는다 | 세 별칭을 지우고 `_DEFAULTS`(기본 인자)와 `DEFAULT_MODIFIER`만 남긴다 |
| C11 | `play/event/suggester.py:56·66-68`, `play/event/suggest_context.py:18` | `EventSuggester.system()`은 부르는 곳이 없다. `_prompt`를 `prompt`로 공개했지만 내부 호출뿐이다. `MATERIAL`이 `npc/prompts.MATERIAL`과 글자까지 같은 두 번째 정의다. 주입 가드 머리말이 두 곳에 있으면 한쪽만 고쳐질 수 있다 | `system()`을 지우고 `_prompt`로 되돌린다. `MATERIAL`은 한 곳(`shared/text.py` 등)에 두고 가져다 쓴다 |
| C12 | `play/distortion_service.py:34-43`, `play/world_state.py:53-59`, `play/rumor/feedback.py:67-68`, `play/rumor/dynamics.py:154` | BR-U7-18("저장 행 또는 기본값 0.3·몫 0")을 왜곡도 목록과 세계 상태가 따로 쓴다. 되먹임의 기본 `FeedbackState`도 두 곳에서 만든다(`step_feedback` 쪽은 운영에서 닿지 않고 PBT만 닿는다) | 순수 도우미 하나(`region_rows(regions, stored)`)와 상수 `FRESH = FeedbackState(DEFAULT_DISTORTION_DEGREE, 0.0)`를 함께 쓴다 |
| C13 | `play/event/suggest_context.py:117-126` `match_region` | 지역 이름 비교에 `casefold()`를 쓴다. 코드베이스의 이름 키는 `normalize_name`(소문자 + 공백 접기, BR-U2-4)이고, LLM이 돌려준 지역 이름을 맞추는 `reconciler`도 이것을 쓴다. 두 규칙은 'River  ton'(공백 둘)·'STRASSE'/'Straße'에서 답이 다르다 | `normalize_name`으로 비교하고, id 먼저·모호하면 버림 규칙은 그대로 둔다 |
| C14 | `play/gm/narrator.py:32·80`, `play/event/suggest_context.py:95` | 잘라 내는 방법이 셋이다. `cap(one_line(x), LINE_MAX)`는 `one_line(x, LINE_MAX)`와 늘 같고(무작위 5,000건), `deed_line`은 날 슬라이스로 자른다 | 한 줄 글은 `one_line(…, 상한)`으로 자르고, `cap`은 여러 줄 글(서술)에만 쓴다 |
| C15 | `web/src/ui/CommitRange.tsx:36` | `onMouseUp`이 `onPointerUp`과 겹친다. 마우스를 놓으면 둘 다 불리고, `saved` ref 덕분에만 한 번 저장된다. frontend §2.4는 onPointerUp이 onMouseUp을 대신한다고 적었다. #4를 고치며 ref를 성공 뒤로 옮기면 두 번 저장된다 | `onMouseUp`과 주석의 "mouse"를 지운다 |
| C16 | `web/src/api/http.ts:20-24`, `features/play/DialoguePanel.tsx:55·103`, `routes/EditorPage.tsx:88` | 오류 상태를 문자열로 가르는 곳이 넷이다. 409(`conflictKind`), 503, `includes("404")`, EditorPage의 409("Error: " 형태만 봄)다. `http()`는 이미 `res.status`를 안다 | `http()`가 `.status`를 가진 `HttpError`를 던지고, `statusOf(err)` 하나를 함께 쓴다(#12의 code 필드와 같이 다룬다) |
| C17 | `play/storage/postgres_repo.py:686` `seed_candidates` | SQL `trim()`은 공백(U+0020)만 지우고, 인메모리는 `str.strip()`으로 모든 공백 문자를 지운다. 탭·줄바꿈·NBSP·U+3000만 있는 retelling에서 두 어댑터의 답이 다르다. 지금은 `cap()`이 저장 전에 strip해서 생기지 않는다. 계약 테스트는 공백만 본다 | 저장할 때 한 번 정규화하고(검증기나 `save_appraisals`), 비교는 `retelling != ''`로 한다. 계약 테스트에 탭·줄바꿈·NBSP를 더한다 |
| C18 | `play/storage/schema.py:35-49` `UtcDateTime` | 읽을 때만 UTC를 붙이고 쓸 때는 바꾸지 않는다. SQLite에 +09:00 시각을 쓰면 벽시계 값이 저장되어 9시간 밀려 읽힌다. 지금은 쓰는 쪽이 모두 UTC라 생기지 않는다. U6 C16 테스트는 `tzinfo`가 있는지만 본다 | `process_bind_param`에서 `astimezone(timezone.utc)`로 바꾸고, +09:00 왕복 사례를 테스트에 더한다 |
| C19 | `web/src/ui/CommitRange.tsx:32-43` | `{...rest}`를 먼저 펼치고 자기 핸들러를 뒤에 둬서, 호출자가 준 `onBlur`·`onKeyUp`·`onPointerUp` 같은 핸들러가 소리 없이 버려진다. 타입은 이것을 받는다. 지금 호출자는 넘기지 않는다 | 호출자 핸들러를 먼저 부르거나, 그 이름들을 Props의 Omit에 더한다 |

테스트 적정성 메모(검증 없이 목록만):
- jsdom은 range 입력의 step 반올림을 하지 않아서 vitest로는 #1을 볼 수 없다. gm.test.tsx의 CommitRange 테스트도 step 위의 값(0.3, step 0.1)만 쓴다.
- gm.test.tsx의 지난 줄 fixture(`{approved, region_id, category}`, `{rumor_id, region_id}`)는 실제로 쓰인 적이 없는 모양이다(#10).
- TP-U7-6 생성기(`player_timelines`)에는 실패 복원이 없다(#5).
- 같은 세션에 GM 쓰기를 동시에 보내는 테스트가 없다. vitest는 API를 mock하고 pytest는 쓰기를 하나씩 보낸다(#2).
- CLI·API 두 조립 루트의 tuning 전달을 보는 테스트가 없고, `test_cli`에는 `world build` 사례가 없다(#3).
- `conflictKind`가 기대는 409 문장을 고정하는 백엔드 테스트가 없다. 문구를 바꾸는 변이에도 730개가 통과한다(#12).
- 승인 뒤 세계 상태·제안 프롬프트를 읽는 테스트가 없다(#13).
- NFR R-01 테스트(`test_gm_events.py:69`)의 `len(ctx) <= CONTEXT_MAX`는 이미 그 길이로 자른 뒤라 늘 참이다. 줄 수(40)는 보지만, 마지막 행적 줄 끝이 잘리는 것은 잡지 못한다(#14와 같은 자리).
- `tests/shared/test_config.py`의 자동 fixture `_clean_env`는 U5 키 여섯만 지운다. 그래서 U7 조정값 하나라도 셸에 export되어 있으면(예: 옛 env.example의 `RUMOR_HIGH_SUPPORT_THRESHOLD=0.6`) 기본값 테스트가 실패한다. U6 테스트도 같은 틈이 있다.
- 엔진이 쓰는 `neighbour_map`과 지역 이름 폴백 갈래는 변이를 넣어도 테스트가 잡지 못한다(C3·C4).

## 3. 상한으로 뺀 정확성 지적
검증을 통과했지만 상한(15) 밖으로 밀린 정확성 지적이다. 모두 심각도 low다.

| 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|
| `locus/shared/config/settings.py:184-186` `_tuning_is_consistent` | 지형 보정 표는 `if m < 0.0`만 검사한다. 그래서 `TOPOLOGY_TERRAIN_MODIFIERS={"mountain": NaN}`(Infinity, `1e400`도 같음)이 기동 검사를 지난다. `compute_weight`는 `clamp01(NaN)`=1.0을 돌려주어, 막힌 산길(0.2×0.4=0.08)이 가장 잘 통하는 연결(1.0)로 빌드되고, 다시 빌드할 때까지 남는다. BR-U7-20("범위 밖 값은 기동 때 실패")과 어긋난다. 기본 가중치 표와 ge·le 스칼라는 NaN을 거절한다. 운영자가 NaN이나 아주 큰 지수를 적어야 생긴다 | C | 두 표 필드를 `dict[str, FiniteFloat]`로 두거나 `not math.isfinite(m) or m < 0`을 검사한다. `test_br_u7_20_*`에 NaN·Infinity·`1e400`을 더한다 |
| `play/event/service.py:201-203` `suggest_events` | 제안 초안의 지역을 프롬프트에 보인 지역(최대 30곳) 안에서만 찾는다. U7 이전에는 월드의 모든 지역 id를 받았다(BR-P2-10). 그래서 31곳 이상인 월드에서는 실제 지역 id로 된 초안도 버려진다. 마을 35곳 월드에서, 최근 사건·행적 줄에 이름이 보이는 지역의 초안이 버려졌다. NFR §4의 의도된 변경 목록에도, code-summary §5에도 없다. 다만 FD 검토 R-06의 "잎 지역이 제안 대상에서 빠진다"는 보인 지역을 제안 대상으로 본 것으로 읽힐 수도 있다 | C | 초안의 지역은 월드 기준으로 확인한다(id는 `regions_by_id`, 이름은 모든 brief에서 같은 모호성 규칙으로). 아니면 최근 사건·행적 줄에 지역 id를 함께 싣는다 |
| `web/src/routes/PlayPage.tsx:212-216` `act` | 행동을 누르고 POST가 끝나기 전에 "GM 모드"(U7 버튼, 또는 예전부터 있던 AppNav의 GM 링크)로 떠나면, 이미 언마운트된 PlayPage가 실행이 끝날 때까지 `getTurnRun`을 폴링한다. 정리(cleanup)가 genRef를 올린 뒤에 `act`가 깨어나, 올라간 값으로 `poll`을 시작하기 때문이다. 실행 중에 플레이로 돌아오면 폴러가 둘이 된다. frontend §2.1은 "폴링은 언마운트 때 멈춘다"고 적었다. 화면에 보이는 문제는 없고 요청만 더 나간다(pollMs=5에서 200ms에 37회, 기본은 700ms 간격) | C | `act`가 첫 await 전에 `gen`을 잡아 두고, await마다 `genRef.current !== gen`이면 그만두며, `poll`에 그 `gen`을 넘긴다 |
| `api/schemas.py:38-43` `DistortionUpdate`·`SupportUpdate`, `play/distortion_service.py:51`, `play/rumor/service.py:192` | GM 쓰기의 값 필드가 NaN·Infinity를 막지 않는다. `clamp01(NaN)`은 1.0이라서 `{"degree": NaN}`(문자열 `"nan"`도 같음)은 200을 받고 왜곡도 1.0을 저장한다. 지지도는 1.0이 되어 다음 턴에 승격된다. `EventCreate.magnitude`도 같다. U7 이전부터 있던 줄이지만 U7이 다시 쓴 함수 안에 있다. 화면은 이 값을 보낼 수 없다(`JSON.stringify(NaN)`은 null이라 422) | C | 세 필드에 `Field(allow_inf_nan=False)`를 붙인다. NaN·Infinity는 422가 되고, 범위 밖 유한값은 지금처럼 clamp된다 |
| `web/src/features/gm/PlayerStrip.tsx:31-33` | `getPlayer`의 어떤 오류든(500, 네트워크) "플레이어 없음"(404)으로 다룬다. 그래서 띠, 플레이로 돌아가기 버튼, 지도 표시가 오류 없이 사라진다. frontend §2.1은 404일 때만 그리지 않게 한다 | C | 404만 "플레이어 없음"으로 본다. 다른 오류는 마지막 플레이어를 두고 한 줄 오류를 보인다 |
| `locus/shared/config/settings.py:105-110·212`, `world/topology/weights.py:22`, `world/topology/builder.py:24-28` | `TOPOLOGY_DEFAULT_BASE`는 어떤 경우에도 쓰이지 않는다. 검증은 모르는 연결 종류를 거절하고, `world_tuning()`은 표를 기본 네 종류 위에 합치며, 토폴로지 빌더는 모르는 종류를 `adjacent`로 바꾼 뒤 가중치를 구한다. 그래서 `base_weights.get(kind, default_base)`의 기본값 갈래에 닿지 않는다(`TOPOLOGY_DEFAULT_BASE=0.1`에서 'teleport'·None·'ROUTE'·'portal'이 모두 0.8). U3 때부터 쓰이지 않던 값을 U7이 env 노브로 문서화했다 | C | 노브와 `WorldTuning.default_base`를 없애고 문서를 고치거나, 빌더가 종류를 바꾸기 전에 가중치를 구하게 한다(U3 동작이 바뀌므로 U3에서 정한다) |
| `play/event/suggest_context.py:46-58` `pick_brief_regions` | 순위가 없는 단계(TERRAIN)가 깊이 99로 마을·구역보다 앞에 온다. 잎과 부모를 가르지 않아서, 부모 마을이 잎 마을 사이에 끼고 잎인 province는 모든 마을 뒤로 간다. 코드 플랜 FD R-06("④ 나머지 잎 지역, 깊은 것 먼저 ⑤ 상위 지역")과 operations.md의 "leaves before parents"는 엄격한 계층에서만 맞는다 | C | 잎 여부(부모 id 집합)를 넘기고 (부모 여부, −경로 길이, 이름)으로 정렬한다. 순위 없는 단계에는 경로 길이를 깊이로 준다 |
| `play/turn/advancer.py:875`, `play/deeds/service.py:335-341` | `rumor_spread` 줄의 summary만 아직 지역 id로 쓴다("rumor spread a -> b"). 페이로드에는 이름이 있다. BR-U7-17은 U7 뒤 지역 줄의 summary도 이름으로 쓰라고 한다. `deed_voided`도 `region_ids`만 있고 이름이 없다. 화면은 템플릿을 써서 API 원문에만 보인다 | C | summary를 `names.get(...)`로 쓴다. `deed_voided`에 이름을 더하거나 BR-U7-17의 범위를 domain-entities §2.2의 종류로 좁힌다 |
| `web/src/features/play/ActionBar.tsx:7·33` `EDGE_SPACE` | 서버 `str.strip()`에 맞추려고 넣은 정규식의 뒤쪽 갈래(`[…]+$`)가 글 안쪽의 긴 공백 덩어리에서 제곱 시간으로 되짚는다. 이 식은 키 입력마다 돈다(40k 공백이면 렌더 2.8s, 다음 키 2.0s). U7 이전에는 선형인 `trim()`이었다. 플레이어 자신의 붙여넣기로만 생긴다 | C | 뒤쪽 갈래를 lookbehind로 선형으로 만든다(`(?<![…])[…]+$`, 40k에서 0.43ms). textarea에 넉넉한 maxLength를 준다 |
| `play/event/suggest_context.py:70·118-120` | 64자(`ID_MAX`)보다 긴 지역 id를 잘라 보이고, 초안은 전체 id로만 맞춰 본다. 시스템 문이 "콜론 앞의 id를 쓰라"고 하므로 그런 지역의 초안은 버려진다. 같은 월드 id로 들여온 손작성 World File에서만 생긴다(빌더 id는 36자) | C | id는 자르지 않는다. 아니면 보인 id도 유일할 때 받는다 |
| `play/event/suggester.py:52`, `play/event/service.py:192` | `if not context`는 머리말이 늘 있어 참이 되지 않는다. 지역이 0개인 월드(에디터로 지역을 모두 지운 열린 세션)에서도 제안이 LLM을 1회 부르고 [] 를 돌려준다. U7 이전에는 지역 id가 없으면 부르지 않았다 | C | `suggest_events`에서 `shown`이 비면 LLM 전에 []를 돌려주고, 죽은 갈래를 지운다 |
| `locus/play/npc/dialogue.py:167-173` `say` | BR-U7-27의 try가 프롬프트 만들기까지 감싼다. 프롬프트를 만들다 버그가 나면 "다시 말해 보세요" 503이 된다. U6 #9가 `_narrate`에서 고친 것과 같은 꼴이다. 다만 지금은 검증된 모델만 들어가서 실제 계기가 없다(무작위 400건에서 예외 없음) | P | 두 문자열을 try 앞에서 만들고 `self._llm.complete(...)`만 감싼다. 판단·서술도 같게 맞춘다 |

## 4. 기각
| 위치 | 지적 | 기각 이유 |
|---|---|---|
| `play/rumor/feedback.py:85` | `feedback_restored_regions`가 몫만 줄고 왜곡도는 그대로인 지역도 싣는다(BLM §1.2는 `restored > 0`) | domain-entities §2.2가 이 키를 "이번 턴 몫을 되돌린 지역 id"로 정의하고, 코드는 그대로다. 읽는 곳은 ADVANCE_TURN 페이로드뿐이고 화면은 이 목록을 보이지 않는다. 남는 것은 BLM §1.2와 domain-entities의 문구 차이다 |
| `play/rumor/dynamics.py` `step_feedback` | 낮춘 `RUMOR_FEEDBACK_CAP`보다 큰 몫이 강한 소문이 있는 동안 줄지 않는다(TP-U7-1 "어떤 입력에서도 share' ≤ cap") | BLM §1.3 그대로다(`room = max(0, cap − share)`). 운영자가 열린 세션 중에 상한을 낮춰야 생기고, 강한 소문이 사라지면 restore로 준다. TP-U7-1 생성기도 `share ≤ cap` 입력만 만든다 |
| `web/src/features/gm/PlayerStrip.tsx:45` | 배경 실행이 끝나도 "(진행 중)"과 턴이 낡은 채 남는다 | frontend §2.1:40·§5:129가 띠를 GM 쓰기·턴 진행 뒤에만 다시 읽게 정했다(폴링 없음) |
| `locus/play/world_state.py:86` | `/state`가 소문 수를 세려고 활성 소문 행 전체를 읽는다 | domain-entities §4·BLM §4.3·TP-U7-7이 정한 순수 집계 모양이다. 턴이 지역당 활성 소문을 20개로 묶어 세션 길이와 함께 늘지 않고, `/state` p95는 11ms다 |
| `api/routers/gm.py:197` | 왜곡도 PUT이 `next(...)`를 기본값 없이 써서 행이 없으면 500이다 | 서비스가 바로 앞에서 그 행을 썼고, 왜곡도 행은 지워지지 않는다 |
| `web/src/ui/CommitRange.tsx:36-37` | 마우스를 놓으면 pointerUp·mouseUp으로 두 번 저장한다 | `saved` ref가 두 번째를 막는다. 겹친 핸들러 자체는 정리 C15로 남겼다 |

## 5. 문서 정확도 메모
규약 각도에서 **인용할 수 있는 CLAUDE.md 규칙 위반은 없었다**.
- 경계 import는 `test_boundaries`가 통과하고, play → localization이나 `locus` → `api` import가 없다.
- 새 서비스(`WorldStateService`, `DistortionService(repo, snapshots)`, `EventService(..., tuning=)`)는 저장소·스냅샷·LLM을 생성자로 받는다(포트 뒤 I/O).
- `PlayContainer.world_state`가 `assemble_play`에서 조립되고, ruff/black(100)이 clean이다.
- 새 순수 함수(`step_feedback`·`region_feedback`·`player_log`·`summarize_state`·`one_line`)에 hypothesis 테스트가 있다.
- U7이 고친 CLAUDE.md 문장(테스트 수 730 + 90, 파일 배치, DeedService 문구)은 사실과 맞다.

사실과 다른 문장은 다른 곳에 있다.
- `operations.md:317·319`("마지막 사건 5개와 행적 5개를 싣는다", "글자 상한으로 21,000자 아래")는 `EVENT_SUGGEST_MAX_REGIONS` 기본값(30)에서만 맞다(#14).
- `env.example:70`·`tuning.py:50`은 `TOPOLOGY_DEFAULT_BASE`를 "표에 없는 연결 종류의 가중치"로 설명하고, `operations.md:346`은 새 env로 적는다. 이 값은 쓰이지 않는다(§3).
- env.example·operations.md와 code-summary §8("WorldTuning(가중치 표·dedup)은 env로만 바뀐다")은 월드 조정값이 빌드에 쓰인다고 적는다. CLI 빌드에는 맞지 않는다(#3).
- code-summary §4의 "U6 #10·#11 → DeedPanel"과 §5 8.7("지난 event_created 줄은 제안·승인 문구로 읽는다")은 #11·#10만큼 사실과 다르다.
- `locus/play/deeds/service.py:3`("The one place deeds and appraisals are written")과 `locus/play/wiring.py:100`("the one writer of deeds")은 U6 리뷰 문서 메모가 좁히라고 한 문장이다. 플랜 9.2는 CLAUDE.md만 고쳤다.
- frontend-components.md:113("`regenerate`는 `deactivated ?? deleted` 개수를 쓴다")과 달리, 재생성 템플릿은 U7 전후 모두 개수를 보이지 않는다. code-summary §5에 없다.
- X3 BR-X3-5의 〔U7 정정〕은 "지역별 listRumors(Q6=B)"를 그대로 두었다. 정리 C1을 고치면 이 문구도 함께 고친다.

설계 메모(결함으로 올리지 않음):
1. **GM 설정과 사건 기여**(P): GM이 왜곡도를 정하면 되먹임 몫은 지워진다(BR-U7-5 "그 값이 새 기준"). 그런데 이미 ACTIVE인 사건의 기여는 남는다. 그 사건을 해소하면 기여 전부를 빼서 GM이 정한 값 아래로 내려간다(0.3 → 전쟁 한 턴 0.6 → GM 0.5 → 해소 0.2). 지속 사건이면 설정 뒤에도 기여가 쌓여 더 벌어진다. BR-U7-5·BLM §1.4·domain-entities §1.1·P2 BR-P2-5 어디에도 이 경우가 없고, Phase 2부터 같았다(U7 회귀 아님). "새 기준"을 사건 기여에도 적용할지(같은 UoW에서 그 지역 기여를 지우고 `event_contributions_cleared`로 남김), 지금 동작을 BR-U7-5에 적고 왜곡도 패널에 보일지 정해야 한다.
2. **지역 없는 지난 줄**: U7 이전의 승격·강등·가지치기·지지도·해소 줄은 지역 id가 없다. 그래서 "승격: rm1"이 "소문 승격 · —"가 된다. BR-U7-17의 "이름이 없으면 id를 보인다"를 지킬 수 없는 줄이다. FR-D3이 화면에서 id를 빼려는 방향이므로, 요약으로 돌아갈지 "—"를 감수로 적을지 정한다.
3. **일괄 쓰기와 GM 리스**: U7 frontend §2.2는 전체 생성·재생성을 "`mapLimit` 5"로 정했고, U4 코드 리뷰 02 #7은 GM 쓰기를 세션 배타 리스로 바꿨다. 두 결정이 부딪힌다(#2). 어느 쪽을 바꿀지(GM끼리 리스 나누기, 또는 일괄을 하나씩)가 #2를 고치는 방식이다.
4. **GM 화면의 다시 읽기 폭**(설계가 받아들인 것): 지지도 슬라이더 저장 한 번이 요청 11개를 부른다(쓰기, GM 타임라인 전체 3,000줄·792KB, 사건·왜곡도·지역 소문, 세션·플레이어·실행, `/state`, 행적, 지역 지식). frontend §2.1·§2.2·§5가 정한 흐름이라 결함으로 올리지 않았다. U8 라이브 p95 측정에 넣을 만하다.

## 6. 확인한 것
| 검사 | 값 |
|---|---|
| U7이 바꾼 테스트 파일 24개 + `test_boundaries` | 385 passed |
| 전체 `pytest -q --no-cov` | 730 passed |
| `npx vitest run` | 90 passed (6 files) |
| `ruff check` / `black --check --line-length 100` (`locus api tests`) | clean |
| `npx tsc --noEmit` | clean |
| `mypy locus api` | 11 errors(기준선과 같음), U7이 바꾼 파일에는 0 |
| CLAUDE.md 테스트 수 | 730 + 90 = 820 일치 |
| 경계 import | `test_boundaries` 통과. `shared/text.py`는 `re`만, `event/suggest_context.py`는 shared만 import한다. play → localization, `locus` → `api` import는 없다 |
| 턴 엔진 수학 | `step_feedback`이 BLM §1.3과 같다. 올림은 clamp 뒤 실제 증가분만 몫에 더하고, 복원은 왜곡도가 0에 닿아도 몫을 `restore`만큼 줄이며, delta가 있는 지역은 그 턴에 복원하지 않는다. 저장 순서는 사건 쓰기(몫 유지) → 초안·행적 소문 → 되먹임(같은 UoW에서 읽음) → 강화·감쇠(사건 영향 지역만 면제) → 가지치기 → 승격 → 일괄 저장 → 턴이다. 사건·되먹임·clamp가 섞여도 "왜곡도 − 기준 = Σ사건 기여 + 몫"이 유지된다(두 각도가 따로 추적) |
| 사건 생애 | one_shot 자동 해소가 `event_resolved`(지역 id·이름)를 남긴다. 폐기 줄은 같은 UoW에서 행보다 먼저 쓴다. SUGGESTED 해소는 400, `n` 검사는 LLM 호출 전이다 |
| U6 이월 | #8(가드 뒤 세션 다시 읽기), #9(장면을 try 밖에서), #14(선언 규칙을 `validate_action`으로), C3·C4(원점별 메모: 도달 지도는 원점과 그래프에만 달려 부모 사이에 나눠 써도 같다), C7·C9·C10·C11·C12·C16, 장면 원본 가리기가 플랜대로다 |
| 어댑터 동등성 | `feedback_share`(None이면 유지, 새 행은 0), UoW 롤백의 몫 복원, `message_counts`(메시지 0개 대화는 0, 세션 격리), `list_deeds`(kind·deed_ids·newest_first·limit·voided, limit 전에 거름), `seed_candidates` 순서·필터가 두 어댑터에서 같다. `uow()` 블록 안에서 `self._repo`를 부르는 곳이 없다(AST 검사) |
| 스키마 이관 | U7 이전 모양의 `region_distortions`에 `ensure_schema`를 두 번 돌려 열이 생기고 멱등이다. 옛 행의 몫은 0이다. play 시각 열 11개가 모두 `UtcDateTime`이다 |
| 기동 검증 | `Settings`가 `assemble_shared`의 `_step` 밖에서 만들어져 잘못된 env는 lifespan을 멈춘다. `.env` 두 값만으로 부팅된다. 깨진 JSON, 모르는 연결 종류, [0,1] 밖 값, `hearsay_min > propagate_min`은 거절된다(NaN 지형 보정은 예외, #K25) |
| 프롬프트 한 줄화 | NPC 대화·판단, GM 서술(폴백 기록 포함), 소문 왜곡, 사건 제안 프롬프트의 자유 글 삽입이 모두 `one_line`을 지난다. 번역 프롬프트는 글이 마지막 구역이라 R-03 범위 밖이다 |
| 웹 data-testid | 옛 SessionPanel의 data-testid가 모두 같은 요소에 있다. `event-form`은 `gm-region` 밖으로 옮겨졌지만 그 위치를 보는 테스트는 없다 |
| i18n | ko·en 키 집합이 같다(`en: Record<Key, string>`). U7이 쓰는 페이로드는 U7 템플릿의 보간 필드를 모두 갖는다(지난 줄은 #K6). U7이 더한 키 중 쓰이지 않는 것은 없다 |
| `conflictKind` | 실제 409 본문(`Error: 409 Conflict: {"detail":"session is closed: …"}` / `turn in progress: …`)과 맞는다 |

## 7. 남은 결정 (사람이 고른다)
원하시는 것: 세계관 자료로 만든 월드에서 소문과 사건이 지형을 따라 퍼지는 솔로 TRPG를 하면서, GM 모드로 월드를 보고 조정하는 것.
지금 하는 것: 승인된 U7 코드의 리뷰를 마쳤습니다(코드는 고치지 않음). 이 질문은 찾은 결함을 언제 고칠지를 정합니다.

U7 코드는 승인됐다(83022bf). 아래 지적을 고치면 **승인된 코드를 바꾸게 된다**. 세션은 지금 U3 월드 에디터 기능 설계 Part 1에 있다(Q1·Q2 답함, Q3·Q4를 묻는 중).
- 지금 아는 것: 정확성 지적 15건이 모두 재현으로 확인됐다.
  - #1: GM이 슬라이더를 Tab으로 지나가거나 손잡이를 누르기만 해도, 고르지 않은 값이 저장된다. 왜곡도라면 되먹임 몫까지 지워져 월드가 영구히 바뀐다. vitest(jsdom)로는 볼 수 없다.
  - #2: "전체 생성"·"전체 재생성"이 다섯 지역 중 한 지역만 처리한다. U4부터 그랬고 U7이 그대로 옮겼다.
  - #3: CLI로 빌드한 월드가 U7의 월드 조정값을 무시한다. 잘못된 가중치가 그래프에 저장된다.
  - #4·#5: GM 슬라이더가 거절된 저장을 다시 보내지 않는다. 실패한 이동 뒤에는 플레이어 로그가 엉뚱한 지역을 보인다. 각각 BR-U7-24와 BR-U7-12를 어긴다.
  - 나머지는 낮음이다. #11은 한 줄로 고친다.
- 왜 지금 정하나: U3 FD 플랜의 이월 목록이 지금 쓰인다. 여기 올리지 않으면 U3 설계가 이 항목 없이 굳는다. U3와 겹치는 것이 둘 있다.
  - #3과 §3의 `TOPOLOGY_DEFAULT_BASE`는 U3의 월드 빌드·연결 가중치와 같은 자리다.
  - #1의 "실제로 바꿨을 때만 저장"은 U3 플랜이 지도 편집(B7, "누르기만 해도 위치가 저장된다")에 세운 원칙과 같다.
- 이 답에 기대는 것: U7 후속 커밋을 할지, U3 FD 플랜 이월 목록의 범위, U8 라이브 시나리오(GM 왕복·슬라이더·전체 생성).

선택지와 결과:
- **A. (권장) 섞는다. 저장 값·빌드 결과·로그를 틀리게 만들거나 기능을 못 쓰게 하는 #1~#5와 한 줄로 고치는 #11은 지금 U7 후속 커밋으로 고치고, 나머지는 U3 FD 플랜 이월 목록에 올린다.**
  - 까닭: #1·#3은 고칠 때까지 만들어지는 세션과 월드에 틀린 값을 남긴다. #2는 GM의 주요 버튼을 못 쓰게 한다. 셋 다 U8 데모 전에 남기면 데모가 같은 결함을 보인다.
  - 결과: 고칠 것은 다음과 같다.
    - `CommitRange`: 바꿨을 때만 저장, 성공했을 때만 `saved`, 왜곡도 패널에 `key`
    - GM 리스: GM 쓰기끼리 나누고 턴만 배타로 두거나, 일괄을 하나씩 보낸다(어느 쪽인지는 고치면서 정함, §5 설계 메모 3)
    - `__main__.py`: `tuning` 전달, `from_factory`의 필수 인자
    - TURN_RUN_FAILED의 `restored_region_id`와 `player_log`의 위치 갱신
    - `onDeedChanged`의 `loadSession()`
  - 테스트: vitest 3~4개(브라우저 step 반올림 흉내 포함), 동시 GM 쓰기 pytest 하나, `test_cli` 사례 하나, 실패한 이동의 EX 하나를 더한다. 게이트(pytest·vitest·ruff·black·tsc)를 다시 돈다. BR-U7-13에 실패 복원을 한 줄 더한다.
  - 비용·위험: 승인된 U7 코드를 다시 연다(audit에 후속 수정으로 남긴다). U3 Q3·Q4 진행이 그만큼 늦어진다.
  - 되돌리기: 커밋 단위라 쉽다.
- **B. 전부 U3로 넘긴다.**
  - 결과: U7 코드는 그대로 두고, 정확성 지적 15건·§3 12건·정리 19건을 U3 FD 플랜 이월 목록에 올린다. #3과 `TOPOLOGY_DEFAULT_BASE`는 U3의 빌드·가중치 작업과 한 번에 고칠 수 있다.
  - 비용·위험: U3가 끝날 때까지 #1·#2가 남는다. 그사이 GM 모드로 돌린 세션에 저장된 왜곡도·지지도는 되돌릴 수 없고, 전체 생성은 여러 번 눌러야 한다. U3 범위가 커진다.
  - 되돌리기: 쉽다(목록 문서만 바뀐다).
- **C. 감수 위험으로 기록하고 진행한다.**
  - 결과: operations.md "Accepted risks"에 적고 고치지 않는다.
  - 비용·위험: #1은 BR-U7-24("같은 값이면 보내지 않는다")가 막으려던 쓰기를 오히려 만든다. US-5.3(조정·슬라이더)의 수용 기준이 실제 브라우저에서 깨지고, 회귀 테스트로도 막히지 않는다. #2는 BR-U7-25("기존 기능은 모두 남는다")를 어긴 채 남는다.
  - 되돌리기: 나중에 고칠 수 있지만, 그사이 저장된 값은 남는다.
- X. Other (please specify)

어느 쪽을 고르든 설계 결정 둘은 따로 남는다. 하나는 GM 설정과 이미 ACTIVE인 사건 기여의 관계(§5 설계 메모 1)이고, 다른 하나는 `TOPOLOGY_DEFAULT_BASE`를 없앨지 의미를 줄지(§3)다. 둘 다 U3 FD에서 정하면 된다.
