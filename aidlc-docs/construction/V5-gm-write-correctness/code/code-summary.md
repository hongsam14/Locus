# V5 GM 쓰기 정확성 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V5 코드 생성을 마쳤다(Step 1~9). 같은 세션의 GM 쓰기가 겹쳐도 결과가 차례로 한 것과 같고, 닫기·월드 교체·재시작·지역 삭제가 반쯤 쓰인 상태를 남기지 않는다. 플레이어의 409는 "턴 중"과 "GM 작업 중"을 나눠 말하고, 문장에 내부값이 없다. 이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V5-gm-write-correctness-code-generation-plan.md`(9단계, 승인 2026-10-08; 실행 메모 § 1.1~1.4 포함).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `efe78c9`) | 결과 (Step 9) → 코드 리뷰 01 뒤(`3995e86`) |
|---|---|---|
| pytest | 1048 | 1119 → **1138**. hypothesis 시드 둘(`1`, `20261008`)로 GREEN |
| ruff · black | clean | clean |
| mypy (`locus api`) | 11 | 11 |
| 웹 | vitest 550 | 바뀐 웹 없음(`git diff efe78c9..HEAD -- web` 비어 있음) |

커밋(7개 + 이 요약):

| 단계 | 커밋 | 내용 |
|---|---|---|
| 2 | `9ac7f28` | guard(턴 슬롯·닫는 중·리스·짧은 쓰기), 409 `gm_busy`·`rumor_inactive`, 세션 닫기, 월드 교체 점검 |
| 3 | `a17ec29` | 겹침 시험 받침(끼워 넣기 문, 실패하는 타임라인, 막히는 가짜 LLM, `threaded_repo`) |
| 4 | `60ef076` | 사건·씨앗 구간(`WriteSection`) |
| 5 | `de45bc4` | 소문 구간(생성·재생성·지지도) |
| 6 | `101cb63` | 행적 취소·왜곡도 설정 구간 |
| 7 | `a507d6a` | 끊긴 run 보상, 지운 지역의 사건 |
| 8 | `03cdb83` | operations.md, env.example |
| 리뷰 01 | `3995e86` | 코드 리뷰 01의 medium 4·low 21 고침(기록 `code/reviews/code-review-01.md` § 6) |

## 2. 바꾼 파일과 만든 파일

