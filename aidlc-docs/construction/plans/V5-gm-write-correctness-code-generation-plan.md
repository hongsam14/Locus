# V5 GM 쓰기 정확성 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V5(실행 5/9), Code Generation Part 1. 승인된 FD·NFR을 코드로 옮길 순서, 커밋 단위, 시험을 정한다. 백엔드만 바뀐다(`locus/play`, `locus/shared/config`, `api`, `tests`, 운영 문서). 이 계획이 Part 2의 유일한 기준이다.

**입력**
- FD(승인 2026-10-08): `construction/V5-gm-write-correctness/functional-design/{domain-entities,business-logic-model,business-rules}.md` — BR-V5-01~25, TP-V5-1~15. 리뷰 01의 R-01~R-06은 Accepted risk → § 1.1
- NFR light(승인 2026-10-08): `construction/V5-gm-write-correctness/nfr/nfr-light.md` — 시험 저장소·끼워 넣기 문·운영자 확인·상태 기계 PBT. 리뷰 01의 R-01~R-06은 Accepted risk → § 1.2
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V5(완료 조건: r1·r2·r3·r4·r5·r9 회귀, 일괄 생성 5개 동시, 플레이어 409에 내부값 없음)
- Application Design `component-methods.md` § 6, `services.md` S1·S2·S5·S6
- 요구 `inception/requirements/follow-up-requirements.md` FR-C1~C5, NFR-1·5·6·8·9·10

**기준선**(Step 1에서 잰다): pytest 1048, ruff·black clean, mypy 11. 웹은 바뀌지 않는다(vitest 550 그대로).

---

## 1. 실행 메모 (리뷰가 넘긴 것, 승인 때 Accepted risk)

### 1.1 FD 리뷰 01

- **〔FD R-01〕 보상이 실패한 끊긴 run**
  - 복구는 run마다 보상한다.
  - 보상이 예외로 끝나면 그 run을 **따로의 작업 단위**에서 `failed`, error `interrupted_uncompensated`로 표시하고, run id·세션 id를 ERROR 로그로 남긴다.
  - 그 표시마저 실패하면(저장소가 내려감) run은 `running`으로 남고, 다음 시작에서 다시 보상한다.
  - 보상 없이 실패로만 표시하는 `fail_stale_runs`는 **없앤다**(포트, 두 어댑터, lifespan, 시험 3곳). 위 처분이 그 자리를 대신한다.
  - operations.md에 `interrupted_uncompensated` run을 찾는 방법과 그때 할 일(플레이어 위치·청구 손으로 확인)을 적는다.
  - TP-V5-5에 "보상이 실패하는 run은 `interrupted_uncompensated`, 다른 run은 보상됨, 다음 복구에서 다시 건드리지 않음"을 단언한다.
- **〔FD R-02〕 TP-V5-1**은 SQL 어댑터(SQLite 파일) 전용이다. 인메모리는 결과 정확성만 본다. 저장소별 재현 표와 끼워 넣기 문의 요건은 NFR § 2를 따른다(§ 1.2 R-02·R-05).
- **〔FD R-03〕 BR-V5-11**은 "재생성끼리"다. 생성과 재생성이 겹치면 결과는 차례로 한 것과 같다: 생성이 뒤면 재생성 한 벌 + 생성분, 재생성이 뒤면 재생성 한 벌. 지역별 활성 상한은 지금처럼 생성에서 다시 보지 않는다(턴만 본다). TP-V5-11의 단언이 이것이다.
- **〔FD R-04〕 저절로 해소된 사건**(지운 지역)
  - `event_updates`·`resolved_ids`에 넣는다. DB에서 해소되고 `TurnResult.resolved_event_ids`에 실린다.
  - 되돌린 이웃은 `influenced_regions`에 넣는다(그 행만 저장).
  - 플레이어 기록에는 나오지 않는다. 플레이어가 그 지역에 설 수 없기 때문이다(지역 삭제는 플레이어가 선 지역을 거부한다).
  - TP-V5-6에 "다음 턴에도 다시 해소되지 않음(줄 하나)"을 단언한다.
