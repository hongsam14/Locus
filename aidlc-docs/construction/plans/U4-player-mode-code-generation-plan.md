# U4 플레이어 모드 — Code Generation Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U4 — 플레이어가 캐릭터로 세션에 들어가 연결을 따라 이동하고, 행동이 턴을 흐르게 하며, 현재 지역을 한 화면에서 보는 것을 코드로 만든다. 턴 엔진은 행동을 받는 단일 진입점이 되고 예산·상한·가드·트랜잭션을 갖는다.

> 근거: `construction/U4-player-mode/functional-design/{domain-entities,business-logic-model,business-rules,frontend-components}.md`(승인 2026-09-30T01:19Z; 검토 02의 R-09~R-15는 Accepted risk → 아래 "이월 결정" 표), `construction/U4-player-mode/nfr/nfr-light.md`(승인 2026-09-30T01:44Z; 검토 01의 R-01~R-06 Accepted risk → 같은 표). 이 플랜이 코드 생성의 단일 기준이다.

---

## 유닛 컨텍스트

- **스토리**: US-3.1(캐릭터로 세션 시작), US-3.2(현재 지역 화면), US-3.3(연결을 따라 이동, 비용·막힌 길), US-3.4(행동 뒤 턴 요약) — 주. US-8.1(소문·LLM 폭주 상한), US-8.3(턴 원자성·동시성), US-1.4(LLM 없이 둘러보기: 플레이 부분), US-6.1(데모 시나리오의 이동 구간 기반).
- **의존**: U2(`WorldSnapshot`·`WorldCache`·`SnapshotSource`, NPC 모델, `LEVEL_RANK`). 뒤 유닛이 기대는 것: `TurnAdvancer.advance(session_id, action)`·`begin`(U5 EndTalk 확장, U6 Declare), `PlayService.current_region`(U5 대화 버튼 자리), `TurnGuard.assert_idle`(U7 GM 화면), `players`·`turn_runs` 테이블(U7 재배치·GM 상태), 타임라인 새 종류(U7 필터).
- **인터페이스(결과)**: `SessionService.start(world_id, PlayerCreate) -> (GameSession, Player)`, `PlayService.{current_region, act, turn_run, list_runs, log}`, `TurnAdvancer.{advance -> ActionResult, begin -> TurnRun}`, `RumorService.append_for_turn(...) -> list[SessionRumor]`(초안), `movement.{is_passable, move_cost, move_options, neighbours, validate_action}`, `LlmBudget`, `TurnGuard`, `TurnExecutor`(+`ThreadTurnExecutor`, `SyncTurnExecutor`), `PlayRepository.uow()` + `PlayerStore`·`TurnRunStore`.
- **DB 엔티티(PostgreSQL, 추가만)**: `players`(session_id UNIQUE), `turn_runs`. `init-schema --play`/`ensure_play_schema`가 만든다(idempotent).
- **바뀌는 외부 계약**: (1) `POST /api/play/worlds/{w}/sessions` — 본문 없음 = 지금처럼 200 `GameSession`; 본문 `{name, start_region_id}` = 201 `{session, player}`(FD R-09). (2) `POST /api/gm/sessions/{s}/advance` — 응답 `TurnResult` 그대로(필드 추가만), 진행 중이면 409. (3) GM 쓰기 라우트 — 진행 중이면 409(FD R-06). (4) `TurnAdvancer.advance` 반환형 `TurnResult` → `ActionResult`(P7; 호출처 24곳 + gm 라우트 1곳). (5) LLM 제공자가 없어도 `POST /api/gm/sessions/{s}/advance`는 **200**(지금은 503; `turns`가 항상 조립됨, Q6). 소문 생성·사건 제안 라우트의 503은 그대로. (6) `SessionService` 생성자 `(repo, graph_repo)` → `(repo, snapshots: SnapshotSource, guard: TurnGuard)`: GM `start_session`도 월드 존재·지역 목록을 `snapshots.get(world_id)`(LookupError → `WorldNotFoundError`, 404 유지)에서 얻는다. 호출처: `locus/play/wiring.py:66`, `locus/__main__.py::_session_service`, `tests/play/test_service.py::_service`(`FakeGraph` → 스냅샷 가짜), `tests/play/helpers.py::compose_play`(`_NullGraph` 제거), `tests/shared/test_wiring.py:104`.
- **바꾸지 않는 것**: 합의 계산, 소문·사건·승격·되먹임의 값 규칙, GM 수동 생성·재생성(상한 없음·즉시 저장), 프롬프트, 번역 저장소, `GET .../regions/{r}/knowledge`, 에디터·GM 화면(409 표시만 기존 오류 경로).

