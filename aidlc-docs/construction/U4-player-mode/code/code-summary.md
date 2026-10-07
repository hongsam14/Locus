# U4 플레이어 모드 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**이 유닛이 해 준 것**: 플레이어가 캐릭터로 세션에 들어가 연결을 따라 이동하고, 행동이 턴을 흐르게 하며, 현재 지역을 한 화면에서 본다. 턴 엔진은 GM 수동 턴과 플레이어 행동이 함께 쓰는 단일 진입점이 되었고 LLM 예산·지역 상한·세션당 실행 1개 가드·트랜잭션 하나의 턴 저장을 갖는다.

플랜: `construction/plans/U4-player-mode-code-generation-plan.md` (11단계, 전부 [x]). 설계: `construction/U4-player-mode/functional-design/*`, `nfr/nfr-light.md`.

## 1. 기준선 → 결과 (Step 1.1 / 11.1, 2026-09-30)
| 검사 | 기준선 | 결과 |
|---|---|---|
| `pytest -q --no-cov` | 388 passed | **475 passed** (신규 69 + 코드리뷰 회귀 18, 회귀 0; 의도적 갱신 6건 §4·§6a) |
| `npm test`(vitest) | 31 passed | **39 passed** (신규 파일 `play.test.tsx` 8 + 갱신 1) |
| `mypy locus api` | 12 errors | **11 errors** (새 코드 0건; 리뷰 수정으로 1 감소) |
| `ruff check` / `black --check` | clean | clean |
| `tsc --noEmit` / `vite build` | clean | clean (208 kB gz 66 kB) |
| `docker build` | OK | OK (`locus-u4-check`) |
| 라이브(Neo4j/PostgreSQL/OpenAI) | 운영자 실행 | 운영자 실행 — §6 명령 |

## 2. 만든 것 / 바꾼 것
**백엔드 `locus/play/`**
- `models.py` +`Player`, `PlayerCreate`, `MoveAction`/`WaitAction`/`EndTalkAction` + `PlayerAction`(discriminated union), `MoveOption`, `TurnRunStatus`, `TurnRun`, `ActionResult`(`player: Player | None`), `RegionView`; `TurnResult`가 여기로 이동(+`llm_calls`, `budget_exhausted`, `llm_failed`, `rumors_skipped_regions`, `rumors_capped_regions`; advancer가 re-export); `TimelineKind` +5; `RegionTurnChange.region_name`.
- `errors.py`(신규): `InvalidActionError(ValueError)`, `TurnInProgressError`.
- `ports.py`: `PlayerStore`, `TurnRunStore`, `PlayUnitOfWork`(+players, runs), `PlayRepository.uow()`.
- `storage/schema.py`: `players`(session_id UNIQUE), `turn_runs`. `storage/postgres_repo.py`: 모든 SQL을 `_PgStores(conn)`로 옮기고 리포지토리 메서드는 `engine.begin()` 한 형태로 위임; `_PgUnitOfWork`. `storage/memory_repo.py`: 전역 `RLock`, UoW = 락 보유 + 깊은 복사 스냅샷 복원.
- `player/movement.py`(신규, 순수): `is_passable`, `move_cost`, `move_options`, `neighbours`, `validate_action`, `action_cost`. `player/service.py`(신규): `PlayService`(current_region/act/turn_run/list_runs/log/player).
- `turn/budget.py`(`LlmBudget`), `turn/guard.py`(`TurnGuard`), `turn/executor.py`(`TurnExecutor` 포트, `ThreadTurnExecutor` 데몬 워커, `SyncTurnExecutor`), `turn/summary.py`(`merge_changes`, `scope_changes`, `narrate`), `turn/changes.py`(+`region_names`).
- `turn/advancer.py`: 계산 → 초안(LLM) → 저장(UoW 하나) 3단계 `_one_turn`; `advance(session_id, action=None) -> ActionResult`(동기, P7) / `begin(...) -> TurnRun`(배경); `_start`(가드 안 검증·즉시 위치 갱신), `_run`, `_fail`(예외 클래스 이름만 기록), 회로 차단(`llm_failed`).
- `rumor/service.py`: `chain_degrees_for`, `_collect_sources(exclude_knowledge_ids=)`, `append_for_turn(...) -> (drafts, skip_reason)`(저장 없음; `min(len(degrees), budget.remaining, max_new-drafted, max_active-active)`). `rumor/feedback.py`: `apply_feedback(..., store=)`.
- `session_service.py`: `SessionService(repo, snapshots, guard)`; `start(world_id, PlayerCreate)`(UoW 하나 + SESSION_STARTED); `start_session`(GM, 타임라인 없음); `close_session`(가드 확인 + SESSION_CLOSED).
- `wiring.py`: `PlayContainer += feedback/turns/play/guard/executor`(항상), `assemble_play(..., executor=)`; 조기 반환 제거(LLM 없어도 턴 엔진 조립).
- `shared/config/tuning.py` +4, `settings.py` +5 env(`PLAY_MAX_MOVE_COST`, `RUMOR_MAX_NEW_PER_REGION_TURN`, `LLM_MAX_CALLS_PER_TURN`, `RUMOR_MAX_ACTIVE_PER_REGION`, `TURN_SHUTDOWN_TIMEOUT_S`). `locus/__main__.py::_session_service` → 스냅샷 소스.

