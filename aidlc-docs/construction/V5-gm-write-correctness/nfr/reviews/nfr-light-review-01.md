## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements + NFR Design (light) — V5 GM write correctness
**Reviewed artifact:** `aidlc-docs/construction/V5-gm-write-correctness/nfr/nfr-light.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-08T06:25:40Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V5-gm-write-correctness/nfr/nfr-light.md > § 3 (P1~P3, 도입 문장 "PostgreSQL의 행 잠금") | 운영자 확인 P1~P3은 PostgreSQL 행 잠금(`FOR UPDATE`, `postgres_repo.py:337,365`)을 확인하지 못한다. 고친 뒤에는 모든 GM 쓰기가 워커 하나 안의 세션별 짧은 쓰기 잠금(§ 1.1, `docker-compose.yml:147-148`의 `--workers 1`)에서 먼저 차례로 서므로 두 요청이 DB까지 겹쳐 오지 않는다. 또 `curl … &` 두 개는 밀리초 단위 창을 맞추지 못해 고치기 전 코드에서도 대개 통과한다. 그래서 P1~P3의 "바른 결과"는 잠금이 있어도 없어도 같고, NFR-10(요구사항 228행)이 남긴 "PostgreSQL 실제 잠금 운영자 확인"을 충족한다는 문장이 근거가 없다. | P1~P3을 "실제 스택 스모크(프로세스 안 잠금 + 실제 DB 경로가 깨지지 않음)"로 이름을 고치거나, 실제로 잠금을 시험하려면 방법을 정한다(예: 해소 직전에 `psql`로 사건 행을 `SELECT … FOR UPDATE`로 잡아 둔 채 요청해 지연이 생기는지 보기, 또는 `GM_WRITE_WAIT_S`를 길게 하고 반복 N회). 어느 쪽이든 "고치기 전 코드에서도 통과할 수 있다"는 한계를 적는다. | New |
| R-02 | Minor | nfr-light.md > § 2.1 마지막 항목 | "두 저장소 모두 `test_repository_contract.py`의 매개변수 방식을 따른다(픽스처 하나가 둘을 낸다)"고 하나, 그 파일의 기존 `any_repo` 픽스처(`test_repository_contract.py:366-377`)는 SQL 쪽을 `create_engine("sqlite://")`(메모리)로 만든다. 같은 문서가 이 방식을 스레드 시험에 쓰지 말라고 한다. 파일 SQLite 픽스처는 새로 만들어야 하고, 계약 시험(`list_running_runs`)은 기존 `any_repo`로 충분하다. 개발자가 `any_repo`를 고쳐 쓰면 다른 계약 시험이 파일 DB로 바뀐다. | 파일 SQLite 픽스처를 새로 만든다고 적고(예: `threaded_repo`), 계약 시험은 `any_repo`에 둔다고 구분한다. | New |
| R-03 | Minor | nfr-light.md > § 1 NFR-1 행 ("바뀌는 단언은 셋뿐") | 셋이라는 수를 확인할 수 없다. 테스트에서 `is_running`/`assert_idle` 호출은 23곳(`test_player_mode.py` 15, `test_turn_guard.py` 7, `test_play_api.py` 1)이고, 프로덕션 호출은 `api/routers/world.py:84`, `session_service.py:115`, `player/service.py:79`이다. `is_running`이 "턴만"으로 좁아지면 GM 리스를 `True`로 기대하는 곳(`test_player_mode.py:964`, `test_turn_guard.py:104`)이 바뀐다. 메서드를 이름 바꿈하면 `assert not …is_running` 20곳 안팎이 바뀐다. 어느 쪽인지 FD/노트에 없다. `world.py:84`(월드 교체의 열린 세션 검사)가 리스를 계속 세는지도 적혀 있지 않다. | `is_running`을 유지하는지(의미 변경) 이름을 바꾸는지 적고, 영향받는 단언 수를 실제 grep 수로 고친다. `world.py:84`가 턴만 보는지 리스도 보는지 한 줄 적는다. | New |
| R-04 | Minor | nfr-light.md > § 3 (P3, P5) | P3은 "201 하나"라 하나 시작 경로 `POST /api/gm/sessions/{s}/seeds/{id}/start`의 상태 코드를 노트가 적지 않는다(코드 확인 필요). P5의 "`failed`/`interrupted`"는 모호하다. 현재 `fail_stale_runs(reason="interrupted")`(`api/main.py:123`)는 status `failed`에 error `interrupted`를 쓴다. 운영자가 어느 칸을 볼지 불분명하다. 또 P3은 같은 세션에 씨앗이 이미 돌고 있어야 409가 나는 구조여서 "동시"가 성립하려면 같은 씨앗 id여야 한다. | P3에 경로·같은 씨앗 id·기대 상태 코드를 적고, P5는 "status=`failed`, error=`interrupted`"(또는 V5가 바꾸는 값)로 한 가지만 적는다. 각 P에 조회 경로(`GET …/turn-runs/{id}` 등)를 한 줄 더한다. | New |
| R-05 | Minor | nfr-light.md > § 2.2 끼워 넣기 문 | 감싸개가 `uow()`의 `.distortions` 등을 감싸야 한다는 요건은 구현 가능하다(`_PgUnitOfWork` 속성이 모두 같은 `_PgStores`를 돌려주고 `postgres_repo.py:766-825`, 인메모리는 저장소 자신). 다만 어느 속성에서든 같은 `_PgStores`가 오므로 "정해진 메서드 이름 기준으로 멈춘다"고 정해야 하고, 인메모리 `uow`는 `__enter__`에서 저장소 `RLock`을 쥐어 안쪽에서 멈추면 다른 스레드가 `uow` 밖 읽기 `_synchronized`(`memory_repo.py:55-66`)에서도 막힌다(RLock 공유). 그래서 인메모리에서 "작업 단위 밖 읽기"를 멈추는 것은 괜찮지만 "안쪽 읽기에서 멈춤"은 시험 설계(1번)가 SQL 전용이어야 한다는 것을 § 2.3이 이미 말한다. 요건 문장에 "문은 메서드 이름 기준, 인메모리 안쪽 멈춤 금지"를 한 줄 더하면 구현 추측이 없어진다. 또 감싸개가 `__getattr__` 위임이면 3.12 이상 `runtime_checkable` Protocol `isinstance`는 통과하지 못한다(`getattr_static`). 코드에 `isinstance(…, PlayRepository)`는 없으나(grep 0건) 시험에서 쓰면 깨진다. | 감싸개가 명시 메서드를 감싸거나 위임이면 `isinstance`를 쓰지 않는다고 한 줄 적는다. | New |
| R-06 | Minor | nfr-light.md > § 4 | 상태 기계가 "리스 들어가기·나오기"를 하나로 다루나, 현 `hold`는 세션마다 개수를 센다(`guard.py:23-24`, U7 review #2: 리스끼리는 겹침 허용). 불변식 목록에 "리스 둘이 함께 있어도 되고 마지막이 나올 때만 `gm_busy`가 풀린다"가 없다. 이것이 빠지면 개수 계산 회귀(첫 리스가 나오면 풀림)를 상태 기계가 못 잡는다. | 불변식에 리스 개수 규칙을 더한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 노트가 이름 붙인 경로(`memory_repo.py`, `postgres_repo.py`, `sql.py`, `test_repository_contract.py`, `guard.py`, `docker-compose.yml`, `operations.md`, `pyproject.toml`) | 모두 존재 | OK |
| `docker-compose.yml:147-148` `--workers 1` | `command:` 줄에 `--workers 1` 있음(app 서비스 `app` 존재, P5의 `docker compose restart app` 가능) | OK |
| `operations.md` 116행 부근 워커 하나 문단 | 해당 문단(Concurrency, 113-120행) 존재 | OK |
| SQLite SELECT가 `engine.begin()` 안에서 잠금을 쥐지 않는다는 주장 | `make_engine`은 `connect_args` 없이 `create_engine`(`sql.py:17-19`). pysqlite 기본(레거시 트랜잭션 제어, Python 3.14.4에서도 기본 유지)은 DML 앞에서만 BEGIN. SQLAlchemy가 이 환경에 설치되어 있지 않아 실행은 못 했고 문서/소스 판단 | 주장 성립(실행 미확인). 쓰기 대기는 `timeout=5`가 busy_timeout |
| `sqlite://` 메모리는 스레드 둘이 같은 DB를 못 본다 | 기존 `any_repo`·`test_postgres_repo.py`가 모두 `sqlite://` 사용(단일 스레드). 노트의 파일 사용 요구는 타당 | OK (R-02) |
| `FOR UPDATE`가 SQLite에서 무시된다 | `with_for_update()`는 SQLAlchemy가 SQLite 컴파일러에서 생략 | OK |
| 시나리오 표의 읽기 위치 | `resolve_event`의 사건 읽기는 `uow` 안(`event/service.py:128-146`), `approve_event`(263)·`adjust_support`(`rumor/service.py:181`)·`set_region_distortion`의 `list_region_distortions`(`distortion_service.py:55`)·씨앗 `_running`(`seeds.py:54`)은 `uow` 밖 | 표(밖/안 구분)와 일치. 1번 SQL 전용 설정도 근거 있음 |
| 끼워 넣기 문이 두 작업 단위에서 구현 가능한가 | `_PgUnitOfWork`의 모든 저장소 속성이 같은 `_PgStores`, 인메모리는 `_MemoryUnitOfWork`가 저장소 자신. 감싸개가 `uow()`를 감싸 가능 | 가능(R-05) |
| 새 포트 `list_running_runs` | 코드에 아직 없음(`fail_stale_runs`만). 설계상 새 항목 | OK (신규) |
| `TurnGuard`의 `turn_running`·`gm_busy`·`closing`·`short_write` | 현 `guard.py`에 없음, 신규 메서드 | OK (신규). 상태 기계는 구현 후 작성 |
| NFR-1 "바뀌는 단언 셋" | `is_running`/`assert_idle` 테스트 호출 23곳 | 확인 불가 (R-03) |
| P1~P6 실행 가능성 | 경로·서비스명 존재. P1~P3은 잠금 유무를 가르지 못함, P5·P3 서술이 모호 | R-01, R-04 |
| 요구사항 NFR-1~10 대응 | NFR-1,2,3·4·7,5,6,8,9,10 모두 행이 있음 | 누락 없음 |

### Summary

노트의 큰 틀은 건전하다. 오프라인 겹침 재현(파일 SQLite + 끼워 넣기 문 + 시나리오별 저장소 표)은 코드의 읽기 위치와 맞고, R-02(시험 저장소)의 물음을 실제로 정한다. 가장 큰 약점은 § 3의 운영자 확인이다. 프로세스 안 짧은 쓰기 잠금이 DB 앞에서 먼저 직렬화하고 `curl &`로는 창을 못 맞추므로 P1~P3은 PostgreSQL 잠금을 증명하지 못한다(R-01). 나머지는 구현 추측을 줄이는 보완이다. 판정은 READY(Critical 0, Major 1).
