# V5 GM 쓰기 정확성 — Code Review 01

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**이 리뷰가 하는 것**: 승인된 V5 코드가 승인된 설계(BR-V5-*, BLM § 1~7, 코드 플랜 § 1 실행 메모)를 지키는지 결함 위주로 확인한다. 범위는 `git diff efe78c9..8352812 -- locus api tests`다. 새 시험이 주장대로 잡는지도 본다. 코드는 고치지 않았다(리뷰 전용).

**방법**: V2~V4 리뷰와 같은 방식이다.
- 네 각도를 병렬로 돌렸다.
  - guard와 잠금(잠금 차례, 교착, 닫기·교체, 공유 guard, 409 문장)
  - GM 쓰기 서비스(구간 안의 새로 읽기, 행과 줄, 응답 계약)
  - 턴 엔진(재시작 보상, 지운 지역의 사건, 운영 문서)
  - 시험의 힘(돌연변이 40개), 받침, HTTP 계약
- 재현물은 세션 scratchpad의 `v5review/{guard,services,turns,tests}/`에만 두었다. 저장소 파일은 바꾸지 않았다(각도마다 `git status`로 확인).
- 이 세션이 상위 후보의 코드 자리를 다시 읽고 돌려 확인했다.
  - `GM_WRITE_WAIT_S=inf`를 설정이 받고, `RLock.acquire(timeout=inf 또는 1e12)`가 `OverflowError`를 낸다.
  - `advancer.py:993`의 `out.influenced_regions |= set(restored)`가 `:711-715`의 `evolve_support`·`reinforced`로 들어간다.
  - `base.py:84`·`write_section.py:56`·`dialogue.py:316`의 문장이 세션 id를 싣는다.
- 판정: **C** = 재현했거나 코드로 기제가 확정됨. **P** = 기제는 실재하지만 이번에 직접 돌리지 못한 조건에 달림.
- 두 각도 이상이 같은 것을 찾은 경우는 하나로 합쳤다.

## 1. 지적 — medium

| # | 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|---|
| 1 | `advancer.py:993`, `:711-721` | **지운 지역의 사건이 끝나는 턴에 이웃 소문이 덤으로 힘을 얻는다.** 되돌린 이웃을 `influenced_regions`에 넣었는데, 이 집합은 행 저장만이 아니라 지지도 강화(`evolve_support`, +`event_support_reinforce`)와 감쇠 면제에도 쓰인다. 재현: x–y 세계, x의 지속 전쟁 한 번 적용, y 소문 지지도 0.5, x 삭제. 턴의 자동 해소는 지지도 0.60으로 승격선 0.6에 닿아 **승격**된다. GM 해소 뒤 턴은 0.45, 승격 없음. BLM § 6 "GM이 해소한 뒤 턴을 돌린 것과 같은 결과"가 깨진다. 코드 플랜 § 1.1 R-04는 "(그 행만 저장)"이었다 | C | `_EventApplication`에 `restored_regions`를 따로 둔다. 저장 단계는 `influenced_regions ∪ restored_regions`의 행을 쓰고, 강화·감쇠 면제는 적용된 사건의 `influenced_regions`만 쓴다. TP-V5-6에 "이웃 소문의 지지도·승격이 GM 해소 뒤 턴과 같다"를 더한다 |
| 2 | `test_v5_overlap.py:298-301`, `wiring.py:105,108,143` | **공유 guard 연결을 사건 서비스만 확인한다.** 소문·행적·왜곡도 서비스의 `guard=guard`를 빼도 1119개가 모두 통과한다. 그러면 SQL에서 지지도 조정과 취소가 겹칠 때 취소된 소문이 되살아나고(RE-P01 복귀), 닫기가 소문·행적 저장을 기다리지 않는다 | C(돌연변이) | 다섯 서비스(`sessions` 포함)가 `gm.guard`를 쓰는지 단언한다. 행동 시험도 둔다: `gm.guard.short_write(s)`를 쥔 채 조정·취소·왜곡도 설정·사건 만들기가 상한 뒤 `GmBusyError` |
| 3 | `test_v5_overlap.py:133-149`, `event/service.py:158` | **같은 사건의 해소 둘이 시험되지 않는다.** BR-V5-05의 "이미 해소된 사건의 해소는 그대로, 줄 없음"을 지키는 것은 구간 안의 `if fresh.is_resolved()` 하나인데, 지워도 통과한다. 두 번 누름이면 복원이 두 번 들어간다(0.3 → 0.15, 줄 둘, 두 저장소) | C(돌연변이) | TP-V5-1에 같은 사건 해소 둘(끼워 넣기 문 `get_event`)을 더한다: 한 번만 복원, 줄 하나 |
| 4 | `api/errors.py` `PLAY_ERRORS`, `api/routers/gm.py:169-180` | **`rumor_inactive`의 HTTP 시험이 없다.** `PLAY_ERRORS`에서 `RumorInactiveError`를 빼도 통과하고, 그러면 지지도 PUT이 500이 된다 | C(돌연변이) | API 시험 하나: 소문을 끈 뒤 PUT `/support` → 409 `rumor_inactive` |

