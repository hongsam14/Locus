# U4 플레이어 모드 — Business Rules

번호는 `BR-U4-n`. 근거 열의 Q는 FD-U4 답, RE는 `reverse-engineering/code-quality-assessment.md`. 번호는 안정적이다(빠진 규칙은 "U7로 이관"으로 남긴다).

## 1. 플레이어·세션
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-1 | 세션당 플레이어는 최대 1명. `PlayerCreate.name`(1~40자)·`start_region_id` 둘 다 필수이고 시작 지역은 시작 시점 스냅샷에 있어야 한다(없으면 400) | FR-C1, US-3.1, A-3 |
| BR-U4-2 | 세션 시작은 세션·플레이어·지역 왜곡도 초기화·`SESSION_STARTED` 타임라인을 **한 UoW**로 쓴다; 실패하면 아무것도 남지 않는다 | RE C4, US-8.3 |
| BR-U4-3 | 플레이어 상태(이름·현재 지역·턴 수)는 PostgreSQL에 있고 새로 고쳐도 그대로다. 스탯·인벤토리 없음 | US-3.1, A-3 |
| BR-U4-4 | (U7로 이관: `sync_regions`, FR-E6.) U4에서는 왜곡도 행이 없는 지역을 기본값으로 **읽기만** 하고, `GET region`은 아무것도 쓰지 않는다 | 스토리 맵, R-07 |
| BR-U4-5 | 진행 중 `TurnRun`이 있는 세션은 닫을 수 없다(409); 끝난 뒤 닫는다. 닫힌 세션의 행동은 409 | FR-E3 |
| BR-U4-30 | 플레이어 없는 세션(GM 전용, 기존 `start_session`)은 유효하다. 그 세션에서 `act`·`GET region`은 400 "session has no player"; GM `advance`는 동작한다 | R-02 |

## 2. 이동
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-6 | 이동 목적지는 현재 지역에서 `CONNECTED_TO`로 이어진 지역만. 그 밖은 400 "not connected" | FR-C2 |
| BR-U4-7 | `blocked` 연결과 가중치 0 연결은 통과 불가(`passable=False`, 400 "blocked pass"). 우회로가 없으면 그 지역은 도달 불가 | A-2 |
| BR-U4-8 | 이동 비용 `cost = clamp(ceil(1 / weight), 1, max_move_cost)`, `max_move_cost = 5`. 가중치가 낮을수록 비용은 크거나 같다(단조) | Q1=A, A-5 |
| BR-U4-9 | 같은 목적지로 연결이 여럿이면 통과 가능한 것 중 최소 비용을 보인다 | Q1 |
| BR-U4-10 | 이동이 받아들여지면 플레이어 위치는 **즉시** 목적지로 바뀌고(`PLAYER_MOVED`), 세계는 그 뒤 `cost` 턴을 배경에서 흐른다 | Q4=A, US-3.4 |

## 3. 행동과 턴
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-11 | 턴 비용: Move = BR-U4-8, Wait = 1, EndTalk = 1, GM 수동(`None`) = 1. 턴마다 기존 엔진(사건 → 소문 → 되먹임 → 지지도 → 가지치기 → 승격 → 턴+1)이 한 번 돈다 | FR-C3 |
| BR-U4-12 | `act`는 행동을 검증한 뒤 `TurnRun{running}`을 202로 바로 돌려준다. 턴 처리는 배경 실행기에서 돌고 `GET turn-runs/{id}`가 결과(`done` + `ActionResult`)나 실패(`failed` + 한 줄 사유)를 준다 | Q4=A, NFR-3 |
| BR-U4-13 | 한 세션에 `running` TurnRun은 최대 1개. 진행 중에 들어온 행동·GM 턴·세션 닫기·GM 세션 상태 쓰기(소문 생성/재생성/지지도/왜곡도/사건)는 즉시 409 `turn in progress`(기다리지 않는다). 읽기는 막지 않는다 | Q3=A, FR-E3, US-8.3, R-06 |
| BR-U4-14 | 턴 하나의 저장은 UoW 하나다. 사건 적용은 메모리에서 계산하고, LLM 호출은 그 턴의 UoW **밖**에서 먼저 끝난 초안이며, 저장은 UoW 안에서 `u.*`로만 한다(협력자는 `self._repo`로 쓰지 않는다). 실패한 실행에서 이미 커밋된 턴은 남고 `TURN_RUN_FAILED`가 남는다 | FR-E3, US-8.3, R-01 |
| BR-U4-15 | API 프로세스가 시작될 때(lifespan) `running`으로 남은 TurnRun은 `failed("interrupted")`로 닫는다. `assemble_play`·CLI는 이것을 하지 않는다 | Q4, R-08 |
| BR-U4-16 | GM 수동 턴은 같은 진입점(`advance(session_id, None)`)·가드·예산을 쓴다. 라우트 응답은 기존 `TurnResult`(동기) 그대로 | FR-D1, services §3.7, R-03 |
| BR-U4-31 | `TurnAdvancer.advance`는 P7대로 `ActionResult`를 돌려준다. 기존 호출처(gm 라우트 1곳, 테스트 24곳)는 `.turns[-1]`로 읽도록 갱신하고 단언 내용은 유지한다 | P7, R-03 |
| BR-U4-32 | 인메모리 리포지토리는 전역 `RLock`으로 스레드 안전하고 UoW 동안 락을 보유한다; PG UoW는 트랜잭션 한 connection 위의 store 묶음이다. 배경 실행기 종료는 timeout(기본 30초)까지만 기다린다 | R-04, R-08 |

