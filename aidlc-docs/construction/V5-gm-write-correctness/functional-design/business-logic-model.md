# V5 GM 쓰기 정확성 — Business Logic Model

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V5 Functional Design. GM 쓰기가 겹치거나 닫기·재시작과 겹쳐도 결과가 차례로 한 것과 같게 하는 흐름을 정한다.

결정: Q1=A(지운 지역의 사건은 저절로 해소), Q2=A(꺼진 소문 조정은 409 `rumor_inactive`), Q3=A(RE-P05·RE-P07도 닫음). 용어와 메서드는 `domain-entities.md`를 본다.

---

## 1. 짧은 쓰기 구간의 모양

모든 GM 쓰기는 같은 모양을 따른다.

```
라우터: with guard.hold(s):                         # 리스: 턴과 배타, GM 쓰기끼리 함께 (그대로)
  서비스:
    (밖) 입력 확인, 월드 스냅숏 읽기, LLM 초안 만들기     # 몇 초 걸려도 된다
    with guard.short_write(s, timeout_s=tuning.gm_write_wait_s):   # 세션마다 하나씩
      with repo.uow() as u:                            # 한 트랜잭션
        session = 세션을 새로 읽는다; 닫혔으면 SessionClosedError
        바꿀 행을 새로 읽는다(사건은 FOR UPDATE)
        조건을 다시 본다(상태, 진행 중 여부, 꺼짐 여부)
        쓴다
        그 일의 타임라인 줄을 쓴다                      # RE-P05: 행과 줄이 함께
    return
```

- **밖에 두는 것**: LLM 호출, 월드 스냅숏 읽기, 이름 찾기. 구간을 짧게 유지한다.
- **안에 두는 것**: 세션 열림 확인, 바꿀 행 읽기, 조건 확인, 쓰기, 타임라인 줄.
- **구간에서 "새로 읽는다"가 핵심이다.** 같은 세션의 구간은 차례로 돌므로, 둘째 쓰기는 첫째가 쓴 값을 읽고 쓴다. 그래서 절대값으로 써도 결과가 차례로 한 것과 같다.
- 구간 안에서 실패하면 작업 단위가 되돌린다. 행만 쓰이고 줄이 빠지는 일이 없다(RE-P05).
- 상한(`gm_write_wait_s`, 5초) 안에 구간에 못 들어가면 `GmBusyError`(409 `gm_busy`)다. 저장 구간은 밀리초라, 상한은 무엇이 멈췄을 때만 걸린다.

## 2. 서비스별 구간 경계