## 2. 지적 — low

### 2.1 코드

| # | 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|---|
| 5 | `settings.py:131`, `guard.py:108` | `GM_WRITE_WAIT_S`에 위 한계가 없다. `inf`·`1e12`면 `OverflowError`로 모든 GM 쓰기와 닫기가 500이고, 확인한 월드 교체는 월드를 바꾼 뒤 500이 된다(세션 열린 채, 보고서·번역 정리 빠짐). 운영자의 "끝없이 기다림" 설정에서 난다 | C | 설정에 `le=600`, `short_write`에서 `min(t, threading.TIMEOUT_MAX)`로 자른다 |
| 6 | `base.py:84`, `write_section.py:56`, `dialogue.py:316` | 닫힌 세션에 대한 플레이어 409 `session_closed` 문장이 세션 id를 싣는다(`session is closed: <sid>`). BR-V5-23은 "문장에 세션 id 없음", domain-entities § 2 표는 이 문장을 "그대로"라 적어 서로 어긋난다. 닫는 중(guard 상수)만 고쳐졌다 | C | 문장을 "the session is closed"로 바꾸고(GM 경로도 같이), domain-entities § 2를 고친다. TP-V5-14의 닫힌 뒤 응답에 `_clean`을 건다 |
| 7 | `seeds.py:57-72` → `event/service.py:96-97` | 씨앗 시작이 짧은 쓰기를 쥔 채 `_require_open`과 `require_region` → `snapshots.get()`을 한다. `WorldCache`는 맞을 때마다 Neo4j 판 표시를 묻고, 판이 바뀌었으면 월드를 다시 읽는다. BLM § 1은 월드 읽기를 구간 밖에 둔다. 느리면 같은 세션의 다른 GM 저장·닫기가 `gm_busy`를 받는다. 닫힌 세션에 진행 중 씨앗이면 `session_closed` 대신 `seed_running`이 나온다 | C | 씨앗의 지역·이름을 잠금 전에 구한다. `create_event`의 안쪽 형태 `_create_in(u, session, …)`를 두고, 씨앗은 `section.open` 하나 안에서 `u.events`로 진행 중을 보고 만든다(다시 들어감이 필요 없어진다) |
| 8 | `event/service.py:249-252` | `suggest_events`가 맞는 초안이 없으면(LLM 실패 포함) 구간에 들어가지 않고 `[]`를 돌려준다. LLM 중에 세션이 닫히면 409가 아니라 200 `[]`다(BLM § 2 제안 줄과 다름). 쓰는 것은 없다 | C | 맞는 초안이 없어도 열림을 확인한다(`section.open`에 들어가 아무것도 쓰지 않음) |
| 9 | `event/service.py:294-302` | 승인이 **모든** ACTIVE 사건에 200(줄 없음)을 준다. GM이 직접 만든 사건이나 시작한 씨앗처럼 제안이었던 적 없는 사건도 그렇다. 전에는 400이었다. BR-V5-07의 뜻은 "그사이 승인됨"이다 | C | 출처가 `llm:event`인 ACTIVE만 그대로 돌려주고, 그 밖의 ACTIVE는 400을 유지한다 |
| 10 | `guard.py:43,107` | 세션별 짧은 쓰기 잠금 `_writes`가 지워지지 않는다. 프로세스가 사는 동안 쓴 세션 수만큼 늘어난다 | C | 닫기가 끝나면 그 세션의 항목을 지운다(닫힌 세션의 구간은 모두 `session_closed`로 끝나므로 남은 대기자가 있어도 아무것도 쓰지 않는다) |
| 11 | `advancer.py:524`, `:604-609` | 한 세션에 `running` run이 둘 남으면(턴 안에서 저장과 실패 기록이 모두 실패, 또는 시작 때 저장소가 안 닿아 복구를 건너뜀) 복구가 오래된 것부터, 지금 세션 턴으로 넘어간 턴을 센다. 이동 둘이 모두 되돌려져야 할 때 플레이어가 a가 아니라 b에 남고, 오래된 run에 뒤 run의 턴이 붙는다(청구 합은 맞다) | C(기제)/P(조건) | 세션에 `running` run이 둘 이상이면 가장 최근 것만 보상하고, 나머지는 `interrupted_uncompensated`로 표시해 운영자에게 넘긴다. operations.md에 적는다 |
| 12 | `advancer.py:526` → `_compensate` | 턴을 모두 마친 뒤 `_finish` 전에 끊긴 run이 `failed`로 복구되고, 플레이어 기록에 "턴 처리 실패" 줄이 남는다(넘어간 턴 = 비용, 환불 0). V5 전에는 줄이 없었다 | P | 넘어간 턴이 비용과 같으면 되돌릴 것이 없으니 줄을 쓰지 않는다. run은 `failed`/`interrupted`로 표시만 한다 |
| 13 | `api/main.py:121-125`, `advancer.py:513-524` | 복구가 guard를 보지 않는다. 이미 돌고 있는 컨테이너를 주입한 두 번째 앱(시험 등)이 시작되면, 돌고 있는 턴의 run을 보상해 버린다. 운영(워커 하나)에서는 닿지 않는다 | P | `guard.turn_running(run.session_id)`인 run은 건너뛴다 |
| 14 | `memory_repo.py:384-392` | `datetime.min.replace(...)`를 썼다(모듈에 `_EPOCH`가 있다). `started_at`이 None이면 메모리는 앞, PostgreSQL은 뒤다(지금은 늘 채워져 닿지 않음) | C | `_EPOCH`를 쓴다 |
| 15 | `turn/executor.py:7-8`, operations.md "Region delete" V5 줄, BLM § 6 | 실행기 독스트링이 아직 "다음 시작이 run을 interrupted로 표시한다"고 말한다. 운영 문서와 BLM의 "GM 해소와 같다"는 #1이 고쳐져야 맞다 | C | 독스트링을 고친다. #1을 고친다 |

