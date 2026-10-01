# U4 플레이어 모드 — NFR (light: 요구 + 설계)

근거: 요구 §NFR(NFR-1~9), 실행 계획 §NFR(light), 승인된 FD(`functional-design/*`, 검토 02 R-09~R-15 disposition), 플랜 가정 N-1~N-5. 새 기술 스택 선택은 없다(C-3, C-4). 아래 표의 "방법"이 코드 생성 플랜의 입력이다.

## 1. NFR별 적용
| NFR | U4 적용 | 방법 (설계) | 수치 · 검증 |
|---|---|---|---|
| **NFR-1 회귀 없음** | ✅ | 기존 테스트는 지우지 않는다. `TurnAdvancer.advance`의 반환형 변경(P7)으로 `tests/play/test_advance_turn.py` 21곳·`test_play_services.py` 3곳은 `.turns[-1]`로 읽도록 **기계적 갱신**(단언 불변). GM `advance` 라우트 응답 `TurnResult`, 세션 시작 라우트의 본문 없는 호출(200 `GameSession`)은 그대로(R-09). `TurnResult`·`RegionTurnChange`는 필드 추가만 | 기존 419(388 pytest + 31 vitest) 전부 GREEN + 신규. Build&Test에서 회귀 0 확인 |
| **NFR-2 PBT Partial** | ✅ | TP-U4-1~7(hypothesis): 이동 비용 단조·범위, 통과 불가, 턴당 새 소문 ≤ 상한, LLM 호출 ≤ 예산·버려지는 호출 없음, 씨앗 제외, 가드 동시성, 실행 길이. 생성기는 `tests/play/strategies.py`(연결·스냅샷·세션·소문·사건; PBT-07 재사용 util). 설정: `deadline=None`, 기본 `max_examples`, 실패 예제는 hypothesis 데이터베이스(로컬) | 각 TP가 테스트 파일 이름으로 대응된다(코드 플랜 표). PBT-03 대상 4개 불변식 모두 포함 |
| **NFR-3 플레이 응답성** | ✅ | `act`는 검증 + UoW 하나(위치 갱신·TurnRun 행)만 하고 202를 돌려준다 — LLM 없음. `GET region`은 `WorldCache` 스냅샷(U2, 월드 단위·버전 마커 재확인)과 PostgreSQL 활성 소문 조회만. 턴 처리(LLM)는 배경 실행기; UI는 `TurnRun` 폴링(700ms)으로 진행 표시·완료 토스트. 인메모리 스냅샷 파생 인덱스(`regions_by_id`, `npcs_by_region`)로 O(1) 조회 | 로컬·LLM 없음 기준 목표: `POST act` p95 ≤ 200ms, `GET region` p95 ≤ 100ms(캐시 적중). Build&Test 라이브 시나리오에서 `curl -w %{time_total}` 10회로 확인(운영자 실행) |
| **NFR-4 데모가 끊기지 않는다** | ✅ | LLM 제공자가 없어도 이동·대기·GM 턴이 동작(Q6). `RegionView.llm_available=false` → 배너. `TurnAdvancer`는 `rumors=None`으로도 조립 | EX-16; 오프라인 API 테스트 |
| **NFR-5 LLM 비용 상한** | ✅ | 턴당 `LlmBudget(max_llm_calls_per_turn=8)`, 지역·턴당 새 소문 ≤ 2, **지역당 활성 소문 ≤ 20**(N-1; 상한에 닿은 지역은 그 턴의 초안을 건너뛰고 `rumors_skipped_regions`에 남김 — GM 수동 생성은 예외, BR-U4-20). 한 행동의 상한 = `cost_turns × 8 ≤ 40`(이동 최대 5턴). `TurnResult.llm_calls`(예약 호출 수 = 상한, R-13)·`ActionResult.llm_calls` 보고 | TP-U4-3/4 + 새 TP(활성 상한): "어떤 턴 뒤에도 지역별 활성 소문 ≤ 20". `PlayTuning` env: `LLM_MAX_CALLS_PER_TURN`, `RUMOR_MAX_NEW_PER_REGION_TURN`, `RUMOR_MAX_ACTIVE_PER_REGION` |
| **NFR-6 보안은 NFR로만** | ✅ | 인증 없음(로컬 데모) 유지. 입력 검증: `PlayerCreate.name` 1~40자, `PlayerAction`은 `type` 판별 유니온(모르는 type → 422), `to_region_id`·`npc_id`는 스냅샷 대조(400), `start_region_id` 스냅샷 대조(400). 오류 응답·`TurnRun.error`는 한 줄 고정 문구; `TURN_RUN_FAILED` payload에는 **예외 클래스 이름만**(N-4), 본문은 서버 로그. 세션 id는 경로 파라미터 그대로(추측 불가 uuid) | 422/400/409 테스트; payload에 스택·SQL 문자열 없음 단언 |
| **NFR-7 코드 품질** | ✅ | ruff·black(100)·tsc 클린. mypy 오류 수 12(현재) 이하 유지 — 새 모듈(`play/player/`, `play/turn/{guard,runner}.py`, `storage/uow`)은 완전 타입. 새 서비스는 단일 책임·DI(`PlayService`·`TurnAdvancer`·`TurnGuard`·`TurnExecutor` 분리). `_PgStores(conn)`로 PG SQL 단일화(11곳 `engine.begin()` 정리) | `ruff check`, `black --check`, `mypy locus api`(≤ 12), `tsc --noEmit` |
| **NFR-8 문서 정확성** | ✅ | `operations.md`: 단일 워커 전제, 배경 실행기·종료 대기, 시작 시 `interrupted` 정리, 새 env 3개. `CLAUDE.md` Status·CLI/API 한 줄. `env.example` 갱신 | U4 코드 게이트 때 문서 diff 포함 |
| **NFR-9 저장소 무결성** | ✅ | 세션은 캐노니컬 지역 id를 참조만 한다. 월드 교체 시 세션 닫기·경고는 U2가 이미 한다. 편집(U3)으로 플레이어의 현재 지역이 사라진 경우: `current_region`·`act`가 404 `player region no longer exists`(500 아님); 재배치 UI는 U7 | 스냅샷에서 지역 삭제 뒤 `GET region` → 404 테스트 |

