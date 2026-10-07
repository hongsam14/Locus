# U4 플레이어 모드 — Functional Design Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 월드 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U4 — 플레이어가 캐릭터로 세션에 들어가 연결을 따라 이동하고, 행동으로 시간을 흐르게 하며, 현재 지역을 한 화면에서 보는 플레이어 모드의 업무 논리 설계. 턴 엔진이 행동을 입력으로 받는 단일 진입점이 되고(AD-R5=B), 폭주 상한·동시성 가드·LLM 예산을 갖는다(RE C1·C3·C4·C12). 이 단계가 정하는 것은 "행동이 어떻게 턴이 되고, 세계가 어떻게 응답하며, 플레이어가 무엇을 보는가"다.

근거: `inception/application-design/purpose-restructure/{unit-of-work,component-methods,services}.md`(U4 절, P1~P7·P11, §3.3·3.4·3.7), 요구사항 FR-C1·C2·C3·C5·C6·D1·D3·E1·E3·F5·NFR-2·NFR-3·NFR-5, 가정 A-2·A-3·A-5, 스토리 US-3.1~3.4·US-8.1·US-8.3(주) + US-1.4·5.4·6.1(부), RE `code-quality-assessment.md` C1·C3·C4·C12. U2가 남긴 것: `WorldSnapshot`·`WorldCache`(플레이는 캐시로 읽는다), `region_briefs`, NPC 모델(`npcs_by_region`).

## Plan (답을 받은 뒤 만드는 산출물)
- [x] `construction/U4-player-mode/functional-design/domain-entities.md` — `Player`·`PlayerCreate`·`PlayerAction`(Move/Wait/EndTalk)·`ActionResult`·`MoveOption`·`RegionView`·`TurnRun`(Q4에 따라)·`TimelineKind` 추가·`PlayTuning` 추가·`players` 테이블·`PlayUnitOfWork`
- [x] `construction/U4-player-mode/functional-design/business-logic-model.md` — 세션 시작(UoW 하나), `movement`(순수), `PlayService.current_region/act/log`, `TurnAdvancer.advance(session_id, action)`(비용만큼 턴 루프, 가드, 예산·상한·씨앗 제외, LLM은 UoW 밖, 저장 UoW 하나), 지역 이름 주입, API·CLI 조율, LLM 없을 때
- [x] `construction/U4-player-mode/functional-design/business-rules.md` — BR-U4-*(이동 비용·통과, 턴 비용, 상한·예산·씨앗, 가드, 원자성, 요약 범위) + Testable Properties(PBT-03 이동 단조성·범위, 턴당 새 소문 ≤ 상한, LLM 호출 ≤ 예산; PBT-07 `tests/play/strategies.py`)
- [x] `construction/U4-player-mode/functional-design/frontend-components.md` — `/play/:sessionId` 실화면: `RegionScene`·`MovePanel`·`ActionBar`·`TurnSummaryToast`·`PlayLog`(F3), 상태·API 연결·진행 표시
- [x] Plan Review(architecture-reviewer, adversarial ≤ 2) → `construction/U4-player-mode/functional-design/reviews/functional-design-review-NN.md`
- [x] 완료 메시지 + 승인 게이트

---

## Functional Design Questions (FD-U4)

`[Answer]:`에 알파벳. 권장안은 맨 앞. 답을 대화창에서 주셔도 된다.

### FD-U4 Q1 — 이동 비용 공식 (A-5, FR-C2, US-3.3)
**배경**: 요구는 "가중치가 낮을수록 턴을 더 쓴다"까지고 공식은 FD가 정한다(A-5). 연결 가중치는 0~1(1 = 완전히 이어짐, 0 = 끊김), `blocked`는 통과 불가(A-2). 이동 옵션 표시(`MoveOption.cost_turns`)·턴 루프 횟수·PBT-03 단조성 테스트가 이 답에 기댄다. 데모 Aldermoor의 유일한 연결은 `blocked` 0.2다(U8에서 길·강이 늘어난다).

