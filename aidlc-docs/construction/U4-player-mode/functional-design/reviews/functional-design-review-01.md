## Review

**Verdict:** NOT-READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U4 플레이어 모드
**Reviewed artifact:** `aidlc-docs/construction/U4-player-mode/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-09-30T01:01:53Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U4-player-mode/functional-design/business-logic-model.md > §4.3 `_one_turn`, §4.4 `append_for_turn` | "LLM 단계(UoW 밖) -> 저장 단계(UoW 하나)" 분리가 기존 코드와 맞지 않는다. (1) 기존 `TurnAdvancer._apply_active_events`는 이벤트 적용 뒤 `set_region_distortion`으로 왜곡도를 **먼저 저장**하고, `RumorService.append_for_region`은 `_chain_degrees`에서 `repo.get_region_distortion`을 읽어 체인 각도를 정한다. 설계는 이벤트 적용을 "메모리 계산, 저장은 UoW에서"라 했으므로 소문 체인은 적용 전 왜곡도로 생성된다(또는 적용 결과를 append_for_turn에 넘기는 방법이 어디에도 없다). (2) 기존 `_generate_for_region`은 체인마다 `self._repo.upsert_rumor`로 즉시 저장한다 — 설계의 "새 소문을 메모리에 모아 UoW에서 upsert"와 반대이고, 턴이 실패하면 소문만 남는 반쪽 상태가 생겨 BR-U4-14 원자성이 깨진다. (3) `generator.generate_chain(..., take=budget.try_take)`의 `take` 파라미터는 현재 시그니처(`locus/play/rumor/generator.py`)에 없다. | 이벤트 적용 결과(왜곡도 맵, 갱신된 이벤트)를 순수 값으로 돌려주고 그 값을 `append_for_turn`에 넘겨 체인 각도를 계산하도록 데이터 흐름을 명시한다. `append_for_turn`은 저장 없이 소문 목록만 반환하고 UoW가 저장한다고 적는다. `generate_chain`의 예산 훅 추가와 `append_for_region`(수동·기존 테스트 경로)의 동작 보존 방식을 명시한다. | New |
| R-02 | Major | business-logic-model.md > §1 마지막 줄(플레이어 없는 GM 세션 허용) vs §4.2 `_run`·§8 GM `advance`; domain-entities.md > §1.6 `ActionResult.player: Player` | 플레이어 없는 세션에서 GM `advance`(action=None)가 허용되지만 `_run`은 `ActionResult(player=..., changes=player_scope(..., player.region_id))`를 무조건 만든다. `ActionResult.player`는 필수(Optional 아님)이고 `player_scope`는 플레이어 지역이 필요하다. 그러므로 GM 전용 세션(기존 UX, `POST /sessions` 본문 없음)의 턴 진행은 항상 `failed`가 된다. | `ActionResult.player`를 Optional로 하고 플레이어가 없으면 `changes`·`narration` 범위를 정하는 규칙(전체 또는 빈 목록)을 BR로 적는다. 플레이어 없는 세션의 advance를 검증하는 EX를 추가한다. | New |
| R-03 | Major | business-logic-model.md > §4.1 마지막 절(`advance` == `begin`), §8 GM `advance` 202; business-rules.md > BR-U4-29; upstream component-methods.md > P7 | 세 곳이 어긋난다. component-methods P7과 unit-of-work U4 인터페이스는 `advance(session_id, action) -> ActionResult`이다. 설계는 `advance`를 `TurnRun`을 돌려주는 `begin`과 같다고 하고 GM `advance` 라우트도 `TurnResult` 동기 반환에서 202 `TurnRun`으로 바꾼다. 반면 BR-U4-29·Testable 표는 "기존 `TurnResult`·기존 테스트 보존"을 약속한다. 현재 `advance(session_id, *, promotion_threshold)`가 `TurnResult`를 돌려주므로(`locus/play/turn/advancer.py`) 시그니처·반환형·라우트 계약이 모두 바뀌고 기존 advancer/gm API 테스트와 SessionPanel 테스트가 깨진다. §4.1은 services.md §3.4 이탈만 기록했고 P7 시그니처 이탈·GM 계약 변경은 승인 대상으로 기록하지 않았다. 또한 GM 화면은 U7 소유인데 U4가 계약을 바꾼다. | `advance`의 최종 시그니처와 반환형(TurnRun vs TurnResult/ActionResult)을 하나로 정하고, 각 호출자(GM 라우트, `promotion_threshold` 인자 포함, 기존 테스트, 프론트)를 나열한다. P7·A7 이탈은 "설계 이탈"로 명시해 사람이 승인하게 한다. BR-U4-29의 "기존 테스트 보존" 문구를 실제 영향과 일치시킨다. | New |
| R-04 | Major | domain-entities.md > §4 포트 (`InMemoryPlayRepository.uow()` = 상태 스냅샷·예외 시 복원), business-logic-model.md > §10 배경 스레드 | 인메모리 UoW를 "진입 시 전체 상태 스냅샷, 예외 시 복원"으로 정하면서 턴 루프를 별도 스레드에서 돌린다. `memory_repo.py`에는 락이 없고, 요청 스레드(다른 세션의 begin·GM 수동 조작·GET region)가 같은 dict를 동시에 쓴다. 롤백 복원은 그 사이의 다른 쓰기를 지우고(lost update), 읽기는 진행 중 UoW의 중간 상태를 본다. 오프라인 테스트(EX-9, TP-U4-6)와 데모가 인메모리를 쓰므로 계약 테스트가 통과해도 실제 구성에서 비결정적이다. PG 쪽도 기존 store 메서드가 각자 `engine.begin()`을 쓰는데(`postgres_repo.py`), "connection을 공유하는 store 뷰"를 어떻게 만들지(메서드 복제 vs connection 인자) 정해져 있지 않다. | 인메모리 어댑터의 스레드 안전 규칙(저장소 전체 RLock, UoW가 락을 잡는 방식, 또는 복원 대신 쓰기 버퍼 커밋)을 정한다. PG UoW 구현 방식(기존 메서드를 connection 인자로 리팩터링 등)을 한 줄로 확정하고 오프라인(SQLite) 테스트에서의 스레드 동작을 명시한다. | New |
| R-05 | Minor | business-logic-model.md > §4.4 `append_for_turn` 의사코드; business-rules.md > BR-U4-18, EX-11 | 체인은 최대 3개 소문을 만들고 `max_new=2`이다. 의사코드는 `chain_len = min(len(degrees), budget.remaining)`만 쓰고 `max_new`를 반영하지 않아 3번째 소문을 위해 LLM 호출을 쓴 뒤 `out[:max_new]`로 버린다(예산 낭비, 가장 왜곡된 단계만 잘림). EX-11의 "활성 소문 ≤ 지역 상한 누적"은 어떤 상한인지 정의가 없고 턴당 +2가 누적되므로 검증할 수 없다. | `chain_len`에 `max_new - len(out)`를 포함하고 어느 각도 단계를 남길지(앞쪽 잘림) 명시한다. EX-11의 기대값을 측정 가능한 수(턴당 호출 ≤ 8, 지역·턴당 신규 ≤ 2)로 바꾼다. | New |
| R-06 | Minor | business-rules.md > BR-U4-13, business-logic-model.md > §5 | 가드는 `act`·`advance`·`close`만 막는다. 진행 중 턴이 있는 동안 GM의 `set_distortion`·`create/resolve event`·`regenerate`·`adjust_support`는 통과한다. 턴 루프는 이벤트 적용 시 읽은 `cur` 왜곡도로 덮어쓰므로 GM이 그사이 바꾼 값이 조용히 사라진다(FR-E3의 "한 단위" 취지). | 이 쓰기들도 가드를 통과시킬지, 아니면 "진행 중 GM 쓰기는 허용·덮어쓰기 가능"을 명시적 수용 위험으로 적는다. | New |
| R-07 | Minor | business-rules.md > BR-U4-4, BR-U4-25; upstream unit-of-work-story-map.md, unit-of-work.md > U7 | `sync_regions`(FR-E6)는 story map에서 U7 소유(U7 책임 "P4 `sync_regions`(E6)")인데 U4가 BR-U4-4로 구현한다. 플레이 로그 필터는 story map에서 "U4(기본) → U7(필터)"인데 BR-U4-25가 필터를 U4에서 구현한다고 적는다. 두 유닛이 같은 항목을 만들어 U7 계획과 충돌한다. 또한 `current_region`(GET)이 쓰기를 한다. | U4가 가져오는 범위를 명시하고 U7 유닛 정의와의 조정 여부를 기록한다(U4에서 뺄지, U7 항목을 완료로 표시할지). GET의 부수 쓰기가 의도임을 적거나 begin/시작 시점으로 옮긴다. | New |
| R-08 | Minor | business-logic-model.md > §5 `fail_stale_runs`, §10 `shutdown(wait=True)` | `assemble_play`가 컨테이너를 만들 때마다 `running` 행을 `failed("interrupted")`로 닫는다. CLI(`locus world ...`)나 두 번째 프로세스가 조립하면 다른 살아 있는 프로세스의 진행 중 실행을 실패 처리한다. `shutdown(wait=True)`는 LLM이 멈추면 종료를 무기한 막는다. | 정리를 API lifespan 시작에서만 하도록 위치를 정하고, 종료 대기에 상한(타임아웃)을 두거나 수용 위험으로 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `advancer.py`의 `_apply_active_events`가 왜곡도를 저장한 뒤 `append_for_region`이 `get_region_distortion`을 읽는지 | 예 (set_region_distortion 후 _chain_degrees) | R-01 근거 |
| `RumorService._generate_for_region`의 소문 저장 방식 | 체인마다 `repo.upsert_rumor` 즉시 저장 | R-01 근거 |
| `generate_chain` 시그니처에 예산/take 훅 존재 여부 | 없음 | R-01, 신규 변경 필요 |
| `ports.py`에 `PlayUnitOfWork` 정의, 구현체 존재 | 프로토콜만 존재, 구현 없음 (U4 소유 주석) | 설계 §4는 유효, R-04 구현 세부 부족 |
| `memory_repo.py` 락 사용 | 락 없음 (grep) | R-04 근거 |
| component-methods P7 `advance -> ActionResult` vs 설계 | 불일치, BR-U4-29와도 충돌 | R-03 |
| gm.py `advance`가 `TurnResult` 동기 반환 | 예 (line 175) | R-03 영향 범위 |
| story map FR-C6 / FR-E6 소유 | C6 U4→U7 필터, E6 U7 | R-07 |
| 이동 비용·상한 값이 FD-U4 Q1~Q6 A 답과 일치 | 일치 (Q1 ceil(1/w) clamp 5, Q2 2/8, Q3 프로세스 락, Q4 즉시 응답 + 폴링, Q5 현재+이웃, Q6 LLM 없이 이동 허용) | OK |
| `tests/test_boundaries.py` 행렬과 설계의 임포트 방향(play -> knowledge/shared) | 위반 없음 | OK |

### Summary

Q1~Q6 답은 충실히 반영되었으나, 턴 루프의 "LLM 밖 / 저장 UoW 하나" 분리가 기존 왜곡도 저장·소문 즉시 저장 코드와 맞지 않고(R-01), 플레이어 없는 GM 세션이 실패하며(R-02), `advance` 반환형·GM 계약 변경이 BR-U4-29 및 upstream P7과 모순되고(R-03), 인메모리 UoW 롤백이 배경 스레드와 안전하지 않다(R-04). Major 4건이라 NOT-READY이며 모두 이 단계 산출물 안에서 고칠 수 있다.
