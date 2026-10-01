## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — U7 (GM 모드·안정화)
**Reviewed artifact:** `aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-01T01:28:14Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md > §6 지역 이름, §4.1·4.2, §4.3 | §6은 "타임라인을 쓰는 서비스는 이미 스냅샷을 읽는다. 쓰는 곳: RumorService, EventService, DistortionService, TurnAdvancer"라고 쓴다. 코드에서 `DistortionService`는 스냅샷을 읽지 않는다. `locus/play/wiring.py:129`가 `DistortionService(store)`로 만들고, `locus/play/distortion_service.py`는 `repo`만 갖는다. 그런데 §4.1(월드 지역마다 한 행), §4.2(`require_region` 404, `region_name` 페이로드)와 BR-U7-6·17·18은 모두 스냅샷이 있어야 한다. `WorldStateService`(§4.3)도 어떤 포트·로더를 받는지 쓰지 않았다. 생성자·조립 변경이 설계에 없어 구현자가 추측해야 한다 | `DistortionService`에 스냅샷 소스(`SnapshotSource`/loader)를 주입하는 변경과 `wiring.py` 조립 변경을 명시한다. §6의 "이미 읽는다" 문장에서 DistortionService를 고치거나 뺀다. `WorldStateService`의 생성자 의존(repo, snapshots)과 `PlayContainer.world_state` 조립 위치를 적는다 | New |
| R-02 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md > §0·§4·§6 (BR-U7-11, EX-15) | BR-U7-11·EX-15·domain-entities §2.2·§7(4)는 플레이어 없는 GM 세션 시작(`POST /worlds/{w}/sessions`)도 `session_started`(`player: null`)를 남긴다고 한다. 현재 `SessionService.create`(`locus/play/session_service.py` 약 55~65행)는 같은 UoW에서 왜곡도만 쓰고 타임라인을 쓰지 않는다. BLM에는 이 흐름(어느 메서드, 어느 UoW, 어떤 페이로드)이 없고 §0 표 행에도 없다 | BLM에 `SessionService.create`의 UoW 안 `session_started` 쓰기를 한 절로 적는다 | New |
| R-03 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md > §1.5, business-rules.md > EX-2 | §1.5 서술은 1~3턴에 소문이 0.5대(0.45 이상)라고 한다. 그러면 BR-U7-1에 따라 1~3턴에도 되먹임이 돌아 몫이 `cap` 0.3까지 쌓인다. 그런데 4턴에 "사건이 해소되어 X는 0.3이 된다(사건 몫만 빠진다)"고 쓴다. 몫이 이미 쌓였다면 해소 뒤 왜곡도는 약 0.6이다. EX-2는 이 수열을 테스트 예제로 가져온다. `step_feedback` 단독 입력 수열로는 맞지만 서술이 모델과 어긋난다 | 1~3턴의 되먹임 누적을 예에 반영하거나, 4턴부터를 "몫 0에서 시작한 입력 수열"로 바꿔 쓴다 | New |
| R-04 | Minor | aidlc-docs/construction/plans/U7-gm-mode-hardening-functional-design-plan.md > A7-2·A7-4 vs business-rules.md > BR-U7-9, business-logic-model.md > §3 | 사람이 게이트에서 볼 수 있는 가정이 설계와 조용히 달라졌다. A7-2는 프롬프트의 지역 최대 12개와 주요 지식 최대 20이라 했고 설계는 `suggest_max_regions`=30, 지역당 지식 2다. A7-4는 재생성 "응답 형태는 그대로"라 했고 설계는 `deleted_ids`→`deactivated_ids`, 페이로드 `deleted`→`deactivated`로 바꾼다. 소비처는 `api/routers/gm.py:158`(번역 정리)과 화면(`deactivated ?? deleted`)뿐이라 영향은 작다 | 완료 메시지나 게이트에서 두 변경을 가정 변경으로 알린다 | New |
| R-05 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/domain-entities.md > §6.2 `delete_rumor` 제거, §1·§6.1 `apply_feedback` 반환형 변경 | "다른 프로덕션 호출처는 없다"는 맞지만(`locus/play/rumor/service.py:151`만), 포트·구현 두 곳(`memory_repo.py:228`, `postgres_repo.py:235,822`)과 테스트 호출 `tests/play/test_repository_contract.py:82`, `tests/play/test_postgres_repo.py:97`이 있다. `apply_feedback`은 지금 `dict`를 돌려주고 `FeedbackOutcome`으로 바뀐다. 이 호출처와 테스트 영향은 적혀 있지 않다 | 코드 계획 단계에서 위 호출처를 열거해 갱신하도록 FD에 한 줄을 남긴다 | New |
| R-06 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md > §2.2 (2) 프롬프트 지역 선택 | `region_briefs`는 계층 순위(상위 단계 먼저), 이름 순으로 정렬한다(`locus/knowledge/query.py:75`). 앞의 30개만 쓰면 지역이 30개를 넘는 월드에서 잎(leaf) 지역이 제안 대상에서 빠진다. 사건은 보통 잎 지역을 겨눈다. 플레이어 지역 맨 앞 규칙만으로는 부족하다. 자르는 순서가 쓰여 있지 않다 | 30개를 넘을 때 어떤 지역을 남길지(플레이어 지역, 활성 사건·소문 지역, 나머지) 정한다 | New |
| R-07 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-logic-model.md > §10 동시성 | "턴 도중 읽으면 지난 커밋 상태를 본다"는 `/state`가 저장소 질의 5회(각각 `_tx`)라 맞지 않는다. 그 사이에 턴이 커밋되면 왜곡도는 새 값, 소문은 옛 값처럼 섞일 수 있다. 표시용이라 치명적이지는 않다 | 문장을 "질의 사이에 커밋이 끼면 섞일 수 있다(표시용이라 허용)"로 고치거나, 읽기를 한 읽기 트랜잭션으로 묶는다 | New |
| R-08 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/frontend-components.md > §2.1 `PlayerStrip` | `api.listTurnRuns(sid)`는 상태 인자가 없으면 세션의 모든 실행을 시작순으로 돌려준다(`web/src/api/play.ts:46`, `memory_repo.py:355`). "가장 최근 하나"는 서버 인자가 아니라 전체를 읽어 고르는 일이 된다. 진행 중 여부만 필요하다 | `listTurnRuns(sid, "running")`을 쓰도록 적는다(`PlayPage`와 같은 호출) | New |
| R-09 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/functional-design/business-rules.md > TP-U7-2, EX-8 | TP-U7-2의 `ceil(share / restore)`는 부동소수 오차로 한 턴 어긋날 수 있다(예: 0.15/0.05가 3.0000000000000004). hypothesis가 찾을 반례다. EX-8은 b가 승격이거나 다른 이유로 남는다는 전제를 쓰지 않았다. b도 비승격 캐노니컬이면 a와 함께 비활성화된다 | TP-U7-2에 허용 오차나 `+1` 여유를 적고, EX-8에 b가 남는 조건(예: 승격 소문)을 적는다 | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 지침 대상 코드 존재: `TurnAdvancer._one_turn`, `RumorFeedbackService.apply_feedback`, `region_feedback`, `decay_support`, `evolve_support`, `promotion.evaluate`, `EventService.resolve/discard/suggest`, `RumorService.regenerate_region` | 모두 존재, 설계의 현재 동작 서술과 일치(되먹임 delta를 `reinforced`에 합침: advancer.py:642-643) | OK |
| `delete_rumor` 호출처 | 프로덕션 1곳(rumor/service.py:151), 구현 3곳, 테스트 2곳 | 설계 주장은 프로덕션에 한해 참. R-05 |
| `DistortionService`의 스냅샷 접근 | 없음(`wiring.py:129`, `distortion_service.py`) | 설계 §6 주장 거짓. R-01 |
| `TimelineKind` 분할(TP-U7-6) | 기존 23 + 신규 3 = 26. OWN 8 + REGION 7 + 숨김 11 = 26, 겹침 없음 | OK |
| 플레이어 로그 순서: 타임라인 정렬 `(turn, created_at, id)` | PG는 앱이 증가 시각을 찍는다(`postgres_repo.py:282-296`, `clock.next_timestamp`) | 같은 UoW 안 순서도 보장됨. OK |
| `player_moved` 페이로드의 `to_region_id`/`region_id`, `session_started.region_id`, `deed_seeded`/`rumor_spread.region_id` | 모두 존재(advancer.py:262·837·854, session_service.py:90) | `player_log` 상태기계 입력 키 OK |
| 승격 평가 임계 | `promotion.evaluate`가 0.6 이상을 자동 승격(promotion.py) | Q4=A의 사실 근거와 일치. 플랜 Q4 서술로 사람이 이미 인지 |
| `_idle` 임대와 GM 쓰기 | `api/routers/gm.py:43,126-320`에 있음 | §10 주장 OK |
| `SessionAppService` | `locus/play/base.py`에 있음(`PlayService`, `DistortionService`가 상속) | `_require_player` 올림 가능. OK |
| `ADDED_COLUMNS` | `locus/play/storage/schema.py:213` | §6.4 OK |
| 에러 매핑 | `api/errors.py`: ValueError(InvalidActionError)→400, LookupError→404, LlmUnavailableError→503 | 새 `LlmCallFailedError`는 503 튜플·`PLAY_ERRORS` 추가가 필요(코드 단계에서 처리 가능) |
| 기존 `data-testid` 존재 | 나열된 12개 모두 `SessionPanel.tsx`에 존재. `approve-`·`discard-`·`resolve-`·`support-`·`promoted-`·`deed-badge-` 접두어는 "event-*"에 들지 않으나 코드 단계에서 보존 | 경미. 목록 외 id도 "기존 것 모두 유지"(BR-U7-25)로 덮임 |
| 상위 ID 해소: FR-A7·C6·D1~D5·E2·E4~E6, US-5.1~5.5·8.2·8.4·8.5 | requirements·stories에 모두 존재, 추적표(§11)와 일치 | OK |
| 상위 변경 선언: `sync_regions`(components.md:154, services.md:115, component-methods.md:160)를 읽기 시점 기본값으로 대체 | 설계가 이탈 2로 명시, US-8.4 넷째 AC는 충족 | 승인된 상위 문서와 다른 선택을 투명하게 밝힘. OK |
| 이월 `F4` 컴포넌트 이름 | unit-of-work의 `ManualTurnButton`을 설계는 `ManualTurnPanel`로 부름 | 사소한 이름 차이 |

### Summary

Critical은 없다. 되먹임(복원·상한), 계보, 플레이어 로그, 조정값의 설계는 현재 코드와 상위 산출물에 맞고 Q1~Q4 답을 그대로 따른다. 가장 큰 문제는 R-01로, 설계가 이미 있다고 믿는 `DistortionService`의 스냅샷 접근이 실제로는 없어 생성자·조립 변경을 명시해야 한다. 나머지는 코드 단계에서 풀 수 있는 Minor다.