**API** — `api/errors.py`(`PLAY_ERRORS`, 409 `TurnInProgressError`), `api/routers/play.py`(세션 시작 이중 응답 200/201, `player`, `region`, `act` 202, `turn-runs`, `log`), `api/routers/gm.py`(`_idle` 의존성 8개 쓰기 라우트, except 10곳 통일, advance `.turns[-1]`), `api/schemas.py`(`SessionStartOut`, `RegionViewOut`, `localize_region_view`), `api/main.py`(lifespan: 시작 시 `fail_stale_runs`, 종료 시 `executor.shutdown(timeout)`).

**프론트엔드 `web/src/`** — `types.ts`, `api/play.ts`, `features/play/{summary,RegionScene,MovePanel,ActionBar,PlayLog,LlmBanner,NewSessionForm}.tsx`, `routes/PlayPage.tsx`(placeholder 교체; 202 → 즉시 재조회 → 폴링 → 알림), `SessionBar.tsx`(+`regions`/`onPlay`, "플레이 시작" 버튼; 기존 버튼·테스트 불변), `routes/EditorPage.tsx`, `i18n.ts`(+라벨·타임라인 템플릿 5), `SessionPanel.tsx`(`changeSummary`를 공유 모듈로).

**테스트** — `tests/conftest.py`(hypothesis 프로파일 `locus`, PBT-08), `tests/play/strategies.py`(PBT-07), `tests/play/{test_movement,test_turn_guard,test_player_mode}.py`, `tests/api/test_play_api.py`, `web/src/__tests__/play.test.tsx`; 기존 `test_models/test_repository_contract/test_postgres_repo` 확장.

**문서** — `env.example`(5 env), `operations.md` "Player mode" 절, `CLAUDE.md` Status/레이아웃.

## 3. 설계 규칙 → 구현 위치 (검증 대응)
| 규칙/속성 | 테스트 |
|---|---|
| TP-U4-1/2 이동 비용 단조·범위·통과 불가 | `test_movement.py` (hypothesis) — **PBT가 잡은 결함 1건**: 극소 가중치(subnormal)에서 `ceil(1/weight)` 오버플로 → `weight * cap <= 1`이면 cap 반환으로 고침 |
| TP-U4-3/4/5 상한·예산·씨앗 제외, 활성 상한, EX-11 수치, 회로 차단 | `test_player_mode.py` Step 5 절 |
| TP-U4-6 가드 동시성, 실행기 | `test_turn_guard.py` |
| TP-U4-7, EX-5~9, EX-16/17, R-10/R-11 | `test_player_mode.py` Step 6 절 |
| EX-1/2/3/13/15, NFR-9, R-09 | `test_player_mode.py` Step 7 절 |
| EX-7/8/18, R-06, NFR R-03(구조 단언: 202 전 UoW 1개·LLM 0회), 세션 시작 이중 응답 | `tests/api/test_play_api.py` |
| EX-19/20 UoW 커밋·롤백·스레드 | `test_repository_contract.py`, `test_postgres_repo.py`(sqlite) |
| 프론트 EX-13/7/16, 409 토스트, 재개 폴링, NewSessionForm | `web/src/__tests__/play.test.tsx` |