- **〔FD R-05〕 오류 계층**
  - (a) `RumorInactiveError(RuntimeError)`. `PLAY_ERRORS`에 넣고, `ERROR_CODES`에는 `seed_running` 다음에 둔다.
  - (b) 월드 교체가 닫기에서 `GmBusyError`(짧은 쓰기 상한)를 받으면 경고 문장을 "busy and could not be closed"로 `turn_running`과 나눈다(`world.py` `_close_if_replaced`).
  - (c) 사전 점검과 닫기 사이에 턴이 시작되는 틈은 지금 한계 그대로다. 그때 닫기가 409이면 경고로 남는다. code-summary 알려진 한계에 적는다.
- **〔FD R-06〕 lifespan**(`api/main.py:118-124`)의 `fail_stale_runs` 호출을 `containers.play.turns.recover_interrupted()`로 바꾼다(`PlayContainer.turns: TurnAdvancer`).

### 1.2 NFR 리뷰 01

- **〔NFR R-01〕 운영자 확인**: B&T 체크리스트로 넘긴다. P1~P3은 "실제 스택 스모크"(고치기 전 코드에서도 통과할 수 있음)로 이름을 고친다. 잠금 자체를 보려면 `psql`로 사건 행을 `SELECT … FOR UPDATE`로 잡아 둔 채 해소를 보내 지연을 보는 확인을 더한다. code-summary § 7(B&T에 넘김)에 적는다.
- **〔NFR R-02〕 픽스처**: 새 `threaded_repo`(인메모리 / SQLite **파일**)를 `tests/play/conftest.py`에 둔다. `list_running_runs`의 계약 시험은 기존 `any_repo`(`test_repository_contract.py:366`)에 둔다. `any_repo`는 고치지 않는다.
- **〔NFR R-03〕 바뀌는 기존 시험**(grep, 2026-10-08)
  - `is_running` 20곳: `test_player_mode.py` 14, `test_turn_guard.py` 5, `test_play_api.py` 1.
  - `assert_idle` 3곳: `test_turn_guard.py` 2, `test_player_mode.py` 1.
  - `running_run_id` 2곳: `test_turn_guard.py`.
  - 409 문장 "turn in progress" 단언 3곳: `test_seeds_api.py`, `test_u3_carry_api.py`, `test_world_editor_api.py`.
  - `turn_running` 단언 4곳: `test_error_codes.py` 1, `test_play_api.py` 2, `test_player_mode.py` 1.
  - `fail_stale_runs` 3곳: `test_repository_contract.py` 2, `test_postgres_repo.py` 1.
  - 세 메서드는 없앤다(BR-V5-25). 월드 교체 점검(`world.py:84`)은 턴만 센다.
  - 실제로 고친 수와 이유는 code-summary에 적는다.
- **〔NFR R-04〕 운영자 확인 P3·P5 문장**(B&T)
  - P3: `POST /api/gm/sessions/{s}/seeds/{같은 씨앗 id}/start` 둘, 기대는 201 하나와 409 하나다.
  - P5: run의 status `failed`와 error `interrupted`를 `GET /api/play/sessions/{s}/turn-runs/{id}`로 본다.
- **〔NFR R-05〕 끼워 넣기 문**
  - **메서드 이름**으로 멈춘다. 저장소와 `uow()`의 저장소 속성을 **명시한 메서드만** 감싼다(`__getattr__` 위임을 쓰면 `isinstance(…, PlayRepository)`를 시험에서 쓰지 않는다).
  - 인메모리 작업 단위 **안**에서는 멈추지 않는다. 그 안은 저장소 `RLock`을 쥐고 있어 다른 스레드가 막힌다.
- **〔NFR R-06〕 상태 기계 불변식**에 "리스 둘이 함께 있어도 되고, 마지막이 나올 때만 `gm_busy`가 풀린다"를 더한다.

### 1.3 이 계획이 정한 것