## 이월 결정 (FD 검토 02 R-09~R-15, NFR 검토 01 R-01~R-06 → 이 플랜에서 확정)
| 출처 | 결정 | 단계 |
|---|---|---|
| FD R-09 | 세션 시작 라우트 이중 응답(본문 없음 200 `GameSession` / 본문 201 `SessionStartOut{session, player}`). 기존 `tests/api/test_play_gm_api.py`·`test_localization_api.py`는 변경 없음. `web/src/SessionBar.tsx`의 "New Session" 버튼(`session-new-btn`, GM 세션 즉시 생성)과 그 테스트(`components.test.tsx` "lists sessions and starts a new one")는 그대로 두고, **별도 버튼** "플레이 시작"(`session-play-btn`)이 `NewSessionForm` 모달을 연다 | 8.2, 9.2, 9.4 |
| FD R-10 | 행동 검증은 **가드 안**에서 최신 플레이어 위치로: `movement.validate_action(snapshot, player, action, tuning)`을 `TurnAdvancer._start`가 가드 획득 뒤 호출(권위). `PlayService.act`의 사전 검증은 친절한 400용 | 4.1, 6.3 |
| FD R-11 | `begin`: `executor.submit` 실패 시 `_fail(run, exc)` + `guard.release`. 대기열의 실행도 `running`으로 보임(문서화) | 6.4 |
| FD R-12 | 상위 시그니처 이탈 목록을 code-summary "설계 이탈"에 완결(TurnGuard acquire/release, 단일 지역 `append_for_turn`, `exclude_knowledge_ids`, `store=`, `chain_degrees_for`, `turn_shutdown_timeout_s`, `SessionService(repo, snapshots, guard)`) | 11.2 |
| FD R-13 | `llm_calls` = 예약 호출 수(상한): `append_for_turn`이 `budget.take(n)`(5.1), `TurnResult.llm_calls = budget.used`(6.2). BR-U4-21 문구는 code-summary에 그렇게 기록; 테스트 이름도 `reserved` | 5.1, 6.2 |
| FD R-14 | `ThreadTurnExecutor` 워커는 데몬 스레드(`threading.Thread(daemon=True)` 기반 자체 큐 실행기, `ThreadPoolExecutor` 미사용) | 4.4 |
| FD R-15 / NFR R-01 | 지역당 활성 소문 상한 `max_active_rumors_per_region=20`. 활성 = `active=True`(승격 포함). 새 소문 수 `n = min(len(degrees), budget.remaining, max_new - len(out), cap - active_count)`; `cap - active_count <= 0`이면 `rumors_capped_regions`에 기록(예산 소진의 `rumors_skipped_regions`와 별개). TP: "턴은 지역을 `max(before, cap)` 위로 올리지 않는다" | 5.1, 5.2 |
| NFR R-02 | 회로 차단: 한 턴에서 생성기 체인이 요청한 degree 수보다 짧게 돌아오면(LLM 실패) `append_for_turn`이 `"llm_failed"`를 알리고(5.1), `_one_turn`이 그 턴의 남은 지역 초안을 포기하며 `TurnResult.llm_failed=True`(6.2). 호출당 최악 ≈ 97초(`retry.py` 30초 × 재시도 3회 + 백오프)를 operations.md에 적는다 | 5.1, 6.2, 10.2 |
| NFR R-03 | 응답성 수치는 목표. 오프라인 구조 단언: `act`는 LLM 스텁 0회·UoW 1개 | 8.4 |
| NFR R-04 | `tests/conftest.py`: hypothesis 프로파일 `locus`(`print_blob=True`, `deadline=None`) 등록·기본 적용; 재현은 `pytest --hypothesis-seed=<n>`(PBT-08) | 1.3 |
| NFR R-05 | env 5개: `PLAY_MAX_MOVE_COST`, `RUMOR_MAX_NEW_PER_REGION_TURN`, `LLM_MAX_CALLS_PER_TURN`, `RUMOR_MAX_ACTIVE_PER_REGION`, `TURN_SHUTDOWN_TIMEOUT_S`. 한 행동 상한 = `max_move_cost × max_llm_calls_per_turn` | 2.2, 10.1 |
| NFR R-06 | `get_run(session_id, run_id)`는 `run.session_id != session_id`면 None → 404 | 3.3, 3.4, 8.2 |
| NFR N-4 | `TURN_RUN_FAILED` payload는 `{run_id, error_type: type(exc).__name__}`만; 본문은 `logger.exception` | 6.4 |
| NFR-9 | 플레이어의 지역이 스냅샷에 없으면 `current_region`·`act`는 `LookupError("player region no longer exists")` → 404 | 7.2 |

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. 복사본·`_v2` 없음.
- 각 단계는 **그 단계의 테스트가 GREEN인 상태로** 끝낸다. 예외: 6단계(`advance` 반환형)는 6.5의 호출처 갱신까지 한 단계 안에서 끝낸다.
- 규칙 번호(BR-U4-n)·검증 번호(TP-U4-n, EX-n)를 테스트 이름이나 docstring에 적는다.
- 새 외부 의존 없음(스레드·hypothesis·SQLAlchemy Core 기존).
- 각 단계 완료 즉시 체크박스를 [x]로 바꾼다.