## 4. 의도적 테스트 갱신 (NFR-1 "FR-E1 변경은 테스트를 고친다")
1. `tests/play/test_advance_turn.py::test_primary_region_rumors_appended_preserving_existing` — BR-U4-19: 이미 파생 소문을 낳은 캐노니컬 지식은 매 턴 다시 씨앗이 되지 않으므로, 지지도 0.9인 기존 소문을 씨앗으로 두어 "추가된다"를 확인.
2. `tests/api/test_play_gm_api.py::test_start_list_get_close_flow` — BR-U4-5: 세션 닫기가 `session_closed` 타임라인 항목 하나를 남긴다(GM `start_session`은 여전히 항목 없음, R-09).
3. `tests/shared/test_wiring.py` — LLM 없이도 `turns`가 조립되고 GM advance가 200(계약 (5)).
4. `advance()` 호출처 24곳(`test_advance_turn.py` 21 + `test_play_services.py` 3) `.turns[-1]` (BR-U4-31; 단언 불변). `tests/play/test_service.py`는 `FakeGraph` → `FakeSnapshots`.

## 5. 설계 이탈 완결 목록 (FD R-12 이월)
| 상위 산출물 | 구현 | 까닭 |
|---|---|---|
| services.md §3.4 위치 갱신 순서 | `_start`에서 즉시 갱신, 세계는 배경 | Q4=A |
| services.md §3.4/§3.7 `act`가 `advance` 결과를 응답 | `act` → `begin` 202 + 폴링; GM advance 동기 `TurnResult` 유지 | GM 화면·기존 계약 보존 |
| P7 `advance(session_id, action) -> ActionResult` | 채택; 라우트는 `.turns[-1]` | P7 정합 |
| P7 `TurnGuard.acquire -> ContextManager` | `acquire(session_id, run_id)` / `release` / `assert_idle` | 배경 실행이 요청 스코프를 넘어 보유 |
| P8 `append_for_turn(session, region_ids, *, budget)` | 단일 지역 + `distortion`/`max_new`/`max_active`/`min_source_support`, `(drafts, reason)` 반환 | 사건 적용 뒤 왜곡도·지역별 사유 필요 |
| `_collect_sources(exclude_knowledge_ids=)`, `apply_feedback(store=)`, `chain_degrees_for`, `Settings.turn_shutdown_timeout_s`, `SessionService(repo, snapshots, guard)` | 신설/변경 | BR-U4-14/19, R-04 |
| services.md §3.9 `sync_regions` lazy 호출 / 플레이 로그 필터 | U4 미구현(기본값 읽기·전체 로그) → U7 | 스토리 맵 |
| 이월 확정: 지역당 활성 상한 20(N-1), 회로 차단(NFR R-02), `llm_calls` = 예약 호출 수(R-13), env 5개(R-05), `get_run` 세션 스코프(R-06), 실패 기록 = 예외 클래스만(N-4), GM `start_session` 타임라인 없음(R-09), `_idle` 신규 의존성(R-10) | 위 §2 | 게이트 disposition |

## 6. 운영자 실행(라이브) 명령
```bash
docker compose up -d neo4j opensearch postgres && locus init-schema --play
locus world demo --name aldermoor --world demo
uvicorn api.main:app --port 8000 --workers 1
# 플레이 세션 시작 → 지역 → 이동 → 폴링
curl -s -X POST localhost:8000/api/play/worlds/demo/sessions -H 'content-type: application/json' \
  -d '{"name":"Ari","start_region_id":"<region id>"}'           # 201 {session, player}
curl -s -w '%{time_total}\n' localhost:8000/api/play/sessions/<sid>/region    # 목표 p95 100ms(50회)
curl -s -w '%{time_total}\n' -X POST localhost:8000/api/play/sessions/<sid>/act \
  -H 'content-type: application/json' -d '{"type":"wait"}'      # 202, 목표 200ms
curl -s localhost:8000/api/play/sessions/<sid>/turn-runs/<run id>              # done + result
```
호스트 7474/7687이 다른 프로젝트에 잡혀 있어(`sigraph-neo4j-1`) 이 환경에서는 compose 라이브 검사를 돌리지 않았다.

