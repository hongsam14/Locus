## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V5 GM 쓰기 정확성
**Reviewed artifact:** `aidlc-docs/construction/V5-gm-write-correctness/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-08T06:20:19Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V5-gm-write-correctness/functional-design/business-logic-model.md > § 5 끊긴 run 복구; business-rules.md > BR-V5-19 | `_compensate`는 `_fail` 본문(`advancer.py:508-556`)이라 run 갱신·환불·위치 복원·행적 삭제·줄이 **한 작업 단위**다. 이것이 실패하면 전부 롤백되어 run은 `running`으로 남고, 설계는 그 run을 `fail_stale_runs`로 `failed/interrupted` 표시만 한다. 결과는 RE-P03이 적은 상태 그대로다(플레이어는 옮겨진 채, 청구된 채, 도착 행적과 `turn_run_failed` 줄 없음)인데 run은 `failed`라서 다음 시작에서도 재시도되지 않는다. FR-C3은 "끊긴 run도 보상한다"이고 TP-V5-5는 이 경로를 "다른 run은 보상됨"까지만 본다. 일시적 저장소 오류 한 번이 영구 불일치가 된다 | 보상이 실패한 run의 처분을 정한다. 예: `running`으로 남겨 다음 시작에 다시 시도하고 운영 로그에 run id를 남긴다, 또는 `failed`로 표시하되 `turn_run_failed` 줄(보상 못 함 표시)을 별도로 쓰고 운영자 확인 목록에 올린다. `fail_stale_runs`를 그대로 안전망으로 쓸지, 쓴다면 남는 불일치를 어디에 알리는지 BR-V5-19에 적고 TP-V5-5에 그 단언을 더한다 | New |
| R-02 | Major | aidlc-docs/construction/V5-gm-write-correctness/functional-design/business-rules.md > 시험 방식 (NFR-10), TP-V5-1, 끝 문단 "겹침 시나리오(1~4, 9~11, 13~15)는 두 저장소에서 돈다" | 현재 `resolve_event`는 지역 왜곡도를 작업 단위 **안**에서 읽는다(`event/service.py:131-146`). 인메모리 `uow`는 저장소 전체 `RLock`을 쥐므로(`memory_repo.py:629-644`) 둘째 해소는 첫째가 커밋할 때까지 `uow`에 못 들어간다. 그래서 TP-V5-1은 인메모리에서 고치기 전 코드에서도 통과하고, 이 문서가 요구하는 "고치기 전 코드에서 한 번 실패하는 것을 확인한다(돌연변이 확인)"를 인메모리에서 못 한다. 시험 방식 첫 항목은 이를 스스로 적었는데(§ SQL 어댑터만 안쪽 읽기가 겹친다) 시나리오 표 마지막 문단은 1번을 두 저장소에 넣는다. 또 SQL 쪽 끼워 넣기 문(저장소를 감싼 시험용 문)이 `uow()`가 돌려주는 저장소 객체(`.distortions` 등, 인메모리에서는 저장소 자신)까지 감싸야 \"읽기 직후\"에 멈출 수 있는데 설계에 이 요건이 없다. r1은 완료 조건의 첫 시나리오다 | TP-V5-1을 SQL 어댑터(SQLite 파일) 전용으로 고치고 인메모리는 \"겹침 없음, 결과 정확성만 확인\"으로 적는다. 끼워 넣기 문이 `uow()`의 저장소 속성도 감싸야 한다는 요건과, 시나리오마다 어느 저장소에서 고치기 전 실패가 재현되는지 표로 적는다(2·3·9·10은 읽기가 `uow` 밖이라 인메모리 재현 가능). SQLite 파일 사용과 `sqlite://`(메모리, 스레드마다 다른 DB)를 쓰지 않는다는 점도 적는다 | New |
| R-03 | Minor | business-rules.md > BR-V5-11 vs TP-V5-11 | BR-V5-11은 "재생성 둘(또는 생성과 재생성)이 겹쳐도 활성 정본 소문은 마지막 것 한 벌"이라 하고, TP-V5-11은 "생성이 뒤면 재생성 한 벌 + 생성분"이라 한다. 둘이 맞지 않는다. 생성은 `existing`를 보고 사슬을 이어 만든 초안을 밖에서 쓰므로, 생성이 뒤에 저장되면 정본 소문이 두 벌이다. 지역별 활성 상한(`max_active_rumors_per_region`)을 생성 저장 구간에서 다시 보는지도 안 적혀 있다 | BR-V5-11을 "재생성끼리"로 좁히고 생성+재생성 조합의 결과(두 벌 허용 여부, 상한)를 한 문장으로 정한다 | New |
| R-04 | Minor | business-logic-model.md > § 6 지운 지역의 사건 | 의사코드가 `ev.resolve(...)`와 줄만 적고 `out.event_updates.append(ev)`, `out.resolved_ids`, 이웃 `out.influenced_regions` 갱신 중 무엇을 하는지가 `restored` 줄 말고는 빠졌다. `_compute_events`는 `event_updates`에 든 것만 저장하므로(`advancer.py:638-642`) 빠뜨리면 사건이 DB에서 ACTIVE로 남아 매 턴 다시 해소되고 줄이 반복된다. `resolved_ids`가 `evolve_support`·`TurnResult`의 해소 집계에 쓰이는지, 줄에 지역 이름이 없을 때(§ 6 끝) 플레이어 로그 필터(`player/log.py`)가 이 줄을 어찌 다루는지도 안 적혀 있다 | 해소된 사건이 `event_updates`·`resolved_ids`에 드는지, `TurnResult`/`region_changes`·플레이어 로그에 어떻게 비치는지(또는 비치지 않는지)를 한 줄로 정한다. TP-V5-6에 "다음 턴에도 다시 해소되지 않음"을 더한다 | New |
| R-05 | Minor | aidlc-docs/construction/V5-gm-write-correctness/functional-design/domain-entities.md > § 2 오류 종류; business-logic-model.md > § 3 월드 교체 | (a) `RumorInactiveError`의 부모가 없다. `PLAY_ERRORS`(`api/errors.py:87-97`)에 들지 않으면 `gm.py:177`의 `except PLAY_ERRORS`가 못 잡아 500이 된다. `ERROR_CODES`에서 `LookupError`·`ValueError`보다 앞이어야 하는지도 부모에 달렸다. (b) `GmBusyError`가 `TurnInProgressError`의 하위라 `world.py:157`의 `except TurnInProgressError`가 닫기의 짧은 쓰기 시간 초과도 "mid-turn"으로 경고한다(`world.py:166-171`). (c) 사전 점검(`turn_running`)과 닫기 사이에 턴이 시작되는 기존 틈은 그대로이고, 닫기 실패는 경고로만 남는다 | (a) 부모 클래스와 `PLAY_ERRORS`·`ERROR_CODES` 위치를 적는다. (b) 월드 교체 경고 문구를 `gm_busy`와 구별하거나 한계로 적는다. (c) 기존 한계 유지임을 § 8에 한 줄 | New |
| R-06 | Minor | business-logic-model.md > § 5, domain-entities.md > § 1.1 호출부 정리 | `api/main.py:121-126`은 이미 시작 시 `repo.fail_stale_runs`를 직접 부른다. 설계는 "lifespan이 `recover_interrupted`를 부른다"고만 적어, 그 호출을 바꾸는 것이 `api/main.py`의 변경임과 `PlayContainer`에서 advancer에 닿는 방법(`wiring.py`는 `TurnAdvancer`를 조립하지만 필드 이름이 설계에 없다)이 빠졌다. 호출부 목록(§ 1.1)도 이 줄을 포함하지 않는다 | 바꾸는 호출부에 `api/main.py` lifespan의 기존 `fail_stale_runs` 호출과, `recover_interrupted`가 `TurnAdvancer` 메서드라면 컨테이너에서 어떻게 닿는지를 적는다 | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| grep `is_running\|running_run_id\|assert_idle` in `locus api` | `is_running`: `player/service.py:79`, `api/routers/world.py:84`; `assert_idle`: `session_service.py:115`; `running_run_id`: 호출부 0(정의만) | 설계의 호출부 정리(`current_region`, `close_session`, `_open_sessions`)와 일치. 제거 안전 |
| 짧은 쓰기를 쓸 서비스 메서드의 호출부(`create_event`, `resolve_event`, `approve_event`, `discard_event`, `suggest_events`, `generate_rumors`, `regenerate_region`, `adjust_support`, `set_region_distortion`, `void`) | 호출은 `api/routers/gm.py`와 `SeedService.start → create_event` 하나뿐. 턴(`advancer`)·`uow` 안쪽에서 부르는 곳 없음 | 잠금 차례 리스 → 짧은 쓰기 → 작업 단위를 거꾸로 잡는 호출부가 없다. 재진입은 씨앗 시작 하나(RLock). 짧은 쓰기는 시간 상한이 있어 교착이 아니라 `gm_busy`로 끝난다. 교착 없음 확인 |
| 닫기·턴 틈: `advancer._start`(`:208-224`) 읽기 순서 | acquire 뒤 `_require_open`을 다시 읽는다(`:225-228`) | `closing`이 acquire를 막고, 닫기가 끝난 뒤 시작한 턴은 닫힌 세션을 본다. 턴이 이미 돌면 `closing`이 409. 닫기 틈과 RE-P02(GM 리스 무시) 모두 설계대로 닫힘 |
| 인메모리 `uow`(`memory_repo.py:629-644`) | 저장소 전체 `RLock`을 `__enter__`에서 쥠 | `uow` 안 읽기는 인메모리에서 겹칠 수 없음 → R-02 |
| `resolve_event`/`set_region_distortion`/`adjust_support`/`approve_event`/`SeedService.start`의 읽기 위치 | 해소의 왜곡도 읽기만 `uow` 안. 몫(`distortion_service.py:55-62`), 지지도(`rumor/service.py:181`), 승인(`event/service.py:263`), 씨앗(`seeds.py:54`)은 `uow` 밖 | TP-V5-2·3·9·10은 인메모리 재현 가능, TP-V5-1은 SQL만 |
| SQL 어댑터 재현 가능성 | `tests/play/test_postgres_repo.py`는 `sqlite://`(메모리) 사용. pysqlite는 SELECT에 잠금을 쥐지 않고 DML 때 BEGIN | 파일 SQLite에서 두 스레드의 읽고-쓰기 잃은 갱신은 재현될 것으로 판단(실행은 안 함). 메모리 `sqlite://`는 스레드마다 다른 DB라 파일이어야 함 → R-02에 포함 |
| `api/errors.py` `ERROR_CODES`·`PLAY_ERRORS` | `SessionClosedError`가 맨 앞, `TurnInProgressError` 둘째, `PLAY_ERRORS`에 `RumorInactiveError` 없음 | `GmBusyError`를 `TurnInProgressError` 앞에 두면 R-04(설계 R-04)대로 동작. `RumorInactiveError` 처리는 → R-05 |
| 지운 지역 사건과 턴의 쓰기 집합(`advancer.py:637-659`) | 저장은 `event_updates`·`influenced_regions`·`timeline`만. `:603-609`은 이미 없는 지역 초안을 건너뜀 | 설계의 먼저-해소 방식은 쓰기 집합과 합성 가능하나 의사코드가 `event_updates` 등록을 빠뜨림 → R-04 |
| V4 통합점: `web/src/features/play/PlayHeader.tsx:54`, `routes/PlayPage.tsx:83-87`, `types.ts:598` | `gm_busy?: boolean`을 읽고 `turn_running`과 함께 잠금 | 설계 § 7의 "V4가 이미 함" 주장은 맞음. `gm_busy` 칸은 V5가 더함 |
| 요구 커버리지 FR-C1~C5, NFR-10 | FR-C1(#9, #12, RE-P01, RE-P06, 몫) BR-V5-05~10, FR-C2 BR-V5-14~17, FR-C3 BR-V5-18~19, FR-C4 BR-V5-20~21, FR-C5 BR-V5-22~24, NFR-10 시험 방식 | 미커버 항목 없음. 단 NFR-10의 "겹침 재현"이 TP-V5-1 인메모리에서 성립하지 않음(R-02), FR-C3 보상 실패 처분이 비어 있음(R-01) |
| `api/main.py` 시작 정리 | 이미 `fail_stale_runs` 호출 | 설계가 바꾸는 자리를 적지 않음 → R-06 |

### Summary

설계의 큰 틀은 건전하다. 잠금 차례에 거꾸로 잡는 호출부가 없고, `closing` + 짧은 쓰기로 RE-P02와 닫기·턴 틈이 닫히며, 지운 지역 사건의 먼저-해소는 턴의 쓰기 집합과 합성된다. 막힌 것은 없고(Critical 0, Major 2) 판정은 READY이지만, 코드 단계 전에 R-01(복구 보상 실패 시 RE-P03 불일치가 조용히 남음)과 R-02(TP-V5-1이 인메모리에서 고치기 전에도 통과해 돌연변이 확인을 못 함)를 고쳐 두는 편이 재작업을 줄인다. R-03~R-06은 구현 중 추측을 없애는 보완이다. 참고(제안): 에디터 지역 삭제는 리스만 쥐고 짧은 쓰기는 안 쥐므로, GM 쓰기가 지운 지역에 사건을 만들 수 있는 틈은 Q1=A의 먼저-해소가 받는다는 점을 § 8에 적어 두면 좋다.
