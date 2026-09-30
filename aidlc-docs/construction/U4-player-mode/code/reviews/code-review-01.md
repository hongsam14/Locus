# U4 플레이어 모드 — Code Review 01

**대상**: 커밋되지 않은 U4 변경(`locus/play/**`, `locus/shared/config/**`, `api/**`, `web/src/**`, `tests/**`).
**경위**: `/code-review`를 세 번 시도했다. 두 번은 시작 직후 사용량 한도(HTTP 429)로 끊겼고, 세 번째에서 각도 하나가 **지적 8건**을 돌려준 뒤 나머지 각도가 한도로 끊겼다. 오케스트레이션의 검증 패스가 돌지 못했으므로 **8건을 이 세션이 코드에서 직접 검증**하고(전건 재현 경로 확인) 조치했다. 수정 뒤 전체 리뷰를 다시 돌린다.

## 지적과 조치
| # | 위치 | 지적 | 판정 | 조치 |
|---|---|---|---|---|
| 1 | `play/storage/postgres_repo.py` `append_timeline`/`list_timeline` | 턴 하나의 타임라인 항목이 **한 트랜잭션**에 들어가는데 PostgreSQL의 `CURRENT_TIMESTAMP`는 트랜잭션 시작 시각이라 모든 행이 같은 값을 받는다. `ORDER BY turn, created_at`이 동률이 되어 한 턴의 항목 순서가 임의가 되고, 같은 세션을 두 번 읽으면 순서가 달라질 수 있다. U4 전에는 항목마다 트랜잭션이 따로였다 | **확인** | `play/storage/clock.py::next_timestamp()`(프로세스 안 단조 증가 UTC)로 애플리케이션이 시각을 찍는다. `list_timeline`은 `(turn, created_at, id)`로 정렬. 이 테이블만 "DB 서버 시간"(BR-S1-8)에서 벗어난다 — code-summary 이탈 기록. 회귀 테스트: 한 UoW에 네 항목을 넣고 순서·단조 증가 확인 |
| 2 | `knowledge/cache.py` `get` | 스냅샷을 **로드한 뒤** 버전 마커를 읽어, 로드 중에 다른 프로세스가 쓰면 낡은 스냅샷이 새 버전으로 저장된다. 그 뒤 버전 재확인은 영원히 일치해 낡은 월드가 프로세스 수명 내내 남는다(`locus world import`를 API와 함께 쓰는 정확히 그 상황) | **확인** (U2 코드지만 U4 플레이가 이 캐시만으로 캐노니컬을 읽는다) | 두 줄을 바꿔 **로드 전에** 마커를 읽는다. 로드 중 쓰기가 있으면 버전 불일치로 다음 읽기가 다시 로드한다. 회귀 테스트: 로드 중 버전이 바뀌는 로더 가짜 |
| 3 | `play/rumor/service.py` `regenerate_region` | 비승격 소문을 **각각 자동 커밋으로 먼저 삭제**한 뒤 LLM을 부른다. 생성기는 LLM 예외를 삼켜 빈 체인을 돌려주므로, 제공자 장애 때 소문(지지도·승격 이력·출처)이 영구히 사라지고 응답은 200이다 | **확인** | 생성을 먼저 한다(`_draft_for_region`, 저장 없음). 초안이 비면 **아무것도 지우지 않고** 타임라인에 `skipped: true`로 남긴 뒤 기존 목록을 돌려준다. 초안이 있으면 삭제+저장+타임라인을 **UoW 하나**로 교체한다. 회귀 테스트 2건(장애 시 보존, 교체 중 실패 시 원상) |
| 4 | `play/event/service.py` `resolve_event` | 왜곡도 복원 N회 + 사건 갱신 + 타임라인이 각각 따로 커밋된다. 중간 실패 시 일부 지역만 복원되고 사건은 ACTIVE로 남아 다음 턴에 **두 번째 기여가 누적**되어 대칭 복원 산술이 영구히 깨진다 | **확인** | 전체를 `repo.uow()` 하나로 감쌌다(결정적 본문이라 BR-U4-14 허용). `SessionAppService._entry`를 base로 올려 UoW 안에서 타임라인을 쓴다. 회귀 테스트: 갱신 실패 시 왜곡도·상태·타임라인 불변, 재시도 성공 |
| 5 | `play/storage/postgres_repo.py` `fail_stale_runs`, `api/main.py` lifespan | 필터가 `status='running'`뿐이라 워커가 둘이면 기동하는 워커가 **다른 워커의 진행 중 실행**을 failed로 만든다 | **확인 · 감수** | 단일 워커 전제가 설계·운영 문서의 전제다(`--workers 1`). 프로세스 간 펜싱은 U4 범위 밖(데모 규모)이라 `operations.md`에 "워커를 늘리면 서로의 실행을 끊는다"를 명시하고 감수 위험으로 남겼다 |
| 6 | `play/storage/memory_repo.py` `_MemoryUnitOfWork` | 일곱 store를 `__init__`에서 리포지토리에 묶어 두어, **열지 않은** UoW로도 쓰기가 된다(락 없음·스냅샷 없음·롤백 불가). PostgreSQL 어댑터는 같은 오용에 예외를 던지므로 트윈이 오프라인에서 결함을 가린다 | **확인** | store를 `__enter__`에서만 유효한 읽기 전용 프로퍼티로 바꿨다(`_s`가 "unit of work is not open"). `PlayUnitOfWork` 프로토콜의 멤버도 읽기 전용 프로퍼티로 고쳐 두 어댑터가 같은 계약을 만족한다(mypy 12 → 11). 회귀 테스트: 열기 전·닫은 뒤 모두 예외 |
| 7 | `api/schemas.py` `RegionViewOut.region_name_ko` | 항상 `None` 리터럴로 채우고 `kind="region"` 번역이 코드 어디에도 없어, 이 필드는 채워질 수 없다. 프론트는 그것으로 지역 제목을 그려 본문만 한국어가 된다. API 테스트가 필드 존재만 단언해 죽은 필드를 고정한다 | **확인** | 죽은 필드를 DTO·프론트 타입·`RegionScene`·테스트에서 제거했다. 지역 이름 번역은 언어 유닛(U5)의 일이므로 U5 설계에 옮겼다 |
| 8 | `play/turn/executor.py` `_loop` | `except Exception`만 잡아 `BaseException`이 올라오면 단일 데몬 워커가 **조용히 죽는데** `submit`은 계속 받는다. 그 뒤 모든 행동은 202를 받고 실행되지 않으며 가드가 풀리지 않아 세션이 프로세스 수명 내내 409가 된다. `shutdown`의 "still busy" 경고도 뜨지 않는다 | **확인** | `except BaseException`으로 잡아 기록하고 루프를 계속한다. 루프가 `_STOP` 없이 벗어나면 `finally`에서 `_closed=True`로 만들어 이후 `submit`이 즉시 실패한다. 회귀 테스트: `BaseException` 뒤에도 다음 작업이 실행됨 |