## 2. 신뢰성 · 가용성 · 규모
- **실패 격리**: 배경 턴의 예외는 `TurnRun.failed` + `TURN_RUN_FAILED` 타임라인으로 끝나고 가드는 `finally`에서 풀린다. 이미 커밋된 턴은 남는다(턴마다 UoW). `begin`에서 `executor.submit`이 거절되면 같은 `_fail` 경로 + 가드 해제(R-11). 시작 시 `running` 잔재는 `failed("interrupted")`(lifespan에서만).
- **동시성**: 세션당 진행 중 실행 1개(가드; TP-U4-6). 검증은 가드 안에서 최신 위치로(R-10). GM 쓰기 라우트는 진행 중이면 409. 인메모리 저장소는 `RLock`(UoW 동안 보유), PG는 트랜잭션 한 connection.
- **종료**: 실행기 워커는 **데몬 스레드**(R-14)이고 lifespan은 최대 30초(N-3, `TURN_SHUTDOWN_TIMEOUT_S`) 기다린다. 그 뒤에도 남은 실행은 프로세스 종료를 막지 않고 다음 시작 때 `interrupted`로 닫힌다. LLM 호출 자체의 timeout은 provider 어댑터 설정에 의존한다(없으면 코드 플랜에서 `LLM_TIMEOUT_S`를 추가한다).
- **가용성**: 단일 프로세스·단일 uvicorn 워커(운영 문서). HA·failover는 범위 밖(로컬 데모).
- **규모(N-5)**: 세션당 플레이어 1, 데모 월드 ≤ 15 지역, 지역당 활성 소문 ≤ 20 → 세션당 ≤ 300 소문. 턴마다 활성 소문 전체를 메모리에 올리는 현 방식(`list_rumors`)이 이 규모에서 충분하다. `turn_runs` 행은 세션당 행동 수만큼 늘고(수백) 보관 정책은 두지 않는다(세션 삭제 시 함께).
- **대기열 표시**: 실행기가 하나라 다른 세션의 실행이 도는 동안 새 실행은 `running`으로 보이지만 시작 전일 수 있다(R-11). 데모 규모(동시 세션 1~2)에서 감수하고 문구를 "세계가 움직이는 중"으로 둔다.

## 3. 사용성
- 한국어 UI 라벨(X3 방침), 진행 표시("세계가 움직이는 중… (N턴)"), 409 시 "턴이 진행 중입니다" 토스트, LLM 없음 배너, 이동 옵션에 비용·통과 불가 표시. UUID 노출 없음(BR-U4-22). 키보드 접근: 이동·대기 버튼은 `<button>`(기존 Doodly 프리미티브).

## 4. 기술 스택 결정 (신규 없음)
| 결정 | 선택 | 대안과 까닭 |
|---|---|---|
| 배경 실행 | 표준 라이브러리 스레드(데몬 워커 1개, 자체 `TurnExecutor` 포트) | Celery/RQ/Redis는 프로세스·인프라를 더한다(C-4 인프라 무변경, 단일 워커 데모). 포트로 감싸 테스트는 동기 스텁 |
| 진행 전달 | HTTP 폴링(700ms) | SSE/WebSocket은 클라이언트 하나에 과하고 uvicorn 단일 워커 설정과 프록시 고려가 늘어난다. 폴링은 기존 fetch 계층 재사용 |
| 트랜잭션 | SQLAlchemy Core `engine.begin()` 한 connection의 store 묶음 | ORM 세션 도입은 기존 Core 스타일과 어긋난다 |
| PBT | hypothesis(기존) | — |

## 5. 코드 생성 플랜으로 넘기는 것
1. R-09~R-14 확정 사항(FD 게이트 disposition)과 R-15 활성 상한(N-1) 규칙·TP 추가.
2. `PlayTuning` 3 + `Settings` 1(`turn_shutdown_timeout_s`) env 이름 확정, `env.example`·`operations.md` 갱신 단계.
3. 회귀 갱신 목록(24곳 `.turns[-1]`) 단계.
4. NFR-6 실패 기록 규칙(N-4), NFR-9 404 규칙, 응답성 확인 명령(운영자 실행)을 Build&Test 체크리스트로.