A. **(권장)** `cost = clamp(ceil(1 / weight), 1, max_move_cost)`, `max_move_cost = 5`(PlayTuning). 예: 1.0→1턴, 0.5→2턴, 0.34→3턴, 0.2→5턴. `blocked`는 가중치와 무관하게 통과 불가. 가중치 0(끊김)도 통과 불가 — 단조·연속·상한이 있어 속성 테스트가 간단하고 값 하나로 조정한다.
B. 종류별 고정표: `adjacent`·`route` 1턴, `river` 2턴, 그 외 3턴, `blocked` 불가; 가중치는 동률에서만 순서 결정 — 읽기 쉽지만 가중치가 비용에 거의 안 나타나 "낮을수록 더 소모" 요구가 약해진다.
C. 항상 1턴, 가중치는 표시만 — 가장 단순하지만 FR-C2·US-3.3의 단조성 요구를 만족하지 못한다.
X. Other (please specify)

[Answer]: A

### FD-U4 Q2 — 턴당 상한과 LLM 예산의 값 (FR-E1, NFR-5, US-8.1)
**배경**: RE C1은 사건 하나로 턴마다 9→36→144→576 호출을 재현했다. 설계는 "지역·턴당 새 소문 상한, 턴당 LLM 호출 예산, 이미 파생 소문을 낳은 캐노니컬 원본은 다시 씨앗이 되지 않음"까지 정했고 값은 FD가 정한다. 값은 `PlayTuning`(환경 변수로 조정)에 들어가고 PBT 불변식이 그 값을 쓴다. 이동 1회가 여러 턴을 돌리므로 턴당 예산이 행동당 비용을 결정한다.

A. **(권장)** 지역·턴당 새 소문 ≤ 2, 턴당 LLM 호출 ≤ 8(소문 체인 1개 = 호출 1~3), 예산이 다 되면 그 턴의 소문 추가를 멈추고 `ActionResult.budget_exhausted=true`로 알린다. 캐노니컬 씨앗 제외 = 그 지역에 그 지식에서 파생된 활성 소문이 하나라도 있으면 제외 — 데모 규모(지역 5~15)에서 이동 5턴이라도 호출 ≤ 40으로 예측 가능하다.
B. 넉넉한 값: 지역·턴당 새 소문 ≤ 5, 턴당 호출 ≤ 20 — 세계가 더 빨리 채워지지만 이동 한 번에 호출 100회까지 가능해 비용·대기 시간이 길다.
C. 상한 없이 지지도 게이트(기존 `min_source_support`)만 — 구현은 없지만 RE C1 폭주가 그대로 남는다(US-8.1 실패).
X. Other (please specify)

[Answer]: A

### FD-U4 Q3 — 동시성 가드 방식 (FR-E3, US-8.3, RE C3)
**배경**: 같은 세션에 턴 진행이 동시에 두 번 돌면 세계가 두 번 움직인다. 배포는 단일 uvicorn 워커를 전제한다(U2 Q6=A, compose `--workers 1`). 인메모리 어댑터도 같은 규칙을 지켜야 한다(계약 테스트). GM 수동 턴과 플레이어 행동이 같은 가드를 지난다.

A. **(권장)** 프로세스 안 세션별 락(`TurnGuard`): 두 번째 요청은 기다리지 않고 즉시 409 `turn in progress` — 단일 워커 전제와 맞고 인메모리·PG 어댑터가 같은 코드를 쓴다. 비용: 다중 워커에선 보호가 안 되며, 이는 운영 문서의 전제로 남는다.
B. PostgreSQL 자문 락(`pg_advisory_xact_lock(session)`) + 인메모리 트윈 — 다중 워커에서도 안전하지만 어댑터 둘에 구현이 들고, 락 대기/409 정책을 따로 정해야 한다.
X. Other (please specify)

[Answer]: A