## 검증 (수정 뒤)
| 검사 | 값 |
|---|---|
| `pytest -q --no-cov` | **464 passed** (리뷰 전 457 → 회귀 테스트 7 추가, 회귀 0) |
| `npm test`(vitest) | 38 passed |
| `mypy locus api` | **11 errors** (리뷰 전 12; UoW 프로토콜 정리로 1 감소) |
| `ruff check` / `black --check` / `tsc --noEmit` | clean |

## 남긴 것
- #5는 감수 위험(단일 워커 전제, 운영 문서에 명시).
- 지적 #4의 같은 모양(비원자적 타임라인 동반 쓰기)이 `EventService.create_event`와 `DistortionService.set_region_distortion`에도 있다. 실패 시 남는 차이가 "타임라인 항목 한 줄 누락"뿐이어서 이번에는 고치지 않았다 — U7(GM 모드·안정화)에서 함께 정리한다.

---

# U4 플레이어 모드 — Code Review 02 (전체 패스)

사용량이 충전된 뒤 `/code-review`를 전체로 다시 돌렸다. 각도 10개가 돌고 검증 패스까지 끝나 **지적 16건**(15 + 나머지 각도가 뒤늦게 보낸 1건)과 상한 아래 목록이 돌아왔다. 1차에서 고친 8건은 "고쳐졌음"으로 확인되어 다시 보고되지 않았다. 16건 중 **15건을 고치고 1건을 감수**했다.

