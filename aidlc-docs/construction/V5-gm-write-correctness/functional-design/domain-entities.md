# V5 GM 쓰기 정확성 — Domain Entities

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V5 Functional Design. 세션을 지키는 guard의 상태, 오류 종류와 응답 코드, 새 포트와 칸을 정한다.

결정(계획 `construction/plans/V5-gm-write-correctness-functional-design-plan.md`):

| 질문 | 답 | 내용 |
|---|---|---|
| Q1 | A | 월드에서 지운 지역의 활성 사건은 다음 턴에 저절로 해소한다(이웃 기여 대칭 복원) |
| Q2 | A | 그 사이 꺼진 소문의 지지도 조정은 409 `rumor_inactive`, 아무것도 쓰지 않는다 |
| Q3 | A | RE-P05(행과 기록 줄의 원자성)와 RE-P07(겹친 재생성의 두 벌)도 함께 닫는다 |

---

## 1. `TurnGuard` — 세션 하나를 지키는 세 가지

프로세스 안의 객체다(API는 워커 하나로 돈다). 세션 id마다 아래 세 상태를 가진다.

| 상태 | 무엇 | 누가 쥐나 | 서로의 관계 |
|---|---|---|---|
| **턴 슬롯** `_running[session] = run_id` | 턴 run 하나 | `TurnAdvancer._start`(acquire) | 다른 턴, GM·에디터 리스와 배타 |
| **닫는 중** `_closing[session] = n` [새] | 진행 중인 세션 닫기의 수 | `SessionService.close_session` | 새 턴만 막는다. GM 리스는 막지 않는다. 수로 세므로 겹친 닫기 둘 가운데 먼저 끝난 것이 다른 것의 표시를 지우지 않는다 |
| **리스** `_lease[session] = n` | GM 쓰기·에디터 지역 삭제가 하고 있는 수 | 라우터 `_idle`, 에디터 지역 삭제 | 리스끼리는 함께 쥔다. 턴과 배타 |
| **짧은 쓰기 잠금** `_write[session]: RLock` [새] | 읽고-쓰는 구간 하나 | GM 쓰기 서비스, 세션 닫기 | 같은 세션의 구간을 차례로 세운다. 같은 스레드는 다시 들어갈 수 있다 |

- 리스는 지금의 `_gm` 카운트를 이름만 바꾼 것이다. 에디터의 `hold(label="editor")`도 리스다.
- 짧은 쓰기 잠금은 세션마다 처음 쓸 때 만들고 지우지 않는다(세션 수만큼, 프로세스가 끝나면 사라진다).
- 잠그는 차례는 늘 같다: **리스 → 짧은 쓰기 → 저장소 작업 단위**. 그 반대로 잡는 곳은 없다.

### 1.1 메서드

```python
class GmBusyError(TurnInProgressError): ...           # 409 "gm_busy"

TurnGuard.acquire(session_id, run_id) -> None
    # 턴: 다른 턴이면 TurnInProgressError, 닫는 중이면 SessionClosedError,
    #     리스가 있으면 GmBusyError. 문장에 run id·"gm" 같은 내부값이 없다
TurnGuard.release(session_id) -> None                 # 그대로
TurnGuard.hold(session_id, *, label="gm") -> ContextManager[str]
    # 리스. 턴이 돌면 TurnInProgressError(그대로). 닫는 중은 막지 않는다
TurnGuard.short_write(session_id, *, timeout_s) -> ContextManager[None]   [새]
    # 짧은 쓰기 구간. timeout_s 안에 못 들어가면 GmBusyError
TurnGuard.closing(session_id) -> ContextManager[None]                     [새]
    # 닫기: 턴이 돌면 TurnInProgressError. 아니면 새 턴을 막고(닫는 중), 블록이 끝나면 푼다
TurnGuard.turn_running(session_id) -> bool            [새] 턴 슬롯만
TurnGuard.gm_busy(session_id) -> bool                 [새] 리스가 하나라도 있으면
# is_running / running_run_id / assert_idle 은 없앤다
```

- 호출부 정리
  - `PlayService.current_region`: `turn_running = guard.turn_running(s)`, `gm_busy = guard.gm_busy(s)`.
  - `SessionService.close_session`: `assert_idle` 대신 `closing` + `short_write`.
  - 월드 교체 사전 점검(`world.py` `_open_sessions`): `is_running` 대신 `turn_running`. 리스(GM 쓰기)는 교체를 막지 않는다.