### 2.2 시험

| # | 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|---|
| 16 | `event/service.py:303-304` | 승인의 "그사이 해소됨 → 400"이 시험되지 않는다. 지우면 해소된 사건이 다시 ACTIVE가 되고 승인 줄이 하나 더 생긴다 | C(돌연변이) | TP-V5-9에 셋째 경우(승인의 첫 읽기와 구간 사이에 승인·해소)를 더한다 |
| 17 | `event/service.py:160` | 해소가 구간 안의 사건으로 복원한다는 것(U3 #10)이 시험되지 않는다. `event = fresh`를 지우면, 해소의 첫 읽기와 구간 사이의 GM 설정 0.7이 0.55로 무너진다 | C(돌연변이) | `_after_first_read(get_event)` 사이에 `set_region_distortion`을 넣는 시험 |
| 18 | `test_v5_turns.py:205-217` | TP-V5-6의 GM 해소 받침에서 지운 x에 왜곡도 행이 없다. `present`를 세션의 행에서 만드는 돌연변이가 통과한다(x에 행이 있으면 0.5 → 0.3으로 고쳐 씀) | C(돌연변이) | x에 행(0.5)을 두고 그대로인지 단언한다 |
| 19 | `test_v5_overlap.py:391-423` | "생성과 재생성" 시험이 나중에 저장된 쪽에 맞춰 기대값을 정해, 옛 코드(버릴 것을 초안 전에 고름)를 16번 중 6번만 잡는다 | C(돌연변이 8회) | 차례를 정해 두 번 돌린다(생성 먼저 저장, 재생성 먼저 저장) |
| 20 | `test_v5_overlap.py:236-259`, `:427-444` | TP-V5-12가 "줄 실패 → 행 없음" 한 방향만 본다. 줄을 따로의 트랜잭션으로 쓰는 돌연변이가 지지도 조정에서 통과한다. `pytest.raises(RuntimeError)`에 `match`가 없고 `failing.raised`를 보지 않아, 다른 `RuntimeError`(`GmBusyError`·`SessionClosedError`도 그 자식)로 실패해도 통과한다 | C(돌연변이) | `match="timeline write failed"`, `failing.raised == N`을 단언한다 |
| 21 | `write_section.py:50-51` | 잠금 차례(짧은 쓰기 → 작업 단위)가 시험되지 않는다. 바꾸면 인메모리에서 씨앗 시작과 해소가 겹칠 때 해소가 엉뚱한 `gm_busy`를 받는다 | C(돌연변이) | 그 재현을 시험으로 둔다 |
| 22 | `test_v5_overlap.py:511-514` | TP-V5-10의 돌려준 행 단언이 느슨하다(`in (0.4, 0.6)`). 구간 뒤 저장소를 다시 읽는 돌연변이가 통과한다 | C(돌연변이) | `out[0]` 0.4, `out[1]` 0.6을 단언한다 |
| 23 | `concurrency.py:108-146` | `InterleaveGate.met`가 독스트링("둘이 함께 안에 있었다")과 다르다. 첫째가 시간 초과로 나간 뒤 둘째가 와도 참이 된다. 겹침 시험은 문을 단언하지 않아, 잠금이 차례를 세웠다는 증거가 없다 | C | `met`은 첫째가 기다리는 동안 둘째가 왔을 때만 참으로 둔다. 고친 코드의 시험에서 `not gate.met`을 단언한다 |
| 24 | `test_guard_machine.py:104-107` | 불변식 `a_turn_is_alone`이 모형 자신만 본다(guard를 보지 않아 깨질 수 없다) | P | 지우거나 guard를 보게 고친다(`turn_running`이면 `not gm_busy`) |
| 25 | `test_v5_overlap.py:344`, `:381` | 스레드가 죽어 결과가 비어도 `all(...)`이 참이 되는 곳이 있다 | P | `not t.is_alive()`와 결과 개수를 단언한다 |

## 3. V6로 넘김 (화면)

- 플레이어 행동의 409 `gm_busy`가 "턴이 진행 중입니다" 알림으로 나온다(`useTurnRun.ts:168`, `conflictKind`가 busy로 묶음). GM 작업 중 문장을 따로 둔다.
- GM 허브는 `rumor_inactive`·GM 쪽 `gm_busy`에서 원문 `String(e)`를 보이고(`GmHub.tsx:115-120`), `rumor_inactive` 뒤에 다시 읽지 않아 꺼진 소문이 활성으로 남아 보인다. `describeError`에 `error.gm_busy`·`error.rumor_inactive` 키가 없다.
- code-summary § 7의 문장 셋(`rumor_inactive`, `region_removed`, `gm_busy`)에 "`rumor_inactive` 뒤 다시 읽기"를 더한다.

## 4. 받아들이는 것 (알려진 한계로 적음)

- 닫는 중에 턴을 시작하면 409 `session_closed`(BR-V5-16)인데, 그 닫기가 상한을 넘겨 `gm_busy`로 실패하면 세션은 열린 채다. 플레이어는 이미 "닫혔다"를 받았다. 창은 GM 저장 구간이 멈췄을 때의 상한(5초)뿐이다. 승인된 규칙이라 그대로 두고 code-summary § 6에 적는다.
- 인메모리 작업 단위가 저장소 전체를 잠가, 짧은 쓰기를 빈 블록으로 바꿔도 인메모리 변형의 TP-V5-3(취소 둘)·9·10·11은 통과한다. 구간 자체는 SQL 변형이 지킨다(NFR § 2.3대로).

## 5. 확인한 것 (문제 없음)

- 잠금 차례는 모든 호출에서 리스 → 짧은 쓰기 → 작업 단위다. 구간 안에서 둘째 작업 단위를 열거나 구간 있는 서비스를 부르는 곳이 없다. guard의 `_lock`을 쥔 채 RLock을 기다리는 곳이 없다. `acquire`·`hold`·`closing`은 한 잠금 아래 원자적이다.
- 공유 guard 하나가 세션·사건·소문·행적·왜곡도·턴에 들어간다(시험만 약함, #2). 닫힌 뒤 GM 쓰기가 저장되는 경로가 없다.
- 구간 안의 새로 읽기와 조건 확인이 BLM § 2와 맞는다. 바깥 읽기의 낡은 사본을 되쓰는 곳이 없다. LLM은 늘 밖이다. 행과 줄은 한 작업 단위다. 재생성 번역 정리는 구간 안에서 고른 `deactivated_ids`를 쓴다.
- 보상 계산(환불, 0턴일 때만 위치·행적 되돌림, 세션이 있을 때만 줄), 보상 실패 뒤 메모리·SQL 되돌림, 표시마저 실패할 때 `running` 유지, lifespan 차례(요청 전), `fail_stale_runs` 잔재 없음, `list_running_runs`(두 어댑터).
- 지운 지역 사건: 있는 지역만 복원, 산 사건보다 먼저, `resolved_turn`, 적용·대상·사건 지역에 넣지 않음, 다음 턴에 다시 해소 안 함, GM 해소도 같은 거름.
- 오류 표 차례, 409 본문 `{detail, code}`, `RegionViewOut.gm_busy`, `types.ts`.
- 돌연변이 40개 가운데 code-summary § 3이 주장한 것은 모두 잡혔다. 흔들림: 연속 6회, 순서 뒤집기, 병렬 16·24회(CPU 부하 8개 곁)에서 실패 없음.

## 6. 처분

- 사람의 선택(2026-10-08): **A. 전부 고침**.
- 고침: `3995e86`(코드와 시험 한 커밋). medium 4건과 low 21건 모두.
  - 코드: #1 `restored_regions`를 따로 둠 · #5 `le=600`과 `TIMEOUT_MAX`로 자름 · #6 `SESSION_CLOSED` 문장 · #7 `EventService.create_in`, 씨앗은 구간 하나 · #8 맞는 초안이 없어도 열림 확인 · #9 승인의 그대로 돌려줌은 `llm:event`만 · #10 `TurnGuard.forget` · #11~#13 복구(세션의 가장 최근 run만, 다 돈 run은 줄 없이 표시, guard가 쥔 run은 건너뜀) · #14 `_EPOCH` · #15 실행기 독스트링.
  - 시험: #2 다섯 서비스와 세션 서비스의 guard(속성과 행동) · #3 같은 사건 해소 둘 · #4 HTTP `rumor_inactive` · #16 승인 뒤 해소된 사건의 승인 · #17 해소의 새로 읽기 · #18 지운 지역의 자기 행 · #19 생성·재생성 차례 고정(매개변수 둘) · #20 `match`와 `raised` 수 · #21 잠금 차례 · #22 돌려준 행 정확히 · #23 `met`은 첫째가 붙잡혀 있을 때만, 겹침 시험이 문을 단언 · #24 불변식이 guard를 봄 · #25 스레드·결과 수.
- 확인: 고친 것마다 돌연변이 17개를 넣어 모두 잡혔다(V5 시험 파일 5개로). 게이트: pytest **1138**, ruff·black clean, mypy 11, 웹 바뀜 없음. V5 시험 91개를 다섯 번 이어 돌려 흔들림 없음.
- 설계 문서 고침: BR-V5-04(씨앗은 다시 들어가지 않음), BR-V5-07(그대로는 승인된 제안만), domain-entities § 2(`session_closed` 문장). operations.md(대기 상한 600, 복구의 두 경우), env.example.
- V6로 넘김(§ 3)과 받아들인 한계(§ 4)는 code-summary § 6·§ 7에 옮겼다.