## 4. 폭주 상한과 예산
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-17 | 턴마다 새 `LlmBudget(max_llm_calls_per_turn = 8)`. 소문 체인 한 degree 단계 = LLM 호출 1회 = 예산 1(시도 기준). 예산이 다하면 그 턴의 소문 추가를 멈추고 `budget_exhausted=true`·`rumors_skipped_regions`에 남긴다. 결정적 단계는 항상 돈다 | Q2=A, FR-E1, NFR-5 |
| BR-U4-18 | 지역·턴당 새 소문은 `max_new_rumors_per_region_turn = 2` 이하. 체인 길이는 `min(len(degrees), budget.remaining, max_new - len(out))`으로 잘라 **버리는 호출이 없다**(앞 단계, 낮은 degree부터) | Q2=A, R-05 |
| BR-U4-19 | 이미 그 지역에 파생 활성 소문을 가진 캐노니컬 지식은 그 턴의 씨앗에서 제외한다(같은 원본이 매 턴 다시 씨앗이 되지 않는다). 기존 소문은 `support >= min_source_support`일 때만 씨앗 | FR-E1, RE C1 |
| BR-U4-20 | GM 수동 생성·재생성(`generate_rumors`·`regenerate_region`)은 상한을 적용하지 않고 지금처럼 즉시 저장한다(의도적 조작, 기존 동작) | BR-H1-8 |
| BR-U4-21 | `TurnResult.llm_calls`는 그 턴에 시도한 생성기 호출 수(degree 단계 수의 합)와 같고, `ActionResult.llm_calls`는 턴들의 합이다 | US-8.1, NFR-5 |

## 5. 화면 데이터와 요약
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-22 | `RegionView`는 지역 이름·설명·계층 경로·NPC 목록·`facts`(direct+inherited+global)·`hearsay`(전언, path_decay)·`rumors`(활성, 왜곡도)·`moves`를 한 번에 준다. 어디에도 UUID만 보이지 않는다(이름 동반) | FR-C5, FR-D3, US-3.2 |
| BR-U4-23 | 플레이어가 있으면 `ActionResult.changes`는 현재 지역 + 직접 연결된 이웃(통과 가능 무관)의 변동만; 플레이어가 없으면(GM 세션) 모든 지역. 항상 `region_name` 포함 | Q5=A, R-02 |
| BR-U4-24 | `narration`은 `changes`의 지역마다 한 문장의 결정적 템플릿(LLM 없음) | Q5, U4 범위 |
| BR-U4-25 | (필터는 U7로 이관.) U4의 플레이 로그는 세션 타임라인 전체를 시간순으로 보이고, 새 종류의 payload에 `region_name`을 넣는다 | FR-C6 "U4 기본 → U7 필터", R-07 |

## 6. LLM 없을 때
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-26 | LLM 제공자가 없으면 이동·대기·GM 턴은 동작하고 소문 초안 단계만 건너뛴다. `RegionView.llm_available=false`, `ActionResult.llm_available=false`가 안내 근거다. 500은 나지 않는다 | Q6=A, US-1.4 |

## 7. 경계·계약
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U4-27 | play는 캐노니컬을 `SnapshotSource.get`으로만 읽고 쓰지 않는다; `knowledge.cache` 하나를 통해 읽는다 | NFR-3, 경계 행렬 |
| BR-U4-28 | `GET /api/play/sessions/{s}/regions/{r}/knowledge`(외부 NPC 계약)와 GM 라우트의 응답 형식은 그대로 둔다 | FR-F5, R-03 |
| BR-U4-29 | `TurnResult`의 기존 필드·의미는 유지하고 필드만 더한다. 기존 테스트의 단언은 유지하되 `advance` 호출은 BR-U4-31대로 읽는다 | AD P7 |