## 고친 것
| # | 위치 | 지적 | 조치 |
|---|---|---|---|
| 1 | `turn/advancer.py` `_run` | `get_run` 읽기가 가드를 푸는 try/finally **밖**에 있어, 저장소가 한 번 흔들리면 가드가 새고 세션이 프로세스 수명 내내 409가 된다(닫지도 못한다) | 읽기까지 try 안으로. 어떤 예외에도 `finally`가 가드를 푼다 |
| 2 | `turn/advancer.py` `begin` | `_fail`이 실패하면 그 뒤의 `release`에 닿지 못해 같은 방식으로 가드가 샌다(형제 `advance`는 `finally`를 쓴다) | `_fail`을 try로 감싸고 `finally`에서 해제 |
| 3 | `api/routers/world.py` | 월드 교체 뒤 세션을 닫을 때 U4가 넣은 idle 검사가 예외를 던져 **월드가 이미 파괴된 뒤** 500이 난다. 더 깊은 원인: `_open_sessions`가 진행 중 턴을 보지 않아 파괴를 시작하게 한다 | 게이트에서 **미리** 검사한다: 진행 중 턴이 있는 세션이 있으면 `confirm`이 있어도 409로 거절(파괴 전). 닫기 단계도 예외를 잡아 못 닫은 세션을 리포트 경고로 남긴다 |
| 4 | `turn/advancer.py` 초안 단계 | 사건의 대상 지역이 월드에서 삭제되면 매 턴 `LookupError`가 나고 사건은 영원히 ACTIVE로 남아 세션의 턴 엔진이 못 돈다 | 스냅샷에 없는 지역은 건너뛰고 `rumors_skipped_regions`에 남긴다 |
| 5 | `turn/advancer.py` `_start`/`_fail` | 이동·턴 소모는 턴 루프 **전에** 따로 커밋되므로, 루프가 실패하면 플레이어는 움직였는데 시계는 그대로다 → 공짜 이동이 무한 반복 | `TurnRun`에 `from_region_id`·`turns_charged`를 남기고, 실패 시 실제로 흐른 턴만큼만 청구하며 한 턴도 안 흘렀으면 위치를 되돌린다. 타임라인에 `turns_advanced`·`turns_refunded` 기록 |
| 6 | `rumor/service.py` `regenerate_region` | 1차 수정의 `if not fresh`는 **전면** 실패만 잡는다. 생성기가 성공한 앞부분만 돌려주면(부분 실패) 대체하지 못하는 소문을 지운다. 또 `fresh == []`가 "LLM 장애"와 "씨앗 없음"을 뭉갠다 | `_draft_for_region`이 `(초안, 완결 여부)`를 돌려준다. 완결이 아니면 아무것도 지우지 않고 `reason="llm_incomplete"`; 씨앗이 없고 지울 것도 없으면 `reason="no_sources"` |
| 7 | `api/routers/gm.py` `_idle` | 라우터 의존성이 **시점 검사**라 핸들러 본문(LLM 수 초) 동안 턴이 시작될 수 있다. 재현: 느린 재생성 중 턴이 소문을 승격했고, 재생성의 낡은 목록이 그 승격 소문을 지웠다(BR-X3-9 위반) | `TurnGuard.hold()` 리스로 바꿨다. yield 의존성이 응답까지 세션을 잡고, 바쁘면 즉시 409 |
| 8 | `turn/advancer.py` 저장 단계 | LLM 단계 **전에** 읽은 지도로 **모든** 지역의 왜곡도를 다시 써서, 그 사이의 GM 편집이 조용히 지워지고 200 지역 월드에서 턴당 200번 upsert가 난다 | 사건이 실제로 움직인 지역(`influenced_regions`)만 쓴다 |
| 9 | `storage/postgres_repo.py` `update_event` | `id`만으로 맞춰 행이 없으면 **INSERT**해서, 턴의 LLM 창에서 폐기된 사건을 부활시키고 세션 사이로 옮길 수도 있다(원본의 기여 누적을 잃는다). 인메모리 트윈은 복제를 만들어 공용 계약 테스트가 못 본다 | 두 어댑터 모두 세션 범위 **갱신 전용**으로, 없으면 `KeyError`. 턴 저장 단계는 그 예외를 잡아 부활시키지 않는다 |
| 10 | `knowledge/cache.py` `_current_version` | 마커 읽기 실패를 `None`으로 삼켜, 그 값이 캐시되면 "이 월드에는 마커가 없다"와 구분되지 않아 교차 프로세스 낡음 검사가 영구히 꺼진다 | 실패는 예외로 올리고, 호출자는 그 읽기만 서비스하고 **캐시하지 않는다** |
| 11 | `session_service.py`/`turn/advancer.py` | 닫기의 idle 검사는 검사일 뿐이라 그 틈에 시작한 턴이 **닫힌 세션**에서 끝까지 돈다. CLI는 가드를 아예 넘기지 않아 검사가 무동작이다 | 턴 루프가 매 턴 경계에서 `_require_open`으로 다시 확인해 닫힌 세션에서 멈춘다(교차 프로세스 한계는 운영 문서) |
| 12 | `player/movement.py` | `neighbours`·`move_options`가 **나가는** 연결만 따라가, 대칭이 아닌 월드 파일에서 일방통행 문이 생겨 플레이어가 갇히고 이웃의 턴 알림이 사라진다 | 두 함수는 연결을 무방향으로 읽는다(`_other_end`) |
| 13 | `play/wiring.py` | **회귀**: 이전에는 `EventService`가 항상 조립되고 LLM은 suggester로만 닿았는데, 재구성이 *소문* 생성기에 묶어 LLM 없는 배포에서 결정적 라우트 7개가 503이 된다(`/events` 전체, 소문 읽기·지지도) | `RumorService`·`EventService`를 항상 조립하고, LLM이 필요한 **메서드**만 `LlmUnavailableError`(503)를 던진다. 라우터의 서비스 단위 503 게이트 제거 |
| 14 | `api/main.py` lifespan | 주입된 play 컨테이너의 실행기까지 종료해(소유권 규칙 위반) 재사용 시 `submit`이 맨 `RuntimeError`를 던지고, `PLAY_ERRORS`가 잡지 못해 플레이어는 이미 이동한 채 500이 난다 | 소유한(`owned`) 컨테이너만 종료하고, `ExecutorShutdownError`를 만들어 503으로 매핑 |
| 15 | `api/routers/gm.py` `events/suggest` | GM 쓰기 라우트 10개 중 **유일하게** 가드가 없어, 턴이 도는 중에도 사건 행을 쓰고 예산 밖 LLM 호출을 태운다 | 같은 리스 의존성을 붙였다 |
| 16 | `web/src/routes/PlayPage.tsx` | `busy`가 한 번 켜지면 풀 길이 없어(폴링 실패 경로가 새로 고치지 않는다) 새로 고침 전까지 모든 버튼이 잠긴다. 폴링 루프에 정리(cleanup)가 없어 떠난 화면에도 계속 쓰고, 옛 세션의 알림이 새 화면에 뜬다 | 세대(generation) 참조로 언마운트·세션 전환 시 루프를 끊고, 폴링의 모든 종료 경로가 새로 고치며, 약속만 하고 그리지 않던 `narration`을 화면에 그린다 |