---

## Steps

### Step 1 — 베이스라인과 뼈대
- [x] 1.1 `./.venv/bin/python -m pytest -q --no-cov`(기대 388) / `cd web && npm test`(31) / `mypy locus api`(12) 실측을 `construction/U4-player-mode/code/code-summary.md` 초안에 기준선으로 기록.
- [x] 1.2 새 파일(전부 신규, 빈 docstring): `locus/play/errors.py`, `locus/play/player/__init__.py`, `locus/play/player/movement.py`, `locus/play/player/service.py`, `locus/play/turn/{budget,guard,executor,summary}.py`, `tests/conftest.py`, `tests/play/strategies.py`, `tests/play/test_movement.py`, `tests/play/test_turn_guard.py`, `tests/play/test_player_mode.py`, `tests/api/test_play_api.py`, `web/src/features/play/`(디렉터리), `web/src/__tests__/play.test.tsx`.
- [x] 1.3 `tests/conftest.py`(신규): hypothesis 프로파일 `locus`(`print_blob=True`, `deadline=None`) 등록 + `settings.load_profile("locus")`(NFR R-04). 전체 `pytest -q --no-cov`가 기준선 388 그대로 GREEN인지 확인(프로파일이 모든 테스트에 적용되므로 부분 실행으로 끝내지 않는다).

### Step 2 — 모델·조정값·설정 (domain-entities §1~2)
- [x] 2.1 `locus/play/models.py`: `Player`, `PlayerCreate`(name 1~40, start_region_id), `MoveAction`/`WaitAction`/`EndTalkAction` + `PlayerAction = Annotated[Union[...], Field(discriminator="type")]`, `MoveOption`, `TurnRunStatus`(running/done/failed), `TurnRun`, `RegionView`(`facts`/`hearsay`는 `KnowledgeView`, `rumors`는 `SessionRumor`), `ActionResult`(`player: Player | None`), `TimelineKind += SESSION_STARTED, SESSION_CLOSED, PLAYER_MOVED, PLAYER_WAITED, TURN_RUN_FAILED`(끝에 추가), `RegionTurnChange.region_name: str = ""`. `locus/play/turn/advancer.py::TurnResult += llm_calls: int = 0, budget_exhausted: bool = False, llm_failed: bool = False, rumors_skipped_regions: list[str] = [], rumors_capped_regions: list[str] = []`. `ActionResult`는 `TurnResult`를 참조하므로 순환을 피해 `TurnResult`를 `models.py`로 옮기고 `advancer.py`는 re-export(gm 라우트 import 유지).
- [x] 2.2 `locus/shared/config/tuning.py::PlayTuning += max_move_cost: int = 5, max_new_rumors_per_region_turn: int = 2, max_llm_calls_per_turn: int = 8, max_active_rumors_per_region: int = 20`; env 연결은 기존 방식 그대로: `locus/shared/config/settings.py`의 `Settings`에 alias 필드 4개(`PLAY_MAX_MOVE_COST`, `RUMOR_MAX_NEW_PER_REGION_TURN`, `LLM_MAX_CALLS_PER_TURN`, `RUMOR_MAX_ACTIVE_PER_REGION`)를 더하고 `settings.py:109`의 `PlayTuning(...)` 생성부에 넘긴다. `Settings += turn_shutdown_timeout_s: float = Field(30.0, alias="TURN_SHUTDOWN_TIMEOUT_S")`.
- [x] 2.3 테스트: `tests/play/test_models.py` — 새 모델 왕복, `PlayerAction` 판별(모르는 type → ValidationError), `TurnResult` 기본값으로 기존 생성 호환(BR-U4-29), `PlayTuning` 기본값·env 로딩.