## 8. Testable Properties (NFR-2, PBT Partial)
| id | 속성 | 규칙 | 생성기 |
|---|---|---|---|
| TP-U4-1 (PBT-03) | `w1 <= w2 ⇒ move_cost(w1) >= move_cost(w2)`; `1 <= cost <= max_move_cost` (통과 가능 연결) | BR-U4-8 | `tests/play/strategies.py::connections()` |
| TP-U4-2 (PBT-03) | `blocked` 또는 `weight == 0` ⇒ `passable=False`, 그 목적지로의 `act(Move)`는 400 | BR-U4-7 | 같은 생성기 |
| TP-U4-3 (PBT-03) | 임의 세션 상태에서 턴 1회 뒤 지역별 새 소문 ≤ `max_new_rumors_per_region_turn` | BR-U4-18 | `sessions_with_rumors()` + 카운팅 생성기 가짜 |
| TP-U4-4 (PBT-03) | 턴 1회의 생성기 호출(degree 단계 합) ≤ `max_llm_calls_per_turn`, `TurnResult.llm_calls`와 같다; 어떤 호출의 결과도 버려지지 않는다(`sum(len(chain)) == len(out)`) | BR-U4-17/18/21 | 같은 |
| TP-U4-5 | 어떤 지역에서 활성 파생 소문이 있는 캐노니컬 지식은 다음 턴의 씨앗에 없다 | BR-U4-19 | 같은 |
| TP-U4-6 | 같은 세션에 `_start`(begin)를 동시에 N번 호출하면 정확히 1개가 running, 나머지는 `TurnInProgressError`; 인메모리 리포지토리 상태는 일관(플레이어 행 1개, TurnRun 1개) | BR-U4-13/32 | 스레드 N개, 인메모리 리포지토리 |
| TP-U4-7 | `done`인 TurnRun의 `len(result.turns) == cost_turns`, `session.turn == started_turn + cost_turns` | BR-U4-11/12 | 인메모리 저장소 + `SyncTurnExecutor` |
| TP-U4-8 (PBT-07) | 생성기는 `tests/play/strategies.py`(연결·스냅샷·세션·소문·사건) | — | — |

### 8.1 규칙별 검증(예제 `EX-n`)
| 규칙 | 검증 |
|---|---|
| BR-U4-1/2/3 | EX-1 `start` → 세션·플레이어·왜곡도·타임라인 한 번에; 시작 지역 없음 400; UoW 안 실패 흉내 → 아무것도 없음(인메모리 롤백 + sqlite 롤백) |
| BR-U4-4 | EX-2 왜곡도 행이 없는 지역에서 `current_region`·턴 → 기본값으로 동작, 행은 생기지 않음 |
| BR-U4-5 | EX-3 running 중 `close` 409 |
| BR-U4-30 | EX-17 플레이어 없는 세션: `act` 400, GM `advance` → `ActionResult.player is None`, `changes`는 모든 지역 |
| BR-U4-6/7/9/10 | TP-U4-1/2; EX-4 이어지지 않은 지역 400; EX-5 Move 뒤 즉시 `player.region_id == to`, `PLAYER_MOVED`, TurnRun running |
| BR-U4-11/12/16/31 | TP-U4-7; EX-6 Wait/EndTalk/GM 턴 각각 1턴; EX-7 `act` 202 → 폴링 done → `ActionResult`; EX-18 gm 라우트 응답이 `TurnResult` 그대로(기존 gm 테스트 통과) |
| BR-U4-13 | TP-U4-6; EX-8 running 중 `act`·GM `advance`·GM 왜곡도 설정·사건 생성 409, `GET region`·`GET state`는 200 |
| BR-U4-14/15/32 | EX-9 두 번째 턴에서 예외 → 첫 턴은 커밋, run `failed`, `TURN_RUN_FAILED`, 가드 해제; EX-10 lifespan 시작 흉내(`fail_stale_runs`); EX-19 sqlite로 `uow()` 안 예외 → 사건·왜곡도·소문 어느 것도 저장되지 않음; EX-20 인메모리: 스레드 A가 UoW 중 예외로 롤백해도 스레드 B의 (UoW 전/후) 쓰기는 남는다 |
| BR-U4-17/18/19/21 | TP-U4-3/4/5; EX-11 RE C1 재현(지역 1, 캐노니컬 지식 3, degrees 2단계, `max_new=2`, `budget=8`, persistent WAR 0.5, 4턴; 생성기 가짜는 요청한 degree 수만큼 돌려줌): 턴마다 새 소문 = 2, 호출 = 2, 4턴 뒤 활성 소문 ≤ 8, 총 호출 ≤ 8, `budget_exhausted=false`; 같은 조건에 `budget=1`이면 턴마다 새 소문 1, `budget_exhausted=true` |
| BR-U4-20 | EX-12 GM `generate_rumors`는 상한 무시·즉시 저장(기존 테스트) |
| BR-U4-22 | EX-13 `RegionView` 필드 채움(이름·경로·NPC·facts/hearsay/rumors/moves) |
| BR-U4-23/24 | EX-14 3지역 중 이웃 아닌 지역의 변동은 `changes`에 없음; narration 한 문장/지역 |
| BR-U4-25 | EX-15 로그가 새 종류를 포함해 시간순 전체 |
| BR-U4-26 | EX-16 `rumors=None` 컨테이너로 Move → done, `llm_available=false`, 소문 0 |
| BR-U4-27/28/29 | `tests/test_boundaries.py`; 기존 play·gm·localization API 테스트 통과 |