### FD-U4 Q4 — 행동 응답 방식: 즉시 응답 + 배경 턴 처리 vs 동기 (NFR-3, US-3.4)
**배경**: US-3.4는 "지역 화면은 LLM을 기다리지 않고 즉시 바뀐다. 턴 처리(LLM 포함)는 진행 표시와 함께 뒤따른다"고 적었다. 반면 services.md §3.4는 `act`가 턴 루프를 돌리고 `ActionResult`를 돌려주는 동기 흐름으로 적었고, 플레이어 위치 갱신을 루프 "마지막"에 두었다. 둘은 양립하지 않으므로 여기서 정한다. API 계약·가드의 "진행 중" 의미·프론트 진행 표시·타임라인 순서가 이 답에 기댄다.

A. **(권장)** 두 단계: `POST /sessions/{s}/act`는 행동을 검증하고 **플레이어 위치를 즉시 갱신**(이동이면 도착)한 뒤 `TurnRun{id, status: running, cost_turns}`을 바로 돌려준다. 턴 루프는 같은 프로세스의 배경 작업(스레드)에서 돌고, `GET /sessions/{s}/turn-runs/{id}`가 `status`(running/done/failed)와 `ActionResult`를 준다. 가드는 배경 작업이 끝날 때까지 "진행 중"(다른 행동·GM 턴은 409). 프론트는 지역 화면을 즉시 그리고 진행 표시 뒤 요약 토스트를 띄운다 — 스토리를 그대로 만족하고, LLM이 없거나 느려도 화면이 멈추지 않는다. 비용: 실행 기록(`TurnRun`) 저장(인메모리·PG), 폴링 엔드포인트, 프로세스 재시작 시 running 기록의 failed 처리.
B. 동기: `act`가 턴 루프를 다 돌린 뒤 `ActionResult`를 돌려주고 위치는 루프 끝에 갱신(services.md 그대로). 구현이 단순하고 상태가 하나지만, 이동 5턴 × LLM 대기 동안 화면이 멈추고 US-3.4의 "즉시 바뀐다"는 프론트의 낙관적 표시로만 흉내낸다.
X. Other (please specify)

[Answer]: A

### FD-U4 Q5 — 플레이어 시점 요약의 범위 (US-3.4, FR-C6, FR-D3)
**배경**: 턴이 흐른 뒤 "내가 있는 지역과 이웃에서 일어난 일"을 짧게 보인다. 턴 엔진은 지역별 변동(`RegionTurnChange`: 승격·강등·가지치기·사건 적용·해소·새 소문)을 만들고 GM 뷰는 전부 본다. `ActionResult.changes`·`narration`(U4는 LLM 없이 템플릿 문장)·플레이 로그 필터가 이 답에 기댄다.

A. **(권장)** 현재 지역 + 직접 연결된 이웃 지역만(통과 가능 여부 무관, 이름으로 표시); 그 밖의 지역 변동은 GM 뷰·타임라인에만 — 플레이어가 아는 범위와 맞고 요약이 짧다.
B. 모든 지역 변동을 이름으로 — 정보가 많지만 "플레이어 시점"이 아니라 GM 시점이 된다.
X. Other (please specify)

[Answer]: A

### FD-U4 Q6 — LLM 키가 없을 때의 행동 처리 (US-1.4, NFR-4)
**배경**: U2에서 조립은 LLM 없이도 살아 있고 빌드·증강 라우트만 503이다. 플레이의 턴 루프는 사건 적용·되먹임·감쇠·가지치기·승격(결정적)과 소문 생성(LLM)으로 이뤄진다. US-1.4는 "턴 진행을 시도하면 'LLM 키가 필요합니다' 안내가 뜨고 500은 나지 않는다"고 적었다. `act`·GM `advance`의 계약과 데모(키 없이 둘러보기)가 이 답에 기댄다.