### Step 3 — 포트·저장소 (domain-entities §3~4; NFR R-06)
- [x] 3.1 `locus/play/ports.py`: `PlayerStore`, `TurnRunStore`(`create_run`, `get_run(session_id, run_id)`, `update_run`, `list_runs(session_id, status=None)`, `fail_stale_runs(*, reason) -> int`), `PlayUnitOfWork += players, runs`, `PlayRepository += PlayerStore, TurnRunStore` + `def uow(self) -> PlayUnitOfWork`.
- [x] 3.2 `locus/play/storage/schema.py`: `players`, `turn_runs` 테이블(domain-entities §3 열; `action`·`result` JSON, `status` 인덱스). `ensure_play_schema`가 만든다.
- [x] 3.3 `locus/play/storage/postgres_repo.py`: 모든 SQL을 `_PgStores(conn)`(store 프로토콜 전부 + players/runs)로 옮기고, `PostgresPlayRepository`의 SQL을 실행하는 공개 메서드 전부(현재 24개 공개 메서드 중 `connect/disconnect/health_check/ensure_schema`를 뺀 것)는 `with self._engine.begin() as conn: return _PgStores(conn).<m>(...)` 한 형태가 된다. `uow()`는 `engine.begin()`을 열어 `_PgStores(conn)`를 UoW로(`__exit__`가 트랜잭션을 닫음). `get_run`은 세션 불일치면 None. `fail_stale_runs`는 `status='running'` → `failed`, `error=reason`, `finished_at=now`.
- [x] 3.4 `locus/play/storage/memory_repo.py`: `threading.RLock` 전역, 모든 메서드 락, `players`/`runs` dict, `uow()` = 락 보유 + `copy.deepcopy` 스냅샷, 예외 시 복원(`__exit__`에서 락 해제). 뷰 객체는 리포지토리 자신(같은 메서드).
- [x] 3.5 테스트: `tests/play/test_repository_contract.py` 확장(두 어댑터 공통: players CRUD·UNIQUE, runs CRUD·세션 불일치 None·`fail_stale_runs`, `uow` 커밋/롤백 EX-19); `tests/play/test_postgres_repo.py` sqlite로 `uow` 롤백 후 아무 행 없음; `tests/play/test_turn_guard.py`에 EX-20(인메모리: 스레드 A 롤백이 스레드 B의 쓰기를 지우지 않음).