## 감수한 것
- **`fail_stale_runs`의 프로세스 간 범위**(1차 #5와 동일): 단일 워커 전제. 운영 문서에 "워커를 늘리면 서로의 실행을 끊는다"를 명시했다.

## 상한 아래 목록에서 함께 고친 것
GM 알림이 지역 이름을 쓰게(`changeTitle`, FR-D3) · SQL `list_rumors`·`list_region_distortions`에 정렬 추가(두 어댑터 동일) · `create_run`의 `action`을 `mode="json"`으로 · 인메모리 트윈이 enum **값**을 저장하도록(어댑터 동등성) · `movement`의 중복 `BLOCKED` 리터럴을 `ConnectionKind.BLOCKED`로 · 테스트 조립이 데몬 스레드를 새지 않게(`SyncTurnExecutor` 기본) · 호출자 없는 `RumorService.append_for_region` 제거.

남긴 것(다음 유닛): 타임라인 전체 재조회(U7 로그 필터에서 페이지네이션과 함께) · 턴마다 초기화되는 LLM 회로 차단(장애 시 다중 턴 이동이 최악 8분; 운영 문서에 기록) · 캐시의 in-flight 중복 억제와 `_gen` 키 누적 · 예산 소진 플래그의 과보고 · 409 본문 문자열 판별 · FK 없는 고아 행 · `promotion_threshold`·`_IN_CHUNK`·`MoveOption.reason` 등 미사용 인자.

## 검증 (2차 수정 뒤)
| 검사 | 값 |
|---|---|
| `pytest -q --no-cov` | **475 passed** (1차 뒤 464 → 회귀 테스트 11 추가, 회귀 0) |
| `npm test`(vitest) | **39 passed** (+1) |
| `mypy locus api` | **11 errors** (기준선 12) |
| `ruff check` / `black --check` / `tsc --noEmit` / `vite build` | clean |