## 6a. 코드 리뷰 (record: `code/reviews/code-review-01.md`)
`/code-review`가 두 번 사용량 한도로 끊긴 뒤 각도 하나가 지적 8건을 돌려주었고, 이 세션이 8건을 코드에서 직접 검증해 **6건을 고치고 2건을 감수**했다. 고친 것: 한 트랜잭션 안 타임라인 순서(애플리케이션 단조 시각), `WorldCache`가 로드 **전에** 버전 마커를 읽음, `regenerate_region`이 생성 먼저·교체는 UoW 하나(LLM 장애 때 소문 파괴 제거), `resolve_event` 원자화, 인메모리 UoW를 열기 전에는 쓰기 거부(트윈 충실도, `PlayUnitOfWork` 프로토콜 읽기 전용화), `ThreadTurnExecutor`가 `BaseException`에도 살아남고 죽으면 `submit`이 즉시 실패. 제거: 채워질 수 없던 `RegionViewOut.region_name_ko`(지역 이름 번역은 U5로). 감수: `fail_stale_runs`의 프로세스 간 범위(단일 워커 전제, 운영 문서 명시), `create_event`·`set_distortion`의 타임라인 동반 쓰기 비원자성(U7).
검증(1차 수정 뒤): pytest 464 / vitest 38 / mypy 11.

그 뒤 사용량이 충전되어 `/code-review`를 **전체로 다시** 돌렸다(각도 10개 + 검증 패스). 지적 **16건 중 15건을 고치고 1건을 감수**했다: 배경 턴의 가드 누출 2건, 월드 교체 게이트가 진행 중 턴을 미리 거절, 삭제된 지역이 턴 엔진을 막던 문제, 실패한 실행의 이동·턴 청구 보상, 부분 LLM 실패에도 소문을 지우던 문제, GM 쓰기의 가드를 시점 검사에서 리스로, 턴이 모든 지역 왜곡도를 덮어쓰던 문제, 폐기된 사건의 부활(두 어댑터 세션 범위 갱신 전용), 캐시 마커 읽기 실패의 영구 고착, 닫힌 세션에서 계속 도는 턴 루프, 일방통행 연결로 갇히는 플레이어, LLM 없이 503이 되던 결정적 라우트 7개(회귀), 주입된 실행기 종료와 500, 가드 없던 사건 제안 라우트, 화면 버튼이 잠기던 폴링 수명 문제. 감수: `fail_stale_runs`의 프로세스 간 범위(단일 워커 전제). 자세한 내용과 상한 아래 목록은 리뷰 기록 2절.

검증(2차 수정 뒤): **pytest 475** (회귀 테스트 18 추가, 회귀 0) / **vitest 39** / **mypy 11**(기준선 12) / ruff·black·tsc·vite build clean.

### 추가 설계 이탈
| 상위 규칙 | 구현 | 까닭 |
|---|---|---|
| BR-S1-8 "`created_at`은 DB 서버 시간" | `timeline_entries`만 애플리케이션 단조 시각 | 턴 하나가 트랜잭션 하나라 서버 시각이 전부 동일해져 순서가 임의가 된다(리뷰 #1) |
| `RegionViewOut.region_name_ko` | 제거 | 채울 경로가 없었다; 지역 이름 번역은 U5 |

## 7. 남긴 것 (인계)
- U5: `EndTalkAction`은 턴만 소모(대화·`NPC_TALKED`), `RegionScene` NPC 카드의 "말하기" 자리.
- U7: `sync_regions`(FR-E6)와 그 호출 지점, 플레이 로그 필터(FR-C6), 플레이어 지역 소멸 시 재배치 UI, GM 화면의 409 전용 토스트, 대기열 상태 표시(`queued`).
- 알려진 한계: 실행기 하나라 세션 간 직렬; 대기 중 실행도 `running`으로 보임(운영 문서).