### Step 4 — 순수 규칙: 이동·예산·가드·실행기·요약 (BLM §2, §4.5, §5, §10)
- [x] 4.1 `locus/play/player/movement.py`: `is_passable`, `move_cost`, `move_options`, `neighbours`, `validate_action(snapshot, player, action, tuning) -> MoveOption | None`(Move: 인접·통과 가능 아니면 `InvalidActionError`; EndTalk: NPC 존재; Wait: None). `InvalidActionError(ValueError)`는 `locus/play/models.py` 옆 `locus/play/errors.py`(신설; `TurnInProgressError`도 여기).
- [x] 4.2 `locus/play/turn/budget.py::LlmBudget(max_calls)`: `remaining`, `take(n)`, `used`, `exhausted`.
- [x] 4.3 `locus/play/turn/guard.py::TurnGuard`: `acquire(session_id, run_id)`, `release`, `is_running`, `assert_idle`.
- [x] 4.4 `locus/play/turn/executor.py`: `TurnExecutor(Protocol)`(`submit(fn, *args)`, `shutdown(timeout)`), `ThreadTurnExecutor`(데몬 워커 1개 + `queue.Queue`; `shutdown`은 센티널 넣고 `join(timeout)`; 종료 뒤 `submit`은 `RuntimeError`), `SyncTurnExecutor`(즉시 실행).
- [x] 4.5 `locus/play/turn/summary.py`: `merge_changes(results)`, `scope_changes(changes, snapshot, player_region_id | None)`, `narrate(changes)`.
- [x] 4.6 `tests/play/strategies.py`(PBT-07): `connections()`, `topologies()`, `snapshots()`(U2 `tests/world/strategies.py` 재사용), `sessions_with_rumors()`. 테스트: `test_movement.py` TP-U4-1/2(hypothesis) + EX-4(연결 안 됨) + 최소 비용 선택(BR-U4-9); `test_turn_guard.py` TP-U4-6(스레드 N개, 정확히 1개 성공); `test_player_mode.py`에 `LlmBudget`·`summary` 단위(EX-14: 이웃 아닌 지역 제외, 플레이어 없음 = 전부).

### Step 5 — 소문 초안·되먹임 (BLM §4.4; FD R-13/R-15, NFR R-01/R-02)
- [x] 5.1 `locus/play/rumor/service.py`: `chain_degrees_for(distortion)`(모듈 함수; `_chain_degrees`가 사용), `_collect_sources(..., exclude_knowledge_ids: set[str] = frozenset())`, `append_for_turn(session, region_id, *, distortion, budget, max_new, max_active, min_source_support) -> tuple[list[SessionRumor], str | None]`(둘째 값: `None` | `"capped"` | `"budget"` | `"llm_failed"`) — 저장 없음; `n = min(len(degrees), budget.remaining, max_new - len(out), max_active - active_count)`; 체인이 `n`보다 짧으면 `llm_failed` 반환(회로 차단은 호출자). `append_for_region`·`_generate_for_region`은 변경 없음.
- [x] 5.2 `locus/play/rumor/feedback.py::apply_feedback(session, active_rumors, *, store: DistortionStore | None = None)` — `store or self._repo`로 쓴다(기존 호출 호환).
- [x] 5.3 테스트: `tests/play/test_player_mode.py` TP-U4-3/4/5 + 활성 상한 TP("after ≤ max(before, cap)"; 시작 상태 21로 GM 예외 케이스 포함) + EX-11(수치: 턴마다 새 소문 2·예약 호출 2, 4턴 뒤 활성 ≤ 8; `budget=1`이면 1·`budget_exhausted`) + 회로 차단(가짜 생성기가 1개만 돌려주면 `llm_failed`, 남은 지역 건너뜀); 기존 `test_rumor_*`·`test_rumor_generator.py` 변경 없음 GREEN(`test_service.py`는 7.1에서 스냅샷 가짜로 갱신).