A. **(권장)** 이동·대기는 동작한다: 결정적 단계만 돌리고 소문 생성은 건너뛰며 결과에 `llm_available=false`와 안내 문구를 싣는다(프론트가 배너로 보인다) — 키 없이도 지도를 걸어 다니며 hearsay 차이(U2 캐시)를 볼 수 있어 US-1.4·US-6.1 기반이 산다. 비용: 결과 모델에 플래그 하나.
B. 턴이 드는 행동은 전부 503 + 안내("LLM 키가 필요합니다") — 스토리 문구에 가장 가깝지만 키 없이는 이동조차 못 해 "둘러보기"가 지역 화면 하나로 끝난다.
X. Other (please specify)

[Answer]: A

---

## 질문 없이 정하는 것 (가정, 승인 시 함께 확인)
- **플레이어**: 세션당 1명(솔로). `PlayerCreate(name, start_region_id)` 둘 다 필수(US-3.1); 시작 지역은 스냅샷에 있어야 한다. `Player(id, session_id, name, region_id, turns_spent)`; PostgreSQL `players` 테이블(세션당 유일). 스탯·인벤토리 없음(A-3).
- **행동 종류(U4)**: `Move(to_region_id)`, `Wait`, `EndTalk(npc_id)`. `EndTalk`는 U4에선 1턴 소모만(대화·판단은 U5·U6). `Declare`는 U6.
- **턴 비용**: Move = Q1 공식, Wait = 1, EndTalk = 1, GM 수동(`action=None`) = 1.
- **세션 시작 원자성(C4)**: 세션 생성·플레이어 생성·지역 왜곡도 초기화·`SESSION_STARTED` 타임라인을 `PlayUnitOfWork` 하나로. `sync_regions`(C12): 세션 조회 때 스냅샷에 새 지역이 있으면 기본 왜곡도 행을 채운다.
- **UoW**: `PostgresPlayRepository.uow()`는 SQLAlchemy 트랜잭션 하나(`engine.begin()`) 위의 store 묶음; 인메모리 트윈은 스냅샷 복사·롤백으로 같은 계약(계약 테스트 공유). 턴 루프는 LLM 호출을 먼저 끝내고(결과를 메모리에 모음) 저장은 UoW 하나로.
- **타임라인**: `SESSION_STARTED`, `SESSION_CLOSED`, `PLAYER_MOVED`, `PLAYER_WAITED`, `TURN_RUN_FAILED`(Q4=A일 때) 추가. `RegionTurnChange.region_name` 채움(D3).
- **RegionView**: 지역·계층 경로·설명·NPC 목록(스냅샷 `npcs_by_region`)·`facts`(`region_known` = direct+inherited+global)·`hearsay`(전언, `path_decay`)·`rumors`(활성 세션 소문, 왜곡도)·`moves`(`move_options`). 이름은 항상 스냅샷에서.
- **외부 계약 유지(FR-F5)**: `GET /api/play/sessions/{s}/regions/{r}/knowledge`는 그대로 둔다.
- **GM 수동 턴**: `/api/gm/sessions/{s}/advance` → `advance(session_id, None)`; 같은 가드·예산. Q4=A면 GM 턴도 `TurnRun`으로 돌려준다(GM 화면은 폴링).
- **PlayTuning 추가**: `max_move_cost`, `max_new_rumors_per_region_turn`, `max_llm_calls_per_turn`(값은 Q1·Q2).
- **PBT-07**: `tests/play/strategies.py`에 세션·소문·이벤트·스냅샷(연결 가중치 포함) 생성기.
- **프론트(F3)**: `/play/:sessionId`는 `features/play/`의 `RegionScene`(지역·이야기·NPC 목록)·`MovePanel`·`ActionBar`(기다리기)·`TurnSummaryToast`·`PlayLog`; 세션 시작 폼(이름·시작 지역)은 에디터/시작 화면에서 `/play/{sid}`로 이동. 번역 표시는 기존 `LocalizedText` 재사용.