| 파일 | 상태 | 내용 | 커밋 |
|---|---|---|---|
| `locus/play/turn/guard.py` | 다시 씀 | 세션마다 턴 슬롯, 닫는 중(수), 리스(수), 짧은 쓰기 `RLock`. `acquire`·`release`·`hold`·`short_write`·`closing`·`turn_running`·`gm_busy`. 문장 상수 셋(내부값 없음). `is_running`·`running_run_id`·`assert_idle` 없앰 | `9ac7f28` |
| `locus/play/write_section.py` | 새 | `WriteSection`: `lock(s)`(짧은 쓰기만, 다시 들어감) · `open(s)`(짧은 쓰기 → 작업 단위 → 세션 다시 읽기, 닫혔으면 `SessionClosedError`) | `60ef076` |
| `locus/play/errors.py` | 바뀜 | `GmBusyError(TurnInProgressError)`, `RumorInactiveError(RuntimeError)` | `9ac7f28` |
| `locus/shared/config/{tuning,settings}.py` | 바뀜 | `PlayTuning.gm_write_wait_s = 5.0`, `GM_WRITE_WAIT_S`(> 0) | `9ac7f28` |
| `locus/play/models.py` | 한 줄 | `RegionView.gm_busy` | `9ac7f28` |
| `locus/play/player/service.py` | 바뀜 | `turn_running`(턴만)과 `gm_busy`(리스)를 채움 | `9ac7f28` |
| `locus/play/session_service.py` | 바뀜 | `close_session`: `closing` → `short_write` → 작업 단위에서 세션을 다시 읽고 닫고, 줄은 한 번. `tuning` 인자 | `9ac7f28` |
| `api/errors.py` | 바뀜 | `gm_busy`(부모보다 앞), `rumor_inactive`(`seed_running` 다음), `PLAY_ERRORS`에 `RumorInactiveError` | `9ac7f28` |
| `api/routers/world.py` | 바뀜 | 교체 점검은 턴만 셈. 닫기가 상한을 넘기면 "busy", 턴이면 "mid-turn" 경고 | `9ac7f28` |
| `locus/play/event/service.py` | 바뀜 | 만들기·해소·승인·폐기·제안이 구간에서 새로 읽고 행과 줄을 함께 씀. 제안의 LLM은 밖. 해소는 월드에 있는 지역만 복원. 승인: ACTIVE면 그대로, 폐기됐으면 404, 해소됐으면 400. `guard` 인자, `section` 속성 | `60ef076` |
| `locus/play/event/seeds.py` | 바뀜 | 진행 중 확인과 만들기를 사건 서비스의 `section.lock` 하나에 둠 | `60ef076` |
| `locus/play/rumor/service.py` | 바뀜 | 생성: 초안 밖, 저장·줄 구간 안. 재생성: 구간 안에서 지역 소문을 다시 읽어 버릴 것을 고르고, 건너뛰기 줄도 구간 안. 지지도: 다시 읽어 꺼졌으면 `RumorInactiveError`. `_generate_for_region` 없앰. `tuning`·`guard` 인자 | `de45bc4` |
| `locus/play/deeds/service.py` | 바뀜 | `void`가 구간 안에서 행적을 다시 읽음. `guard` 인자 | `101cb63` |
| `locus/play/distortion_service.py` | 바뀜 | 되먹임 몫을 구간 안에서 읽고, 저장한 `RegionDistortion`을 돌려줌. `tuning`·`guard` 인자 | `101cb63` |
| `api/routers/gm.py` | 바뀜 | `set_distortion`이 서비스가 돌려준 행을 그대로 돌려줌 | `101cb63` |
| `locus/play/ports.py`, `storage/{memory,postgres}_repo.py` | 바뀜 | `list_running_runs()` 더함, `fail_stale_runs` 없앰 | `a507d6a` |
| `locus/play/turn/advancer.py` | 바뀜 | `_compensate`(실패와 끊김의 한 규칙), `_fail`이 부름, `recover_interrupted()`. `_compute_events`가 지운 지역의 사건을 먼저 끝냄 | `a507d6a` |
| `api/main.py` | 바뀜 | lifespan이 `turns.recover_interrupted()`를 부름 | `a507d6a` |
| `locus/play/wiring.py` | 바뀜 | 공유 guard·tuning을 세션·사건·소문·행적·왜곡도 서비스에 넘김 | 2·4·5·6 |
| `aidlc-docs/operations/operations.md`, `env.example` | 바뀜 | 409 코드, 리스와 짧은 쓰기, `GM_WRITE_WAIT_S`, 닫기·교체, 워커 하나의 이유 셋, 재시작 보상과 `interrupted_uncompensated` 찾는 법, 지운 지역의 사건 | `03cdb83` |

새 시험 파일: `tests/play/{concurrency,conftest,test_concurrency_harness,test_guard_machine,test_v5_overlap,test_v5_turns}.py`, `tests/api/test_v5_busy_api.py`.

## 3. 요구·규칙·시험 대응