### Step 6 — 턴 엔진 (BLM §4; FD R-10/R-11, NFR N-4)
- [x] 6.1 `locus/play/turn/advancer.py`: `_apply_active_events` → `compute_event_application(session) -> _EventApplication`(+`distortions`, `event_updates`, `timeline`; 쓰기 없음). `TurnAdvancer.__init__(repo, snapshots, rumors: RumorService | None, feedback, guard, executor, params)`; `llm_available` 속성.
- [x] 6.2 `_one_turn(session, budget, promotion_threshold) -> TurnResult`: (a) 계산 (b) 초안(예산 소진 → skipped, 상한 → capped, 실패 → `llm_failed` 뒤 나머지 지역 포기) (c) UoW 하나(사건·왜곡도·타임라인·초안 upsert → `apply_feedback(store=u.distortions)` → evolve/decay/prune/promote → upsert → bump → ADVANCE_TURN). `shape_region_changes(..., region_names=)`(`locus/play/turn/changes.py` 인자 추가, 기본 `{}`).
- [x] 6.3 `_start(session_id, action) -> TurnRun`: `require_open` → 가드 획득 → **가드 안에서** `player = repo.get_player`, `validate_action`(FD R-10) → UoW(위치·turns_spent·PLAYER_MOVED/WAITED·`create_run`); 실패 시 가드 해제 후 재발생.
- [x] 6.4 `advance(session_id, action=None, *, promotion_threshold) -> ActionResult`(동기; `_start` → `try: _run_turns; run done 저장 / except: _fail 후 재발생 / finally: guard.release` — 정상 종료도 `finally`에서 해제), `begin(session_id, action, *, promotion_threshold) -> TurnRun`(`_start` 뒤 `executor.submit` 실패 → `_fail` + `guard.release` 후 재발생, FD R-11), `_run(run_id)`(같은 try/except/finally, 예외는 삼키고 로그), `_run_turns`, `_fail`(payload `{run_id, error_type}`; `logger.exception`). `run_now` 없음(테스트는 `SyncTurnExecutor`).
- [x] 6.5 호출처 갱신: `tests/play/test_advance_turn.py` 21곳, `tests/play/test_play_services.py` 3곳 → `advance(...).turns[-1]`(헬퍼 `_turn(adv, sid, **kw)` 하나로); `api/routers/gm.py:179` → `.turns[-1]`. 기존 단언 불변.
- [x] 6.6 테스트(`tests/play/test_player_mode.py`, `SyncTurnExecutor` + 인메모리): EX-5(Move 즉시 위치·PLAYER_MOVED·run), EX-6(Wait/EndTalk/GM 1턴), TP-U4-7(길이·턴 번호), EX-8(running 중 `begin`·`advance` 409 — `ThreadTurnExecutor` + 느린 가짜 생성기로 1건), EX-9(둘째 턴 예외 → 첫 턴 커밋·failed·`TURN_RUN_FAILED` payload에 `error_type`만·가드 해제), EX-10(`fail_stale_runs`), EX-16(`rumors=None` → done·`llm_available=False`), EX-17(플레이어 없는 세션 GM advance → `player=None`·changes 전부), R-10 경쟁(검증이 낡은 위치를 거부), R-11(`submit` 거절 → failed·가드 해제).

### Step 7 — 세션·플레이어 서비스 (BLM §1, §3; NFR-9)
- [x] 7.1 `locus/play/session_service.py`: `SessionService(repo, snapshots: SnapshotSource, guard: TurnGuard)`(`graph_repo` 제거). 월드 존재·지역 목록은 `snapshots.get(world_id)`에서: `LookupError` → `WorldNotFoundError`(LookupError 하위, 404 매핑 그대로). `start(world_id, player: PlayerCreate) -> tuple[GameSession, Player]`(UoW 하나: 세션·플레이어·`snapshot.topo.regions` 왜곡도 기본값·SESSION_STARTED). `start_session(world_id)` 유지(GM 세션; 같은 스냅샷 지역으로 왜곡도 초기화, 트랜잭션도 UoW 하나로 통일). `close_session`: `guard.assert_idle` → 닫기 + SESSION_CLOSED. 호출처 전수 갱신: `locus/play/wiring.py`(`SessionService(repo, knowledge.cache, guard)`; `shared.graph` None 검사 제거 — play는 그래프를 더 쓰지 않는다), `locus/__main__.py::_session_service`(`assemble_knowledge(shared).cache`를 넘기고 `TurnGuard()` 새로; `shared.graph is None`이면 지금처럼 None), `tests/play/test_service.py::_service`(`FakeGraph(regions)` → `regions` dict로 `snapshot_of`를 만드는 `FakeSnapshots`; 없는 월드 테스트는 `LookupError`를 내는 가짜로 `WorldNotFoundError` 단언 유지), `tests/play/helpers.py`(`_NullGraph`·`compose_play(graph=)` 제거, `SharedContainer(graph=None)`), `tests/shared/test_wiring.py:104`(그대로 동작하는지 확인).
- [x] 7.2 `locus/play/player/service.py::PlayService(repo, snapshots, params, guard, turns, tuning)`: `current_region`(플레이어 없음 400 `InvalidActionError`; 지역 없음 → `LookupError` 404), `act`(사전 검증 400 → `turns.begin`), `turn_run`(None → LookupError 404), `list_runs`, `log`(타임라인 전체).
- [x] 7.3 테스트: EX-1(UoW 원자성: 저장소 실패 흉내 → 세션·플레이어·타임라인 없음; 시작 지역 없음 400), EX-2(왜곡도 행 없는 지역 기본값·행 생성 없음), EX-3(running 중 close 409), EX-13(`RegionView` 필드), EX-15(로그 전체·새 종류), NFR-9(지역 삭제된 스냅샷 → 404), `test_session_query.py`·`test_play_services.py` GREEN.