- **커밋**: 단계마다 하나다. 게이트가 GREEN일 때만 커밋한다. 게이트는 ruff·black(`locus api tests`), mypy ≤ 11, pytest(pipefail)이다. 세션 scratchpad에 `v5gate.sh`로 둔다(V3의 `v3gate.sh`와 같은 내용).
- **돌연변이 확인**: 겹침 시험마다 쓸 때 한 번, 짧은 쓰기를 빈 블록으로 바꾼 코드(또는 고치기 전 코드)에서 실패하는지 본다. 결과는 단계 실행 기록에 적는다.
- **시험 시간**: 끼워 넣기 문의 기다림은 0.5초다. 겹침 시험이 20개 안팎이면 pytest가 10초 남짓 늘어난다.
- **푸시·PR**: 하지 않는다(사람의 일).

### 1.4 실행 메모 (코드 계획 리뷰 01, 승인 때 Accepted risk)
- 〔실행 메모 R-01〕 Step 2.5의 닫기: 앞의 `_require`는 404 확인뿐이다. 열림·닫힘 판단과 "줄은 한 번" 판단은 짧은 쓰기 **안에서** 다시 읽은 세션(또는 저장소가 돌려준 `closed`의 이전 상태)으로 한다. 닫기 둘이 겹쳐도 줄은 하나다(TP-V5-14).
- 〔실행 메모 R-02〕 Step 8.1에 둘을 더한다.
  - `interrupted_uncompensated` run을 찾는 법과 할 일. 경로 `GET /api/play/sessions/{s}/turn-runs?status=failed`로 찾고 error를 본다. 또는 SQL `select id, session_id from turn_runs where error = 'interrupted_uncompensated'`. 찾으면 플레이어 위치·청구를 손으로 확인한다.
  - operations.md 113~120행의 `fail_stale_runs`·"turn in progress" 문장을 새 복구와 409 코드(`turn_running`·`gm_busy`)로 고친다.
- 〔실행 메모 R-03〕 새 생성자 인자 `guard`는 지금 선례(`SessionService`, `TurnAdvancer`)처럼 기본값 `None` → 자기 `TurnGuard()`, `tuning`은 기본 `None` → `PlayTuning()`이다. wiring은 공유 guard와 tuning을 넘긴다. 겹침 시험은 `assemble_play`(시험 헬퍼 `compose_play`)로 만들거나 같은 guard를 넘긴다. 직접 만드는 곳(EventService 2, RumorService 4, DeedService 2, DistortionService 1, SeedService 1)은 기본값 덕에 그대로 돈다.
- 〔실행 메모 R-04〕 TP-V5-15를 나눈다. Step 2: `sessions_busy`와 "리스가 교체를 막지 않음". Step 5.2: "GM 생성 중 월드 교체 → 생성 409 `session_closed`".
- 〔실행 메모 R-05〕 Step 3.1에 `FailingTimeline`(타임라인 쓰기가 작업 단위 안에서 실패하는 감싸개, 두 저장소)을 더한다. TP-V5-12가 쓴다.
- 〔실행 메모 R-06〕 code-summary § 5(이탈)에 "`fail_stale_runs` 없앰"을 적는다. 승인된 BR-V5-19, domain-entities § 3, TP-V5-5 문장이 이와 다르다는 것과 근거(FD 리뷰 R-01 → 실행 메모 § 1.1)를 함께 적는다.

---

## 2. 단계

### Step 1 — 진행 기록과 기준선
- [x] 1.1 진행 기록을 커밋한다: audit, state, FD 계획(체크), FD 산출물·리뷰, NFR light·리뷰, 이 계획과 리뷰(`docs(aidlc): V5 functional design and NFR approved; V5 code plan`). 지난 push 사실을 적은 state 줄도 함께 간다.
- [x] 1.2 기준선을 잰다(2026-10-08: pytest 1048, ruff·black clean, mypy 11): pytest(1048), ruff·black, mypy(11). `v5gate.sh`를 만든다.

### Step 2 — guard·오류·조정값·호출부 (domain-entities § 1~3, BR-V5-03·04·14·16·17·22~25)
- [x] 2.1 `locus/play/errors.py`
  - `GmBusyError(TurnInProgressError)`를 더한다.
  - `RumorInactiveError(RuntimeError)`를 더한다(§ 1.1 R-05a).