## 2. 오류 종류와 응답 코드

| 오류 | HTTP | `code` | 언제 | 문장(`detail`) |
|---|---|---|---|---|
| `GmBusyError` [새] | 409 | `gm_busy` | 리스가 있는데 턴을 시작하려 함. 짧은 쓰기를 상한 안에 못 얻음 | "the session is busy with a GM write; retry shortly" |
| `TurnInProgressError` | 409 | `turn_running` | 턴이 도는데 턴·GM 쓰기·닫기를 하려 함 | "a turn is running in this session; retry when it ends" |
| `SessionClosedError` | 409 | `session_closed` | 닫힌(또는 닫는 중인) 세션에 씀 | 닫힘 "the session is closed", 닫는 중 "the session is closing". 둘 다 세션 id 없음(〔코드 리뷰 01 #6〕, 예전 문장은 id를 실었다) |
| `SeedAlreadyRunningError` | 409 | `seed_running` | 씨앗의 사건이 이미 진행 중 | 그대로 |
| `RumorInactiveError` [새] | 409 | `rumor_inactive` | 지지도를 조정하려는 소문이 그 사이 꺼짐(Q2=A) | "the rumor is no longer active" |

- 오류 표(`api/errors.py` `ERROR_CODES`)는 위에서부터 처음 맞는 줄을 쓴다. `GmBusyError`는 부모 `TurnInProgressError`보다 **먼저** 둔다(설계 리뷰 R-04).
- 플레이어에게 가는 409 문장에는 run id, `gm:xxxx` 토큰, 세션 id가 없다(FR-C5, #5(a), RE-P12 일부). 세션 id를 싣는 지금의 문장("turn in progress: {session_id} (run {current})")은 위 문장으로 바꾼다.
- 화면 문장은 `code`로 고른다(V2). `gm_busy`·`turn_running`은 V4가 이미 읽는다. `rumor_inactive`의 한국어 문장은 V6(GM 화면)가 붙인다. 그 전에는 V2의 409 기본 문장이 나온다.

## 3. 포트와 칸

| 이름 | 바뀜 | 내용 |
|---|---|---|
| `TurnRunStore.list_running_runs() -> list[TurnRun]` | [새] | 모든 세션의 `running` run(설계 리뷰 R-01). 끊긴 run 복구가 쓴다. 인메모리·SQL 두 어댑터와 저장소 계약 시험에 더한다 |
| `TurnRunStore.fail_stale_runs(*, reason)` | 그대로 | 복구 뒤 남은 `running`을 실패로 표시하는 마지막 안전망으로 남는다 |
| `RegionView.gm_busy: bool = False` | [새] | 리스가 있으면 참(FR-C5). V4 화면이 이미 읽는다 |
| `RegionView.turn_running` | 뜻이 좁아짐 | 턴 run만. 지금은 GM 리스도 참이었다(#5(a)) |
| `PlayTuning.gm_write_wait_s: float = 5.0` | [새] | 짧은 쓰기 기다림 상한. 환경 변수로 바꿀 수 있다 |
| 타임라인 `EVENT_RESOLVED` payload `reason` | [새 키] | 저절로 끝난 사건은 `"region_removed"`(Q1=A). GM이 해소한 줄은 키가 없다 |
| 타임라인 `TURN_RUN_FAILED` payload `error_type` | 값이 하나 늚 | 재시작으로 끊긴 run은 `"Interrupted"`(그 run의 `error`는 `"interrupted"`) |

## 4. 바뀌지 않는 것

- 턴 하나가 세션 전체를 배타로 쥐는 규칙(BR-U4-13).
- GM 쓰기끼리 리스를 함께 쥐는 규칙(U7 리뷰 #2). 일괄 생성 다섯 개는 LLM을 함께 부른다.
- 대화(`say`)는 턴 중에도 된다(BR-U5-27). 대화는 리스도 짧은 쓰기도 쥐지 않는다.
- PostgreSQL의 행 잠금(`FOR UPDATE`)과 상태 조건 쓰기(`update_event_contributions(..., status=...)`)는 남긴다. 여러 프로세스는 범위 밖이지만 두 겹으로 지킨다.
- 응답 본문의 모양(`{"detail", "code"}`).