| 쓰기 | 밖 | 구간 안 | 겹쳤을 때의 결과 |
|---|---|---|---|
| **사건 만들기** `EventService.create_event` | 지역 확인(스냅숏) | 열림 확인 → 사건 저장 → `event_created` 줄 | 둘 다 만들어진다(차례로 한 것과 같음) |
| **사건 해소** `resolve_event` (#9) | 이름 찾기 | 사건을 FOR UPDATE로 읽음 → 이미 해소면 그대로 돌려줌 → 지역 왜곡도를 **구간 안에서** 읽고 기여를 되돌림 → 해소 → `event_resolved` 줄 | 다른 두 사건의 해소가 겹쳐도 두 복원이 모두 반영된다 |
| **사건 승인** `approve_event` (RE-P06) | 이름 찾기 | 사건을 새로 읽음 → 없으면 404 → 이미 ACTIVE면 그대로 돌려줌(줄 없음) → 해소됐으면 400 → 승인 → `event_approved` 줄 | 승인 둘: 줄 하나. 승인 뒤 폐기: 400. 폐기 뒤 승인: 404 |
| **사건 폐기** `discard_event` | 이름 찾기 | 사건을 새로 읽음 → 없으면 404 → 제안이 아니면 400 → `event_discarded` 줄 → 삭제 | 폐기 둘: 둘째 404 |
| **사건 제안** `suggest_events` | 문맥 만들기, **LLM 호출** | 열림 확인 → 초안마다 사건 저장과 `event_suggested` 줄 | 제안과 닫기가 겹치면 409 `session_closed`, 아무것도 안 쓴다 |
| **씨앗 시작** `SeedService.start` (#12) | 씨앗·지역 확인(스냅숏) | 진행 중인지 확인 → 아니면 사건 만들기(같은 구간에 다시 들어감) | 시작 둘: 하나는 201, 하나는 409 `seed_running`. ACTIVE 사건은 하나 |
| **소문 생성** `RumorService.generate_rumors` | 사슬 단계 계산, **LLM 초안** | 열림 확인 → 초안 저장 → `generate` 줄 | 다섯 지역 일괄 생성은 LLM을 함께 부르고 저장만 차례로 한다 |
| **소문 재생성** `regenerate_region` (RE-P07) | 사슬 단계, **LLM 초안**(정본 지식에서만) | 열림 확인 → 지역 소문을 **새로 읽고** 버릴 것(승격 안 된 정본)을 이때 고름 → 건너뛰기 조건 판단 → 버릴 것 끄기, 새것 저장 → `regenerate` 줄 | 재생성 둘: 뒤의 것이 앞의 것을 끄고 자기 것을 둔다. 활성 정본 소문은 한 벌이다 |
| **지지도 조정** `adjust_support` (RE-P01, Q2=A) | — | 소문을 새로 읽음 → 없으면 404 → 꺼졌으면 `RumorInactiveError`(409 `rumor_inactive`), 아무것도 안 씀 → 지지도 저장 → `adjust_support` 줄 | 취소·재생성과 겹쳐도 꺼진 소문을 되살리지 않는다 |
| **행적 취소** `DeedService.void` | 이름 찾기 | 행적을 새로 읽음 → 없으면 404 → 이미 취소면 그대로(줄 없음) → 취소, 그 행적의 소문 끄기 → `deed_voided` 줄 | 취소 둘: 줄 하나 |
| **왜곡도 설정** `DistortionService.set_region_distortion` (U8 §3) | 지역 확인(스냅숏) | 되먹임 몫을 **구간 안에서** 읽음 → 값 저장, 몫 0 → ACTIVE 사건 기여를 상태 조건으로 지움 → `set_distortion` 줄 | 같은 지역 설정 둘: 몫은 첫째만 기록하고 둘째는 0을 기록한다 |

- 같은 세션의 구간에 다시 들어가는 곳은 씨앗 시작(→ 사건 만들기) 하나다. 짧은 쓰기 잠금은 같은 스레드에서 다시 들어갈 수 있다.
- 왜곡도 설정은 저장한 행을 서비스가 돌려준다(`RegionDistortion`). 지금처럼 라우터가 저장소를 다시 읽지 않는다(component-methods § 6).
- 재생성의 두 건너뛰기("생성이 덜 됨", "씨앗 없음")도 구간 안에서 판단하고, 건너뛴 줄도 구간 안에서 쓴다.

## 3. 세션 닫기 (RE-P02)

```
SessionService.close_session(s):
  with guard.closing(s):                 # 턴이 돌면 409 turn_running. 아니면 새 턴을 막는다
    with guard.short_write(s, timeout):  # 저장 중인 GM 쓰기가 있으면 그 저장이 끝난 뒤
      with repo.uow() as u:
        닫음(이미 닫혔으면 그대로) → 처음 닫을 때만 session_closed 줄
```

- **닫기는 리스를 쥐지 않는다.** GM 쓰기의 LLM 호출(몇 초~몇십 초)을 기다리지 않는다. 기다리는 것은 짧은 저장 구간뿐이다.
- 닫기가 끝난 뒤 들어오는 GM 저장 구간은 세션이 닫힌 것을 보고 쓰지 않는다(409 `session_closed`). 그 GM 쓰기가 만든 LLM 초안은 버려진다.
- **닫는 동안 새 턴은 시작하지 못한다**(`closing`). 지금은 턴 여부를 한 순간만 보므로, 그 직후 시작한 턴이 닫히는 세션에 쓸 수 있었다. 닫는 중에 턴을 시작하려 하면 409 `session_closed`다. 닫기가 끝나면 그 턴은 어차피 닫힌 세션을 본다.
- **월드 교체의 닫기**(`world.py` `_close_if_replaced`)도 같은 함수를 부른다.
  - 사전 점검은 **턴이 도는 세션만** 막는다(409 `sessions_busy`). GM 쓰기는 교체를 막지 않는다.
  - 교체가 세션을 닫으면, 그때 진행 중이던 GM 쓰기는 저장 때 닫힘을 본다.

## 4. 턴과 GM 쓰기의 관계

| 지금 쥔 것 | 턴 시작(`acquire`) | GM 쓰기(`hold`) | 닫기(`closing`) |
|---|---|---|---|
| 아무것도 없음 | 됨 | 됨 | 됨 |
| 턴 | 409 `turn_running` | 409 `turn_running` | 409 `turn_running` |
| GM·에디터 리스 | 409 `gm_busy` | 됨(함께) | 됨(저장 구간만 기다림) |
| 닫는 중 | 409 `session_closed` | 됨(저장 때 닫힘을 봄) | 됨(이미 닫는 중이면 기다림) |

- 턴은 짧은 쓰기를 쥐지 않는다. 턴이 도는 동안에는 GM 쓰기도 닫기도 시작하지 못하므로 겹칠 것이 없다.
- GM의 수동 턴(`/advance`)도 턴이다. GM 쓰기가 리스를 쥐고 있으면 409 `gm_busy`다.

## 5. 끊긴 run 복구 (FR-C3, RE-P03)

```
TurnAdvancer.recover_interrupted() -> list[str]:      # api lifespan이 시작할 때 부른다
  done = []
  for run in repo.list_running_runs():                # 모든 세션
    try:
      _compensate(run, error_type="Interrupted", error="interrupted")
      done.append(run.id)
    except Exception: 기록하고 다음 run으로
  repo.fail_stale_runs(reason="interrupted")           # 보상이 실패해 남은 것만 (마지막 안전망)
  return done

_fail(run, exc) = _compensate(run, error_type=type(exc).__name__, error=RUN_FAILED_MESSAGE)
```

- `_compensate`는 지금의 `_fail` 본문이다. 실패와 복구가 같은 규칙을 쓴다(설계 리뷰 R-01: `_fail`의 예외 인자를 오류 종류 문자열로 바꾼다).
  - 넘어간 턴 수 = 세션 턴 − run의 시작 턴(0 이상, 비용 이하).
  - 청구는 넘어간 턴만큼만 남기고 나머지를 환불한다.
  - 0턴이면 이동을 되돌리고(이동이었을 때), 그 run의 행적과 판단을 지운다.
  - run을 `failed`로 바꾸고, `turn_run_failed` 줄을 쓴다(`error_type`, 넘어간 턴, 환불, 되돌린 지역).
- 새 프로세스라 guard는 비어 있다. 복구가 끝나기 전에 요청을 받지 않는다(lifespan의 시작 단계).
- 세션이나 플레이어가 없는 run도 `failed`가 된다. 줄은 세션이 있을 때만 쓴다(지금 `_fail`과 같다).

## 6. 지운 지역의 사건 (FR-C4, RE-P04, Q1=A)

턴 계산 `_compute_events`에서, 사건을 적용하기 **전에** 대상 지역이 월드에 없는 ACTIVE 사건을 먼저 끝낸다.

```
present = 스냅숏의 지역 id들
for ev in active:
  if ev.region_id not in present:
    restored = {rid: v for rid, v in ev.contributions if rid in present}   # 있는 지역만
    cur = restore_contributions(cur, restored)          # GM 해소와 같은 대칭 복원
    ev.resolve(session.turn + 1)                        # 이 턴에 끝남 (one_shot과 같은 턴 번호)
    influenced += restored의 지역                        # 바뀐 이웃 행만 저장된다
    줄: event_resolved {event_id, restored, region_id, reason: "region_removed"}
    continue                                            # 적용하지 않는다
  (그 밖의 사건은 지금처럼 적용)
```

- 지운 지역 자신의 왜곡도 행은 더 이상 쓰이지 않는다. 턴은 "사건이 움직인 지역"의 행만 쓰는데, 지운 지역은 거기에 들지 않는다.
- 복원은 남아 있는 지역에만 한다. GM이 그런 사건을 손으로 해소할 때도 같다(없는 지역의 행을 새로 만들지 않는다).
- 먼저 끝내고 나서 다른 사건을 적용하므로, GM이 그 사건을 해소한 뒤 턴을 돌린 것과 같은 결과다.
- 지역을 나중에 같은 id로 되살려도 사건은 돌아오지 않는다. GM이 다시 만들거나 씨앗을 다시 시작한다.
- 줄의 지역 이름은 남지 않는다(지역이 없다). V6의 GM 화면이 `reason: "region_removed"`로 "사라진 지역의 사건이 끝났다"를 쓴다.

## 7. 바쁨 표시 (FR-C5, #5(a))

- `PlayService.current_region`이 `turn_running = guard.turn_running(s)`, `gm_busy = guard.gm_busy(s)`를 채운다.
- 플레이어의 행동(`act`)
  - 턴이 돌면 409 `turn_running`, 리스가 있으면 409 `gm_busy`, 닫는 중이면 409 `session_closed`.
  - 문장에 run id·"gm" 토큰·세션 id가 없다.
- 화면(V4가 이미 함): `gm_busy`면 머리에 "GM이 작업 중이에요"가 뜨고 행동이 꺼진다. 1초 × 5번 다시 읽고, 그 뒤에는 [다시 확인]을 보인다. 409 busy를 받으면 다시 읽고 진행 중인 run을 찾는다.
- 에디터의 지역 삭제(`hold(label="editor")`)도 리스라 `gm_busy`로 보인다. 플레이어에게는 같은 안내다.

## 8. 바꾸지 않는 것과 범위 밖

- 턴 하나가 세션을 배타로 쥐는 규칙, GM 쓰기끼리 리스를 함께 쥐는 규칙, 대화가 턴 중에도 되는 규칙.
- 여러 API 프로세스(워커 둘 이상). 짧은 쓰기는 프로세스 안 잠금이다. PostgreSQL 행 잠금과 상태 조건 쓰기는 남겨 두 겹으로 지키고, 실제 PostgreSQL 겹침은 운영자 확인 목록에 남긴다(NFR-10).
- 지운 지역에 남은 **소문**의 되먹임(턴의 `apply_feedback`)이 그 지역 행을 쓰는 일. FR-C4는 사건만 말한다. 알려진 한계로 적는다.
- 웹 화면의 이중 실행(씨앗 [시작] 두 번 누름 등)은 V6가 막는다. V5는 서버가 두 번째를 409로 답하게 한다.
- RE-P12의 나머지(외톨이 서로게이트 500, 깊은 중첩 `RecursionError`, `?status=` 검증 없음)는 V9로 넘긴다. V5는 "(run gm)" 내부값만 닫는다.