- [x] 2.2 `locus/play/turn/guard.py`를 다시 쓴다.
  - 상태: 턴 슬롯, 닫는 중(수), 리스(수), 세션별 짧은 쓰기 `RLock`.
  - 메서드: `acquire`(턴 → `TurnInProgressError`, 닫는 중 → `SessionClosedError`, 리스 → `GmBusyError`), `release`, `hold`(턴 → `TurnInProgressError`), `short_write(s, *, timeout_s)`(상한을 넘으면 `GmBusyError`), `closing(s)`(턴 → `TurnInProgressError`), `turn_running`, `gm_busy`.
  - 문장에는 세션 id·run id·토큰을 싣지 않는다.
  - `is_running`·`running_run_id`·`assert_idle`은 없앤다.
- [x] 2.3 `locus/shared/config/{tuning,settings}.py`
  - `PlayTuning.gm_write_wait_s: float = 5.0`
  - `Settings.gm_write_wait_s`(alias `GM_WRITE_WAIT_S`, > 0)
  - `play_tuning()`에 연결한다.
- [x] 2.4 `locus/play/models.py` `RegionView.gm_busy: bool = False`. `locus/play/player/service.py`가 `turn_running = guard.turn_running(s)`, `gm_busy = guard.gm_busy(s)`를 채운다.
- [x] 2.5 `locus/play/session_service.py` `close_session`: `with guard.closing(s): with guard.short_write(s, timeout_s=…):` 안에서 작업 단위로 닫는다. 서비스가 tuning을 받는다(wiring).
- [x] 2.6 `api/routers/world.py`
  - 사전 점검은 `play.guard.turn_running(sid)`만 본다.
  - `_close_if_replaced`는 `GmBusyError`(바쁨)와 `TurnInProgressError`(턴)를 나눠 경고한다(§ 1.1 R-05b).
- [x] 2.7 `api/errors.py`
  - `ERROR_CODES`에 `(GmBusyError, 409, "gm_busy")`를 `TurnInProgressError` **앞**에 둔다(R-04).
  - `(RumorInactiveError, 409, "rumor_inactive")`를 `seed_running` 다음에 둔다.
  - `PLAY_ERRORS`에 `RumorInactiveError`를 더한다.
- [x] 2.8 시험(파일: `tests/play/test_turn_guard.py`, 새 `tests/play/test_guard_machine.py`, 새 `tests/api/test_v5_busy_api.py`)
  - `test_turn_guard.py`: 세 메서드를 새 메서드로 고친다. 더하는 것: `short_write` 기다림·상한·같은 스레드 다시 들어감, `closing` 수 세기, 리스 수 세기.
  - 새 `test_guard_machine.py`: hypothesis 상태 기계(NFR § 4 + R-06).
  - TP-V5-8: 행동 409 세 코드, 문장에 내부값 없음, `RegionView` 두 칸, `GmBusyError` 매핑.
  - TP-V5-14: 닫는 중 턴 409 `session_closed`, 닫기 둘 겹침.
  - TP-V5-15: 리스가 있어도 월드 교체가 진행되고 세션이 닫힘. 턴이 돌면 `sessions_busy`.
  - § 1.2 R-03의 기존 단언을 고친다.
- [x] 2.9 커밋: `fix(play): the session guard tells a turn from a GM write and closes without a gap; 409s carry no internals (V5, FR-C2, FR-C5)`

### Step 3 — 시험 받침 (NFR § 2, R-02·R-05)
- [x] 3.1 `tests/play/concurrency.py`
  - `InterleaveGate`: 메서드 이름 기준, 첫 두 호출, 0.5초. 저장소와 `uow()` 저장소 속성의 명시 메서드를 감싼다. 인메모리 작업 단위 안에서는 멈추지 않는다.
  - `BlockingDrafts`: 가짜 생성기·제안기다. `threading.Event`로 멈추고, 동시에 들어온 수의 최댓값을 센다.
- [x] 3.2 `tests/play/conftest.py`: `threaded_repo` 픽스처(`memory` / `sql`: `sqlite:///{tmp_path}/play.db`, `check_same_thread=False`, `timeout=5`, 스키마 생성).
- [x] 3.3 받침 자체 시험: 문이 두 스레드를 모으고, 혼자면 시간 초과로 푼다.
- [x] 3.4 커밋: `test(play): an interleave gate and a threaded repository for overlap tests (V5, NFR-10)`