| TP | 무엇 | 시험 | 저장소 | 고치기 전 실패 확인 |
|---|---|---|---|---|
| TP-V5-1 | 두 해소 겹침(#9) | `test_v5_overlap::test_tp_v5_1_*` | 둘(겹침은 SQL에서) | Step 4 이전 코드: SQL 실패, 인메모리 통과(NFR § 2.3대로) |
| TP-V5-2 | 씨앗 경합(#12) | `test_tp_v5_2_*` | 둘 | 이전 코드: 둘 다 실패 |
| TP-V5-3 | 지지도 부활(RE-P01), 취소 둘 | `test_tp_v5_3_*`(2) | 둘 | 돌연변이(바깥 읽기 사용, 다시 읽기 없음) 잡힘. 꺼지지 않은 행적 소문은 다음 턴에 r1 → r2로 퍼지는 것을 따로 확인(대조) |
| TP-V5-4 | 닫기 중 생성(RE-P02) | `test_tp_v5_4_*` | 둘 | 이전 코드: 실패 |
| TP-V5-5 | 끊긴 run(RE-P03) | `test_v5_turns::test_tp_v5_5_*`(4: 0턴·1턴, 보상 실패, 표시마저 실패, API 시작) | 인메모리 | 돌연변이(표시만, 미보상 표시 없음) 잡힘 |
| TP-V5-6 | 지운 지역의 사건(RE-P04) | `test_tp_v5_6_*`(2: 턴, GM 해소) | 인메모리 | 돌연변이(적용, 모든 지역 복원, 이웃 저장 빠짐) 잡힘 |
| TP-V5-7 | 일괄 생성 다섯 | `test_tp_v5_7_*` | 둘 | 돌연변이(초안을 구간 안으로) 잡힘. 이전 코드에서는 통과(결함 재현이 아니라 회귀 방지) |
| TP-V5-8 | 플레이어 409·바쁨 표시 | `test_v5_busy_api::test_tp_v5_8_*`(2) | 인메모리 | 돌연변이(표 순서, `gm_busy` 칸) 잡힘 |
| TP-V5-9 | 승인 겹침(RE-P06) | `test_tp_v5_9_*`(3) | 둘 | 이전 코드: 승인 둘·승인 먼저 실패. 폐기 먼저(404)는 이전 코드에서도 통과 |
| TP-V5-10 | 몫 이중 기록 | `test_tp_v5_10_*` | 둘 | 이전 왜곡도 코드: `[0.2, 0.2]`로 실패 |
| TP-V5-11 | 겹친 재생성(RE-P07), 생성과 재생성 | `test_tp_v5_11_*`(2) | 둘 | 이전 코드: 재생성 둘 실패 |
| TP-V5-12 | 행과 줄의 원자성(RE-P05) | `test_tp_v5_12e_*`, `test_tp_v5_12r_*` | 둘 | 이전 코드: 둘 다 실패 |
| TP-V5-13 | 기다림 상한·씨앗 다시 들어감 | `test_tp_v5_13_*`(2) | 둘 | 이전 코드: 상한 시험 실패 |
| TP-V5-14 | 닫기와 턴의 틈, 닫기 둘 | `test_v5_busy_api::test_tp_v5_14_*`(3) | 인메모리 | 돌연변이(닫는 중 표시 없음, 줄 매번) 잡힘 |
| TP-V5-15 | 월드 교체와 GM 쓰기 | `test_v5_busy_api::test_tp_v5_15_*`(4) | 인메모리 | 돌연변이(리스도 셈, busy 가지 없음) 잡힘. 생성 중 교체는 이전 소문 코드에서 실패 |
| NFR-6 | guard 상태 기계 | `test_guard_machine.py` | — | 돌연변이(리스 수·닫기 수를 참/거짓으로) 둘 다 잡힘 |
| NFR-10 | 받침 자체 | `test_concurrency_harness.py`(11) | 둘 | — |

- guard 단위 시험(`test_turn_guard.py`): 짧은 쓰기 차례·상한·다시 들어감·예외 뒤 풀림, 닫기 수, 리스 수, 문장에 내부값 없음, 옛 메서드 없음(BR-V5-25).
- 설정 시험(`test_config.py`): `GM_WRITE_WAIT_S` 기본·읽기·0 거부.
- 계약 시험(`test_repository_contract.py`): `list_running_runs`가 모든 세션의 `running`만(`any_repo`, 두 어댑터).
- "고치기 전 실패"는 단계마다 그 단계 전의 서비스 파일을 잠시 되돌려 돌리거나 돌연변이를 넣어 확인했고, 끝나면 되돌렸다.

## 4. 바뀐 기존 시험 (§ 1.2 R-03의 수와 견줌)

| 예측 | 실제 | 이유 |
|---|---|---|
| `is_running` 20곳 | 20곳 | `turn_running`(턴) 또는 `gm_busy`(리스)로 |
| `assert_idle` 3곳 | 3곳 | `closing`으로, 플레이어 모드의 한 곳은 독스트링 |
| `running_run_id` 2곳 | 2곳 | 없앰 |
| 409 문장 "turn in progress" 3곳 | 3곳 | `code == "turn_running"`과 "세션 id 없음"으로 |
| `turn_running` 단언 4곳 | 0곳 | 뜻이 좁아졌어도 네 곳 모두 턴을 잡고 보는 단언이라 그대로 맞다 |
| `fail_stale_runs` 3곳 | 3곳 | 계약 시험 하나를 `list_running_runs` 시험(`any_repo`)으로 바꿈, SQL 시험 한 줄 |
| (예측 밖) | 3곳 | 아래 |

예측 밖의 세 곳:
- `test_world_editor_api.py::test_region_delete_waits_for_no_turn_and_holds_the_sessions`: 에디터 삭제 중 턴 시작이 `TurnInProgressError` → `GmBusyError`(에디터도 리스다, BLM § 7).
- `test_advance_turn.py::test_approve_non_suggested_rejected`: Step 4에서 "ACTIVE면 그대로"로 바꿨다가, 코드 리뷰 01 #9로 처음 단언(GM이 만든 ACTIVE는 400)으로 돌아갔다. 그대로 돌려주는 것은 제안에서 승인된 사건뿐이다.
- `test_player_mode.py::test_a_region_deleted_from_the_world_does_not_wedge_the_turn_engine`(U4-2 #4): 지운 지역에 초안을 시도하고 건너뛰던 것을, 사건이 먼저 끝나 초안이 없는 것으로 바꿈(FR-C4). 턴이 막히지 않는다는 원래 뜻은 그대로다. 지운 지역 초안을 건너뛰는 방어 코드는 남겼지만, 사건으로는 더 닿지 않는다.

시험 받침: `tests/api/play_fixtures.py::play_container`에 `tuning` 인자를 더했다.

## 5. 이탈

1. **`fail_stale_runs`를 없앴다**(§ 1.1 R-01, 실행 메모 R-06). 승인된 BR-V5-19, domain-entities § 3, TP-V5-5는 "보상이 실패해 남은 `running`은 `fail_stale_runs`로 실패 표시"라고 적는다. FD 리뷰 R-01이 그것을 "보상 없이 실패 표시만 하면 플레이어 위치·청구가 틀린 채 묻힌다"로 짚었고, 코드 플랜 승인 때 대신할 처분을 정했다. 보상이 실패한 run은 자기 작업 단위에서 `failed`/`interrupted_uncompensated`로 표시하고 ERROR 로그를 남긴다. 그 표시마저 실패하면 `running`으로 남아 다음 시작에서 다시 보상한다. 포트, 두 어댑터, lifespan, 시험 3곳에서 없앴다.
2. **`WriteSection`을 따로 두었다.** 플랜은 서비스가 guard와 tuning을 받는다고 적었다. 그대로 받되, 구간의 모양(짧은 쓰기 → 작업 단위 → 세션 다시 읽기)을 한 클래스에 모아 다섯 서비스가 같은 코드를 쓴다. 서비스는 `section` 속성으로 그것을 들고 있다.
3. **`SeedService`는 guard를 받지 않는다.** 사건 서비스의 `section`을 그대로 쓴다. 코드 리뷰 01 #7 뒤로는 그 구간 하나에서 진행 중을 보고 `create_in`으로 만든다(다시 들어가지 않음, BR-V5-04 고침). R-03의 "직접 만드는 곳은 기본값으로 돈다"는 그대로 맞다.
4. **`session_closed` 문장**: 닫는 중은 "the session is closing", 닫힘은 "the session is closed"다. 둘 다 세션 id가 없다(FR-C5, 코드 리뷰 01 #6). domain-entities § 2의 "그대로"를 고쳤다.

## 6. 알려진 한계

- **교체 점검과 닫기 사이의 틈**(§ 1.1 R-05c). 월드 교체의 사전 점검이 지난 뒤 닫기 전에 그 세션에서 턴이 시작되면, 교체는 일어나고 그 세션의 닫기는 `turn_running`으로 거절된다. 보고서에 "mid-turn and could not be closed" 경고로 남고 세션은 열린 채다. 그 턴은 경계에서 멈춘다(BR-U4-11).
- **지운 지역에 남은 소문의 되먹임**(BLM § 8). 턴의 `apply_feedback`이 지운 지역의 소문으로 그 지역 행을 쓸 수 있다. FR-C4는 사건만 다룬다.
- **한 프로세스 안의 보장**이다. 짧은 쓰기와 guard는 프로세스 안 잠금이다. PostgreSQL 행 잠금(`FOR UPDATE`)과 상태 조건 쓰기는 두 번째 겹으로 남겼지만, 실제 PostgreSQL에서의 겹침은 오프라인 시험이 돌리지 못한다(아래 B&T 확인).
- **지운 지역 초안 건너뛰기 방어 코드**는 사건 경로로는 더 닿지 않아 그 시험이 빠졌다(§ 4).
- **닫는 중에 거절된 턴**은 409 `session_closed`(BR-V5-16)인데, 그 닫기가 상한을 넘겨 `gm_busy`로 실패하면 세션은 열린 채다. 플레이어는 이미 "닫혔다"를 받았다. 창은 GM 저장 구간이 멈췄을 때의 상한(5초)뿐이다(코드 리뷰 01 § 4).
- **인메모리 변형의 겹침 시험**은 작업 단위가 저장소 전체를 잠가 구간 없이도 통과하는 것이 있다(TP-V5-3 취소 둘, 9, 10, 11). 구간 자체는 SQL 변형이 지킨다(NFR § 2.3, 코드 리뷰 01 § 4).
- 받침의 끼워 넣기 문은 시간에 기대는 곳이 있다(0.5초 기다림). 단계마다 3~6번 이어 돌려 흔들림이 없었지만, 아주 느린 CI에서는 늘릴 수 있다.

## 7. 다음에 넘김

- **V6 (GM 화면)**: 한국어 문장 셋.
  - `rumor_inactive`: "그 사이 꺼진 소문이에요" 같은 문장. 지금은 V2의 409 기본 문장이 나온다.
  - 타임라인 `event_resolved`의 `reason: "region_removed"`: "사라진 지역의 사건이 끝났어요". 줄에 지역 이름이 없다(지역이 없다).
  - GM 쓰기의 409 `gm_busy`(짧은 쓰기 상한을 넘김)와 월드 교체 경고 "busy and could not be closed".
  - 제안에서 승인된 사건을 다시 승인하면 200(그대로)이다. 두 번 누름은 화면이 막는다(BLM § 8).
  - 코드 리뷰 01 § 3: 플레이어 행동의 409 `gm_busy`가 "턴이 진행 중입니다"로 나온다(`conflictKind`). GM 작업 중 문장을 따로 둔다. GM 허브는 `rumor_inactive`·`gm_busy`에서 원문을 보이고 `rumor_inactive` 뒤에 다시 읽지 않는다. `describeError`에 두 키를 더하고, `rumor_inactive` 뒤에는 지역을 다시 읽는다.
- **Build and Test (운영자 확인)**: NFR § 3의 P1~P6을 B&T 체크리스트에 넣는다.
  - § 1.2 R-01: P1~P3는 "실제 스택 스모크"로 이름을 바꾼다(고치기 전 코드에서도 통과할 수 있다). 잠금 자체를 보는 확인을 더한다: `psql`에서 사건 행을 `SELECT … FOR UPDATE`로 잡아 둔 채 해소를 보내 응답이 늦어지는지 본다.
  - § 1.2 R-04: P3는 `POST /api/gm/sessions/{s}/seeds/{같은 씨앗 id}/start` 둘, 201 하나와 409 하나. P5는 run의 `failed`와 `error=interrupted`를 `GET /api/play/sessions/{s}/turn-runs/{id}`로 본다.
  - P5에 더할 것: 보상이 실패한 run(`interrupted_uncompensated`)이 없는지 operations.md의 SQL로 본다.
