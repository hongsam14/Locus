## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 — U4 플레이어 모드
**Reviewed artifact:** `aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-09-30T01:49:52Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 7.1 (+ Step 5.3, Step 8.3) | `SessionService(repo, graph_repo)` → `(repo, snapshots, guard)` 변경의 호출처가 불완전하다. 실제 생성자 호출: `locus/play/wiring.py:66`(플랜 포함), `locus/__main__.py:81`(CLI `_session_service`: `list_sessions`/`close_session`만 쓰는 곳 — 스냅샷 소스도 프로세스 내 가드도 없음, 플랜에 없음), `tests/play/test_service.py:29`(`SessionService(repo, FakeGraph(regions))`; 파일 전체가 이 서비스 테스트이고 `WorldNotFoundError`를 `:48`에서 기대) — 그런데 Step 5.3은 `test_service.py` "변경 없음 GREEN"이라 적고 Step 7은 이 파일을 갱신하지 않는다. `_NullGraph`는 `tests/api/play_fixtures.py`가 아니라 `tests/play/helpers.py:32`에 있고, `compose_play(graph=)` 인자와 `play_fixtures.py`의 `graph=GraphRepo()`·`tests/shared/test_wiring.py:104`의 `SharedContainer(graph=GraphRepo())`가 함께 걸린다. 또 `start_session`의 왜곡도 시드 지역 목록이 지금은 그래프 `find_nodes`인데 "지금 방식"이라며 `graph_repo`를 제거하므로 지역 출처(스냅샷 `regions_by_id`)와 빈 월드/없는 월드의 오류 계약(`WorldNotFoundError` → 404 vs 스냅샷 `LookupError`; `api/routers/play.py:24`는 `WorldNotFoundError`만 잡음)이 결정되지 않았다. | 7.1에 호출처 전수(wiring, `__main__.py:81`, `tests/play/test_service.py`, `tests/play/helpers.py`, `tests/api/play_fixtures.py`, `tests/shared/test_wiring.py`)와 각각의 처리를 적는다. CLI가 가드/스냅샷 없이 쓰는 경로(닫기·목록)를 어떻게 구성할지(예: 가드 선택 인자, 또는 CLI는 `repo` 직접 사용) 확정한다. GM `start_session`의 지역 출처와 없는 월드 오류 매핑을 명시하고, 5.3의 "test_service.py 변경 없음" 문구를 정정한다. `_NullGraph` 위치를 바로잡는다. | New |
| R-02 | Major | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 8.1 / 8.4 | "`turns`는 항상 조립(`rumors` None 허용)", "LLM 없는 컨테이너에서 advance 200"은 기존 계약의 뒤집기다. 기존 `tests/shared/test_wiring.py:108-113`가 `play.turns is None`과 `POST /api/gm/sessions/{sid}/advance == 503`을 단언한다(`assemble_play`의 `if generator is None: return container` 조기 반환이 그 근거). 플랜은 이 테스트를 어디에서도 갱신 대상으로 적지 않았고, "바뀌는 외부 계약"(§유닛 컨텍스트)에도 "LLM 없는 advance 503→200"이 없다. 조기 반환 구조 재배치도 지시가 없다. | 외부 계약 목록에 "LLM 없는 advance 503 → 200(rumors=None)"을 추가하고 근거 FD/US-1.4 조항을 적는다. 갱신할 기존 테스트(`tests/shared/test_wiring.py`)와 `assemble_play` 조기 반환 제거 방식을 8.1/8.4에 명시한다. | New |
| R-03 | Major | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 8.1 / 8.2 (`api/errors.py`, `api/routers/gm.py`) | `TurnInProgressError`/`InvalidActionError`를 `http_error`에 매핑해도 라우터의 `except` 절이 잡지 않으면 500이다. `api/routers/gm.py:179-180` advance는 `except (LookupError, SessionClosedError)`만 잡고(같은 패턴이 `:106,122,137,154,215,229,243,257,266`), 플랜은 advance에 `.turns[-1]`만 적는다. 플랜이 약속한 "진행 중이면 409"(§바뀌는 외부 계약 2)와 `TP-U4-6`의 409는 이대로면 구현되지 않는다. 또한 `http_error`는 알 수 없는 예외를 `raise exc`한다. `_idle` 의존성이 `HTTPException`을 던지는지 `TurnInProgressError`를 던지는지도 미정이다. | 8.2에 `advance` 및 새 `play.py` 라우트의 `except` 튜플에 `TurnInProgressError`·`InvalidActionError` 추가(또는 공통 처리)를 명시하고, `_idle`이 던지는 예외 유형과 변환 지점을 정한다. 8.4에 `POST /api/gm/sessions/{s}/advance` running 중 409 테스트를 넣는다(현재 목록은 act/GM 쓰기 라우트만). | New |
| R-04 | Major | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > 이월 결정 FD R-09 행 vs Step 9.4 | FD R-09 확정은 "`web/src/SessionBar.tsx` 변경 없음"인데 9.4는 `EditorPage.tsx`/`SessionBar.tsx`의 "New Session"을 `NewSessionForm` 모달로 바꾼다고 적어 자기모순이다. 기존 `web/src/__tests__/components.test.tsx:141-149`는 `session-new-btn` 클릭 직후 `startSession("w")`가 호출되고 `onSelect`가 불리길 기대한다. 모달이 앞에 서면 이 테스트가 깨지는데 9.5는 신규 `play.test.tsx`만 적고 기존 테스트 갱신을 적지 않았다. "비우면 기존 GM 세션" 경로가 모달의 어떤 동작인지(빈 값 제출 허용? 별도 버튼?)도 불명확해 개발자가 추측해야 한다. | 9.4에서 SessionBar의 GM 세션 시작 버튼은 그대로 두고 플레이어 세션은 별도 진입(별도 버튼 또는 EditorPage 쪽)으로 두는 안, 또는 기존 테스트 갱신을 명시하는 안 중 하나로 정한다. 이월 결정 표의 "변경 없음" 문구와 9.4를 일치시키고 정확한 UI 동작(빈 값 제출 처리)을 적는다. | New |
| R-05 | Minor | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 1.2 / 1.3 | `tests/conftest.py`는 현재 없다(`ls tests`). 1.3이 "등록"이라 적어 기존 파일 수정처럼 읽히고 1.2의 신규 파일 목록에도 없다. 또 `tests/api/play_fixtures.py`·`tests/play/helpers.py` 갱신이 여러 단계에 흩어져 있다. | 1.2에 `tests/conftest.py`를 신규로 선언한다. 프로파일 등록이 기존 PBT의 deadline 동작을 바꾸므로 확인 범위를 `tests/world tests/shared` 외에 `tests/play tests/knowledge`까지 넓힌다. | New |
| R-06 | Minor | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 3.3 | "(11곳 정리)"는 검증되지 않는다. `postgres_repo.py`의 공개 저장 메서드는 20개(`create_session`…`delete_event`)이고 `begin()`/`connect()`가 각 11회 나오나 메서드 수와 다르다. 모든 SQL을 `_PgStores`로 옮기는 지시이므로 숫자는 오해를 부른다. | "11곳"을 지우거나 실제 대상(20개 메서드, 헬퍼 `_upsert_rumor_conn` 포함)으로 정정한다. | New |
| R-07 | Minor | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > 이월 결정 표 "단계" 열 | 단계 매핑이 실제 구현 위치와 어긋난다. FD R-13(`llm_calls` = 예약 호출 수)은 5.2가 아닌 `_one_turn`(6.2)에서 채워지고 5.2는 `apply_feedback(store=)`이다. NFR R-02의 회로 차단 호출자는 6.2이다(5.1은 `llm_failed` 반환만). code-summary "이월 결정별 구현 위치"(11.2)가 이 표를 따르면 틀린 위치가 기록된다. | 표의 단계를 실제 구현 단계(R-13→6.2, R-02→5.1+6.2 등)로 고친다. | New |
| R-08 | Minor | aidlc-docs/construction/plans/U4-player-mode-code-generation-plan.md > Step 8.1 (lifespan) / Step 6.4 | lifespan의 `play.repo.fail_stale_runs`는 `containers.play`가 None(assemble 실패)일 때의 처리가 없다(`api/main.py`의 `_try`가 None을 돌려줄 수 있음). 6.4의 동기 `advance`가 가드를 성공/실패 어느 경로에서 해제하는지도 `_start`의 "실패 시 해제"만 적혀 있어 정상 종료 해제가 명문화되어 있지 않다. | 8.1에 play None 방어를 한 줄 추가하고, 6.4에 `advance`(동기) 종료 시 `finally: guard.release`를 명시한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `advance(` 호출처(§Step 6.5: 24곳 + gm 1곳) | `test_advance_turn.py` 21, `test_play_services.py` 3, `api/routers/gm.py:179` 1 | 일치 |
| 플랜이 명명한 기존 경로 존재(models.py, ports.py, storage/{schema?,postgres_repo,memory_repo}, turn/{advancer,changes}, rumor/{service,feedback}, session_service, wiring, settings.py, tuning.py, api/*, web/src/*) | `git ls-files` 상 `locus/play/storage/schema.py`는 tracked에 없음(Step 3.2가 "만든다"로 신규 취급, 기존 `ensure_play_schema` 위치는 미확인); 나머지 존재 | 3.2가 신규/기존을 선언하지 않음(경미) |
| `SessionService(` 생성자 호출처 | wiring:66, `__main__.py:81`, `tests/play/test_service.py:29` | 플랜은 wiring만 커버 → R-01 |
| `_NullGraph` 위치 | `tests/play/helpers.py:32` (플랜은 `tests/api/play_fixtures.py`) | 경로 오류 → R-01 |
| `tests/shared/test_wiring.py` 기대 | `play.turns is None`, advance 503 | Step 8.1과 충돌 → R-02 |
| `gm.py` except 튜플 | advance 포함 10곳 모두 `LookupError`/`SessionClosedError` 위주 | 409/400 미변환 → R-03 |
| `components.test.tsx:141-149` | `session-new-btn` → `startSession("w")` 즉시 호출 기대 | 9.4 모달과 충돌 → R-04 |
| `PlayUnitOfWork`/`uow()` 존재 | `ports.py`에 Protocol만 있고 구현·`uow()` 없음 | 3.1 "+= players, runs"는 타당 |
| `TurnResult` 순환 회피 이동 | `RegionTurnChange`는 `models.py:209`, `locus/play/__init__.py`가 advancer에서 re-export | 이동 후 re-export로 호환 가능 |
| `Settings.play_tuning()`(`settings.py:~109`), `PlayTuning` 필드 | 존재, 신규 4필드 충돌 없음 | OK |
| 스토리 커버리지 US-3.1~3.4, 8.1, 8.3, 1.4 | Step 2~9에 대응 단계 있음 | OK |
| 이월 R-10/R-11/R-14/R-15, NFR R-01~R-06 | 각각 단계·구현 지시 존재(단계 번호 일부 부정확 → R-07) | 종결됨 |

### Summary
승인된 FD/NFR의 이월 결정은 대체로 닫혔으나, 플랜이 스스로 약속한 "기존 테스트 변경 없음"·"409/400 매핑"과 실제 코드가 어긋난다. `SessionService` 시그니처 호출처(CLI·test_service·helpers), LLM 없는 advance 503→200 계약 뒤집기, 라우터 except 절, SessionBar 모달 충돌이 미처리라 Major 4건으로 NOT-READY이며, 고치면 구조 변경 없이 플랜 수정만으로 해소된다.