### Step 8 — 조립·API (BLM §8; FD R-09/R-06, NFR R-03/R-06)
- [x] 8.1 `locus/play/wiring.py`: `PlayContainer += play: PlayService, guard: TurnGuard, executor: TurnExecutor`; `turns: TurnAdvancer`(Optional 아님)·`feedback`은 항상 조립 — `assemble_play`의 `if generator is None: return container` 조기 반환을 없애고 `rumors`/`events`만 generator/suggester 유무에 따라 None. `assemble_play(..., executor: TurnExecutor | None = None)` 기본 `ThreadTurnExecutor`. `gm.py`의 `_need(p.turns, "turn engine")` 제거. 갱신할 테스트: `tests/shared/test_wiring.py:108-113` → `play.turns is not None`, LLM 없는 `advance` **200**(소문 생성 503은 그대로). `api/main.py` lifespan: 시작 시 `if containers.play is not None: containers.play.repo.fail_stale_runs(reason="interrupted")`, 종료 시 같은 방어 뒤 `executor.shutdown(settings.turn_shutdown_timeout_s)`. `api/errors.py`: `http_error`에 `TurnInProgressError` → 409 추가(`InvalidActionError`는 ValueError 하위라 400 자동); `PLAY_ERRORS = (LookupError, SessionClosedError, TurnInProgressError, ValueError)` 튜플을 정의하고 `api/routers/gm.py`의 `except (LookupError, SessionClosedError[, ValueError])` 10곳(106·122·137·154·180·215·229·243·257·266행)을 `except PLAY_ERRORS as exc: raise http_error(exc)`로 통일; 새 play 라우트도 같은 튜플. `_idle(session_id, p)` 의존성은 `guard.assert_idle`의 `TurnInProgressError`를 `http_error`로 바꿔 409.
- [x] 8.2 `api/routers/play.py`: `POST /worlds/{w}/sessions`(본문 `PlayerCreate | None`; 없음 → 200 `GameSession`, 있음 → 201 `SessionStartOut`), `GET /sessions/{s}/player`, `GET /sessions/{s}/region`(`RegionViewOut`, localization enrich: facts/hearsay `statement_ko`, rumors `statement_ko`, 지역 이름 `region_name_ko`), `POST /sessions/{s}/act`(202 `TurnRun`), `GET /sessions/{s}/turn-runs`·`/{id}`, `GET /sessions/{s}/log`. `api/schemas.py`: `SessionStartOut`, `RegionViewOut`, `TurnRunOut`(result 포함). `api/routers/gm.py`: `_idle(session_id, p)` 의존성을 소문 생성/재생성/지지도/왜곡도/사건 생성·승인·해결·삭제 라우트에 추가; advance는 `.turns[-1]`.
- [x] 8.3 `api/deps.py`: 테스트용 실행기 주입은 `compose_play(executor=SyncTurnExecutor())`(`tests/api/play_fixtures.py`).
- [x] 8.4 테스트: `tests/api/test_play_api.py` — 세션 시작 두 형태(R-09), region 200(번역 필드)·플레이어 없음 400, act 202 → 폴링 done(동기 실행기라 즉시), 잘못된 행동 400, 닫힌 세션 409, running 중 409(가드를 직접 잡아 흉내), 다른 세션 run id 404(R-06), log, NFR R-03 구조 단언(`act` 동안 LLM 스텁 호출 0·`uow()` 호출 1), GM 쓰기 라우트 409(running 흉내), GM `advance` running 중 409, LLM 없는 컨테이너에서 advance 200(`test_wiring.py` 갱신과 짝). 기존 `test_play_gm_api.py`·`test_localization_api.py` 변경 없음 GREEN.