### Step 4 — 사건·씨앗 구간 (BLM § 2, BR-V5-01·02·05·06·07·12·21)
- [x] 4.1 `EventService`가 guard와 tuning을 받는다(wiring).
  - `create_event`·`resolve_event`·`approve_event`·`discard_event`: 구간 안에서 열림을 확인하고 새로 읽고 쓰고 줄을 쓴다.
  - `suggest_events`: LLM은 밖, 저장과 줄은 구간 안이다.
  - 승인 규칙(BR-V5-07), 해소의 복원은 월드에 있는 지역만(BR-V5-21)이다.
- [x] 4.2 `SeedService.start`: 진행 중 확인과 만들기를 한 구간에 둔다(다시 들어감).
- [x] 4.3 시험(새 `tests/play/test_v5_overlap.py` — 겹침 시나리오는 모두 이 파일, `threaded_repo`로 두 저장소)
  - TP-V5-1: SQL 전용, 인메모리는 정확성만.
  - TP-V5-2, TP-V5-9.
  - TP-V5-12 사건 쪽(만들기·승인·제안).
  - TP-V5-13: 상한 0.1초, 씨앗 다시 들어감.
  - 돌연변이 확인.
- [x] 4.4 커밋: `fix(play): event and seed writes run one at a time per session — both restores land, one seed start wins (V5, #9, #12, RE-P06)`

### Step 5 — 소문 구간 (BLM § 2, BR-V5-08·11·12·13)
- [x] 5.1 `RumorService`가 guard와 tuning을 받는다.
  - `generate_rumors`: 초안은 밖, 저장과 줄은 구간 안.
  - `regenerate_region`: 초안은 밖, 구간 안에서 버릴 것을 다시 고르고 건너뛰기를 판단한다.
  - `adjust_support`: 구간 안에서 새로 읽고, 꺼졌으면 `RumorInactiveError`, 줄도 같은 단위에 쓴다.
  - `_generate_for_region`을 초안과 저장으로 나눈다.
- [x] 5.2 시험(`tests/play/test_v5_overlap.py`)
  - TP-V5-4: 닫기 중 생성.
  - TP-V5-7: 일괄 다섯, 동시 최댓값 ≥ 2.
  - TP-V5-11: 재생성 둘, 생성·재생성.
  - TP-V5-12 소문 쪽.
  - TP-V5-3의 조정 쪽은 Step 6에서 행적 취소와 함께 본다.
  - 돌연변이 확인.
- [x] 5.3 커밋: `fix(play): rumor writes save inside the session's short write — a closed session gets nothing, a second regenerate replaces the first (V5, RE-P02, RE-P05, RE-P07)`

### Step 6 — 행적·왜곡도 구간 (BLM § 2, BR-V5-08·09·10)
- [ ] 6.1 `DeedService.void`: guard를 받고, 구간 안에서 다시 읽는다(이미 취소면 그대로).
- [ ] 6.2 `DistortionService.set_region_distortion`: guard를 받고, 몫을 구간 안에서 읽고, 저장한 `RegionDistortion`을 돌려준다. `api/routers/gm.py` `set_distortion`은 그 값을 그대로 돌려준다(저장소를 다시 읽지 않는다).
- [ ] 6.3 시험(`tests/play/test_v5_overlap.py`): TP-V5-3(조정과 취소가 겹침, 다음 턴에 퍼지지 않음), TP-V5-10. 돌연변이 확인.
- [ ] 6.4 커밋: `fix(play): a voided deed's rumor stays voided under a support change; a distortion set records the feedback share once (V5, RE-P01)`

### Step 7 — 턴: 끊긴 run 복구와 지운 지역의 사건 (BLM § 5·6, BR-V5-18~21, § 1.1 R-01·R-04·R-06)
- [ ] 7.1 포트 `TurnRunStore.list_running_runs()`를 더하고, `fail_stale_runs`를 없앤다(인메모리, SQL, 포트).
- [ ] 7.2 `TurnAdvancer`
  - `_fail` 본문을 `_compensate(run, *, error_type, error)`로 옮긴다. `_fail`은 그것을 부른다.
  - `recover_interrupted() -> list[str]`: 보상 → 실패면 `interrupted_uncompensated` 표시와 ERROR 로그(§ 1.1 R-01).