### Step 9 — 프론트엔드 (frontend-components.md)
- [x] 9.1 `web/src/types.ts`: `Player`, `PlayerCreate`, `PlayerAction`, `MoveOption`, `RegionView`, `TurnRun`, `ActionResult`, `RegionTurnChange.region_name`, `TurnResult` 추가 필드, `SessionStartOut`.
- [x] 9.2 `web/src/api/play.ts`: `startSession(worldId, body?)`(오버로드: body 없으면 `GameSession`, 있으면 `SessionStartOut`), `getPlayer`, `getRegion`, `act`, `getTurnRun`, `listTurnRuns`, `getLog`. `SessionBar.tsx`의 기존 호출은 그대로.
- [x] 9.3 `web/src/features/play/`: `summary.ts`(`changeSummary` — `SessionPanel.tsx`에서 옮겨 공유, 기존 import 갱신), `RegionScene.tsx`, `MovePanel.tsx`, `ActionBar.tsx`, `PlayLog.tsx`, `LlmBanner.tsx`, `NewSessionForm.tsx`(모달: 이름·시작 지역 select). `web/src/i18n.ts`: 새 타임라인 종류 템플릿(`region_name` 사용) + 라벨.
- [x] 9.4 `web/src/routes/PlayPage.tsx`: placeholder 교체(상태·로드·행동·폴링 700ms·stale 방지·토스트는 기존 `NotificationCenter`). `web/src/SessionBar.tsx`: 기존 "New Session"(`session-new-btn`, GM 세션 즉시 생성 → `onSelect`)은 **그대로**; 옆에 "플레이 시작"(`session-play-btn`) 버튼을 더해 `NewSessionForm` 모달을 연다(이름·시작 지역 필수 → `startSession(worldId, body)` 201 → `navigate(\`/play/${session.id}\`)`). 지역 목록은 `EditorPage`가 `regions` prop으로 넘긴다(`SessionBar` props 확장, 기본 `[]`).
- [x] 9.5 테스트(`web/src/__tests__/play.test.tsx` 신설): PlayPage 로드 표시(EX-13), Move 클릭 → `act`·`getRegion` 즉시 재조회·폴링 done 토스트(EX-7), 409 토스트, 배너(EX-16), blocked 옵션 비활성(TP-U4-2 UI), NewSessionForm 필수값·이동. `tsc --noEmit`·`vite build` 클린.

### Step 10 — 문서·환경 (NFR-8, NFR R-02/R-05)
- [x] 10.1 `env.example`: env 5개(설명 한 줄씩). `docker-compose.yml` 변경 없음(단일 워커 그대로).
- [x] 10.2 `aidlc-docs/operations/operations.md`: 플레이어 모드 절 — 배경 실행기(데몬 워커 1, 종료 대기 30초), 시작 시 `interrupted` 정리, 가드·409, 예산·상한 5개, LLM 장애 시 최악 시간(호출당 ≈ 97초, 턴당 회로 차단, 한 행동 ≤ `max_move_cost × 97초`), 대기열 표시 한계. `CLAUDE.md` Status/CLI-API 한 줄, `README`는 U8.

### Step 11 — 검증·요약
- [x] 11.1 전체: `pytest -q --no-cov`(기존 388 + 신규 전부 GREEN, 회귀 0), `cd web && npm test`, `ruff check`, `black --check`, `mypy locus api`(≤ 12), `tsc --noEmit`, `vite build`, `docker build`(이미지 빌드만). 라이브(Neo4j/PG) 시나리오는 운영자 실행으로 남기고 명령을 code-summary에 적는다(응답성 목표 측정 포함).
- [x] 11.2 `construction/U4-player-mode/code/code-summary.md`: 기준선/결과 수치, 파일 목록, 설계 이탈 완결 목록(FD R-12 + 위 표의 확정값), 이월 결정별 구현 위치, 남긴 것(U5·U7 인계: EndTalk 대화, 로그 필터, `sync_regions`, 재배치 UI).
- [x] 11.3 코드 게이트 제시 → 승인 뒤 `/code-review`(전 U 단계와 같은 절차).