- [ ] 7.3 `api/main.py` lifespan: `containers.play.turns.recover_interrupted()`.
- [ ] 7.4 `_compute_events`: 적용 전에 대상 지역이 없는 ACTIVE 사건을 해소한다.
  - 복원은 있는 지역만, `event_updates`·`resolved_ids`·`influenced_regions`에 넣고, 줄의 `reason`은 `region_removed`다.
- [ ] 7.5 시험(새 `tests/play/test_v5_turns.py`, 계약은 `tests/play/test_repository_contract.py`)
  - TP-V5-5: 0턴 이동, 1/2턴, 보상 실패, 다음 복구.
  - TP-V5-6: 다음 턴에 다시 해소되지 않음, GM 해소도 없는 지역 행을 만들지 않음.
  - 계약 시험 `list_running_runs`(`any_repo`).
  - `fail_stale_runs` 시험 3곳을 고친다.
- [ ] 7.6 커밋: `fix(play): a run cut by a restart is compensated like a failed one; an event whose region is gone ends (V5, FR-C3, FR-C4)`

### Step 8 — 운영 문서
- [ ] 8.1 `aidlc-docs/operations/operations.md`
  - 워커 하나 문단(113~120행)에 짧은 쓰기 잠금을 덧붙인다.
  - `GM_WRITE_WAIT_S`를 적는다.
  - 124행의 재시작 처리를 고친다(보상, `interrupted_uncompensated`).
  - 273~276행의 끊긴 run 설명을 고친다.
- [ ] 8.2 `env.example`: `# GM_WRITE_WAIT_S=5` 한 줄.
- [ ] 8.3 커밋: `docs: GM writes in one worker, the wait limit, and restart compensation (V5)`

### Step 9 — 게이트와 요약
- [ ] 9.1 게이트: ruff·black, mypy ≤ 11, pytest 두 번(hypothesis 시드 둘), 바뀐 웹 없음 확인(`git diff --stat -- web` 비어 있음).
- [ ] 9.2 `construction/V5-gm-write-correctness/code/code-summary.md`
  - § 1 기준선과 결과
  - § 2 파일
  - § 3 BR·TP 대응
  - § 4 바뀐 기존 시험(§ 1.2 R-03 수)
  - § 5 이탈
  - § 6 알려진 한계(§ 1.1 R-05c, 지운 지역 소문의 되먹임)
  - § 7 다음에 넘김: V6에 `rumor_inactive`·`reason: region_removed`·`gm_busy` 문장, B&T에 운영자 확인 P1~P6과 § 1.2 R-01·R-04
- [ ] 9.3 커밋: `docs(aidlc): V5 code summary`

---

## 3. 요구 대응

| 요구 | 단계 | 회귀 |
|---|---|---|
| FR-C1 겹친 GM 쓰기(#9, #12, RE-P01, RE-P06, 몫) | 4, 5, 6 | TP-V5-1·2·3·9·10 |
| FR-C1 + Q3=A(RE-P05, RE-P07) | 4, 5 | TP-V5-11·12 |
| FR-C2 닫기(RE-P02) | 2, 5 | TP-V5-4·14·15 |
| FR-C3 끊긴 run(RE-P03) | 7 | TP-V5-5 |
| FR-C4 지운 지역의 사건(RE-P04) | 7 | TP-V5-6 |
| FR-C5 바쁨 표시(#5(a), RE-P12 일부) | 2 | TP-V5-8 |
| 완료 조건: 일괄 생성 5개 동시 | 5 | TP-V5-7 |
| NFR-6 PBT | 2 | 상태 기계 |
| NFR-10 겹침 재현 | 3~6 | 저장소별 표(NFR § 2.3) |

**규모**: 9단계, 커밋 9개. 새 시험 파일 6개(`tests/play/{concurrency,conftest,test_guard_machine,test_v5_overlap,test_v5_turns}.py`, `tests/api/test_v5_busy_api.py`). 고친 파일은 약 18개다. 시험은 약 40개를 더하고, 기존 단언 약 35곳을 고친다.
