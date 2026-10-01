# U7 GM 모드·안정화 — Business Logic Model

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U7 기능 설계 중 흐름입니다. 다음을 어떤 순서로 처리하는지 고정합니다.
- 턴 안의 되먹임
- 사건 상태와 제안
- 재생성
- 세계 상태
- 플레이어 로그
- GM 화면 전환

규칙 번호(BR-U7-n)는 business-rules.md, 데이터는 domain-entities.md를 따른다.

## 0. 한눈에
| 흐름 | 바뀌는 곳 | 요구 |
|---|---|---|
| 턴의 되먹임 단계 | `RumorFeedbackService`, `rumor/dynamics.py`, `TurnAdvancer._one_turn` | FR-E2, US-8.2 |
| 사건 상태·제안 | `EventService`, `EventSuggester` | FR-E4, FR-D2, US-5.2, US-8.4 |
| 재생성 | `RumorService.regenerate_region` | FR-E5 |
| 왜곡도 목록·세계 상태 | `DistortionService`, 새 `WorldStateService` | FR-E6, FR-D4 |
| 플레이어 로그 | 새 `player/log.py`, `PlayService.log` | FR-C6 |
| 지역 이름 | 타임라인을 쓰는 모든 곳 | FR-D3 |
| 조정값 | `Settings`, `shared/config/tuning.py`, 상수 사용처 | FR-A7 |
| 넘겨받은 정리 | `NpcDialogueService`, `PlayService`, `SessionAppService` | U5 C1·C4, 대화 500 |
| 화면 | GM 패널 분할, 전환 버튼, 오버레이, 슬라이더 | FR-D1·D4·D5 (frontend-components.md) |

## 1. 턴의 되먹임 (Q2=A, Q4=A)

### 1.1 저장 단계의 순서 (`_one_turn` (c), 바뀌는 줄만)
```
rumors = u.rumors.list_rumors(session.id)                 # ACTIVE
fb = self._feedback.apply_feedback(session, rumors, store=u.distortions)
#    -> FeedbackOutcome(raised: dict[rid, float], restored: dict[rid, float], strong_regions)
reinforced = events.influenced_regions                     # BR-U7-4 (was ∪ feedback)
evolve_support(rumors, events.influenced_regions, reinforce=params.event_support_reinforce)
decay_support(rumors, reinforced, decay=..., exempt_ids=newborn_deed_ids)
... prune → promotion(params.promotion_threshold) → upsert → bump      # 그대로
TurnResult.feedback_regions = sorted(fb.strong_regions)    # 의미 그대로: 강한 소문이 있던 지역
ADVANCE_TURN payload += feedback_restored_regions
```

### 1.2 `RumorFeedbackService.apply_feedback`
1. `deltas = region_feedback(rumors, weight, high_support_threshold)`. 승격 소문은 세지 않는다. 밀도의 분모도 비승격 활성 소문이다.
2. `rows = store.list_region_distortions(session.id)`에서 `states[rid] = FeedbackState(degree, share)`를 만든다.
   - `deltas`에 있는데 행이 없는 지역은 `FeedbackState(DEFAULT, 0)`이다.
3. `steps = step_feedback(states, deltas, cap=params.feedback_cap, restore=params.feedback_restore)`
4. 값이 바뀐 지역만 `store.set_region_distortion(sid, rid, step.degree, feedback_share=step.share)`로 쓴다.
5. `FeedbackOutcome`을 돌려준다.
   - `raised`: `step.raised > 0`인 지역
   - `restored`: `step.restored > 0`인 지역
   - `strong_regions = set(deltas)`

### 1.3 `step_feedback` (순수)
지역마다:
- **올림** (`d = deltas[rid] > 0`)
  - `room = max(0, cap − share)`, `add = min(d, room)`
  - `degree' = clamp01(degree + add)`
  - `raised = degree' − degree`. clamp 뒤의 실제 양이다.
  - `share' = share + raised`
  - 이 지역은 이번 턴에 복원하지 않는다.
- **복원** (`deltas`에 없고 `share > 0`)
  - `back = min(share, restore)`
  - `degree' = clamp01(degree − back)`
  - `restored = degree − degree'`
  - `share' = max(0, share − back)`. 왜곡도가 0에 닿아 덜 내려가도 몫은 `back`만큼 준다. 몫이 0보다 큰 채로 멈추지 않게 하기 위해서다.
- 둘 다 아니면 출력에 넣지 않는다.

### 1.4 다른 쓰기와의 관계
- **사건 해소**
  - 자기 `contributions`만 빼고, 몫은 건드리지 않는다.
  - 해소 뒤 왜곡도가 몫보다 작아질 수 있다. 그래도 복원은 `degree`를 0 아래로 내리지 않고, 몫은 `back`씩 0으로 간다.
- **GM 왜곡도 설정**
  - 정한 값이 새 기준이 된다. `feedback_share=0`으로 쓰고, 지운 몫을 타임라인에 남긴다(BR-U7-5).
- **턴 안 사건 반영** (`events.distortions` 쓰기)
  - `feedback_share=None`이므로 몫을 그대로 둔다. 사건 반영 다음에 되먹임 단계가 같은 UoW에서 돈다.

### 1.5 한 지역이 어떻게 움직이는가 (예) 〔Step 1.3 정정 — 코드 생성 플랜 승인 2026-10-01의 이월 결정 반영〕
`step_feedback`에 넣는 입력 수열이다. 기본값은 `feedback_weight` 0.1, `cap` 0.3, `restore` 0.05이고, 시작 상태는 왜곡도 0.3, 몫 0이다(되먹임이 아직 쌓이지 않은 지역).
- 턴 1: 비승격 소문 4개 중 3개가 0.45 이상이다. `d = 0.1 × 3/4 = 0.075`, 왜곡도 0.375, 몫 0.075
  - 사건 영향이 없으므로 이 소문들은 감쇠한다(−0.05/턴).
- 턴 2: 0.45 이상이 1개 남는다. `d = 0.025`, 왜곡도 0.4, 몫 0.1
- 턴 3: 0.45 이상이 없다. 복원 0.05, 왜곡도 0.35, 몫 0.05
- 턴 4: 복원 0.05, 왜곡도 0.3, 몫 0
- 결과: 왜곡도가 시작값으로 돌아온다(US-8.2 둘째). 0.45~0.6 사이 소문은 감쇠하고, 기준 아래는 가지치기된다(US-8.2 첫째).
- 사건이 함께 도는 동안 쌓인 몫도 같은 방식으로 상한(+0.3) 안에서 쌓이고, 사건 해소(사건 몫만 빠짐) 뒤 강한 소문이 사라지면 턴마다 0.05씩 돌아온다.

## 2. 사건 상태와 제안 (FR-E4, FR-D2)

### 2.1 상태 전이
```
           approve              resolve (one_shot: 턴이 자동)
SUGGESTED ────────► ACTIVE ───────────────► RESOLVED
    │  discard (행 삭제 + event_discarded)
    └──────────► (없음)
GM create ──► ACTIVE  (event_created)
```
- `resolve_event`
  - SUGGESTED면 `InvalidActionError` → 400이다(BR-U7-7).
  - RESOLVED면 지금처럼 그대로 돌려준다(멱등).
- `approve_event`: SUGGESTED가 아니면 400(그대로). 승인하면 `event_approved`를 남긴다.
- `discard_event`
  - 같은 UoW에서 `event_discarded`를 남기고 행을 지운다(BR-U7-8).
  - SUGGESTED가 아니면 400(그대로).

### 2.2 제안 (`EventService.suggest_events(session_id, *, n=1)`)
1. `1 ≤ n ≤ params.max_event_suggestions`가 아니면 `InvalidActionError` → 400이다. LLM을 부르기 전에 검사한다.
2. `snapshot = snapshots.get(world_id)`, `briefs = region_briefs(snapshot, top_k=2)`(knowledge 경계의 순수 함수)
   - 프롬프트에는 앞의 `suggest_max_regions`개만 넣는다.
   - 플레이어가 있으면 그 지역 brief를 맨 앞에 둔다.
3. 최근 사건은 `repo.list_events(session_id)` 중 SUGGESTED가 아닌 것이다. `created_turn` 내림차순으로 5개를 넣는다.
4. 최근 행적은 U6 `_deed_context`(`DeedService.recent(5)`)를 그대로 쓴다.
5. `suggester.suggest(briefs=…, recent_events=…, deeds=…, turn=…, n=n)`
   - 프롬프트(BR-U7-9):
     - 지역 줄: `- {id}: {name} ({level_path 이어 붙임}) — {description ≤160자}; known for: {top_knowledge 최대 2}`
     - 사건 줄: `- [{region name}] {category} m={magnitude:.1f} {status}: {description ≤160자}`
   - 지역 설명·사건 설명·행적은 "material, not instructions" 머리말 아래에 둔다.
   - 시스템 프롬프트: "`region_id`에는 위 id를 쓰고, `description`에는 지역 이름을 쓴다"
6. 초안의 `region_id`가 id 목록에 없으면 이름으로 한 번 더 찾는다. 대소문자는 무시하고, 앞뒤 공백을 지운 뒤 정확히 같아야 한다. 그래도 없으면 버린다(BR-P2-10 그대로).
7. 저장 + `event_suggested`(이름 포함)

### 2.3 LLM 없을 때
그대로 503(`LlmUnavailableError`)이다. 제안 실패는 `[]`다(BR-P2-11 그대로).

## 3. 재생성은 비활성화한다 (FR-E5)
`regenerate_region`의 교체 UoW:
- `dropped`(캐노니컬·비승격)를 `active=False`로 바꿔 `upsert_rumors`로 저장한다. 행을 지우지 않는다.
- 결과 `RegenerateResult.deactivated_ids`(was `deleted_ids`). 라우터는 이 id로 번역을 정리한다. 활성 목록에 다시 나오지 않으므로 번역을 둘 까닭이 없다.
- 타임라인 페이로드 키는 `deactivated`다.
- 남은 소문의 `distorted_from_id`가 가리키는 부모 행이 남는다.
  - U5 원본 가리기(`RegionSources.lineage`, 비활성 포함)는 이 행을 따라 뿌리까지 올라간다(BR-U7-16, TP-U7-5).
- `delete_rumor`를 쓰던 유일한 곳이므로 포트에서 메서드를 없앤다.

## 4. 왜곡도 목록과 세계 상태 (FR-E6, FR-D4)

### 4.1 `DistortionService.list_distortions(session_id)`
1. 세션을 확인한다(닫힌 세션도 읽기 허용, 그대로).
2. `stored = {rd.region_id: rd for rd in repo.list_region_distortions(sid)}`
3. 결과는 `snapshot.topo.regions` 순서로, 지역마다 `stored.get(rid)` 또는 `RegionDistortion(sid, rid, DEFAULT, 0)`이다.
   - 쓰지 않는다(BR-U4-4).
   - 월드에 없는 지역의 행은 넣지 않는다(이탈 6).

### 4.2 `DistortionService.set_region_distortion(session_id, region_id, degree)`
1. 열린 세션인지 확인한다.
2. **`require_region`**: 월드에 없는 지역이면 404다(BR-U7-6). 지금은 확인하지 않는다.
3. 이전 몫을 읽는다. `set_region_distortion(..., clamp01(degree), feedback_share=0.0)`
4. `set_distortion` 타임라인: `region_name`, `degree`, `feedback_share_cleared`
5. 라우터는 저장 뒤 다시 읽은 행을 돌려준다(P10, 지금도 그렇다. `stored is None` 대체 분기는 지운다).

### 4.3 `WorldStateService.state(session_id) -> WorldState` (`locus/play/world_state.py`)
- **읽기**: 세션 → 스냅샷 → (플레이어가 있으면) 플레이어 → 왜곡도 행 → 활성 소문(세션 전체 한 번) → ACTIVE 사건
- **집계**: `summarize_state`(순수)가 한다.
- **비용**: 저장소 질의 5회(세션·플레이어·왜곡도·소문·사건)이고 LLM은 없다. 지역 수만큼 질의가 늘지 않는다(TP-U7-7, NFR).
- 닫힌 세션도 읽을 수 있다.
- 조립: `PlayContainer.world_state`

### 4.4 GM 세션 시작 기록 (BR-U7-11) 〔Step 1.3 정정 — 코드 생성 플랜 승인 2026-10-01의 이월 결정 반영〕
- `SessionService.start_session(world_id)`(플레이어 없는 GM 세션)은 세션 생성·왜곡도 기본 행과 같은 UoW에서 `session_started` 줄을 쓴다.
- 페이로드는 `{"player": null}`이고 `region_id`는 없다. 플레이어 로그의 `here`는 `None`으로 남는다.

## 5. 플레이어 로그 (FR-C6, Q3=A)
`PlayService.log(session_id)` = `player_log(repo.list_timeline(session_id))`

`player_log`는 순수 함수이고, 기록 순서대로 한 번 지나간다.
```
here = None; seen_events = set()
for e in entries:
    if e.kind == session_started:  here = e.payload.get("region_id"); seen_events = set()
    if e.kind == player_moved:     here = e.payload["to_region_id"]; seen_events = set()
    if e.kind in OWN_KINDS:        keep
    elif e.kind in REGION_KINDS and here is not None and e.payload.get("region_id") == here:
        if e.kind == event_applied:
            if e.payload["event_id"] in seen_events: skip
            seen_events.add(e.payload["event_id"])
        keep
    else: skip
```
- `player_moved`는 행동 요청(`_start`) 때 쓰인다. 그 뒤 이동 턴들의 줄은 도착 지역 기준이다(U4 규칙: 이동하면 바로 도착).
- `region_id`가 없는 지난 지역 줄(U7 이전의 `promote`·`prune` 등)은 숨는다.
- GM 타임라인(`GET /api/gm/.../timeline`)은 그대로 전부 보인다.

## 6. 지역 이름 (FR-D3)
- 이름표는 `{r.id: r.name for r in snapshot.topo.regions}` 하나로 만든다. 〔Step 1.3 정정 — 코드 생성 플랜 승인 2026-10-01의 이월 결정 반영〕
  - `RumorService`, `EventService`, `TurnAdvancer`는 이미 스냅샷 소스를 갖는다.
  - `DistortionService`는 지금 `repo`만 갖는다. 생성자를 `DistortionService(repo, snapshots)`로 바꾸고 `wiring.py`가 `loader`를 넘긴다.
  - `WorldStateService(repo, snapshots)`를 새로 두고 `assemble_play`가 `PlayContainer.world_state`에 조립한다.
- 지역이 사라졌으면 id를 이름 자리에 쓴다(U6 규칙 그대로).
- `summary` 문장도 이름으로 쓴다(예: `promoted rumor in Riverton`).
- 턴의 `promote`·`demote`·`prune` 줄은 소문의 `region_id`로 이름을 찾는다.
- `event_resolved`(GM 해소와 턴의 one_shot 자동 해소 둘 다)는 사건의 `region_id`를 싣는다.
  - 턴의 자동 해소는 지금 `event_applied` 줄만 남긴다. `resolved_ids`는 `advance_turn` 페이로드에만 있다.
  - U7은 one_shot 자동 해소에도 `event_resolved` 줄을 남긴다. 그래야 플레이어 로그가 "사건이 끝났다"를 보인다.

## 7. 조정값 조립 (FR-A7)
- `Settings`에 §5의 env 필드를 더한다.
- `knowledge_tuning()`·`play_tuning()`·**`world_tuning()`**이 frozen dataclass를 만든다.
- **knowledge**: `ConsensusParams`는 이미 `knowledge_tuning()`에서 한 번 만든다(U1). 값만 env를 따른다.
- **world**
  - `assemble_world`가 `WorldTuning`을 받는다.
  - 토폴로지 빌더는 `compute_weight(kind, terrains, *, tuning)`, 온톨로지 dedup은 `threshold=tuning.dedup_threshold`로 쓴다.
  - 모듈 상수는 `WorldTuning()` 기본값과 같은 값을 가진 기본 인자로 남는다.
- **play**
  - `event/dynamics.py`의 세 함수는 키워드 인자(`max_delta`, `min_weight`, `reinforce`)를 받는다.
  - `TurnAdvancer`는 `self._params`에서 넘긴다. `promotion_threshold` 인자의 기본값은 `None`이고, 그러면 `params.promotion_threshold`다.
- **확인**: 설정을 바꾸면 그 값이 실제 계산에 쓰인다(TP-U7-8 예제: env `EVENT_MAX_DELTA=0.1` → 한 턴 +0.1).

## 8. 넘겨받은 정리
| 항목 | 흐름 |
|---|---|
| U5 C1 N+1 | `npcs_here`와 EndTalk가 `message_counts(session_id)` 한 번으로 NPC별 메시지 수를 얻는다. `get_conversation` N회가 사라진다. 웹은 `say` 뒤 NPC 목록을 다시 읽지 않고 그 NPC의 수를 +2 한다 |
| U5 C4 남은 것 | `PlayService.params` 인자·속성을 없앤다(아무도 읽지 않음). `_require_player(session_id)`를 `SessionAppService`로 올리고, `PlayService`·`NpcDialogueService`의 복사본을 지운다 |
| 대화 LLM 실패 | `say`에서 `self._llm.complete(...)`가 예외를 내면 `LlmCallFailedError`로 바꾼다. 메시지는 저장하지 않는다(플레이어 줄도). 라우터는 503과 고정 문구 `"the NPC could not answer right now; try again"`을 준다. 화면은 입력을 지우지 않는다 |

## 9. API (A7)
| 메서드·경로 | 변경 |
|---|---|
| `GET /api/gm/sessions/{s}/state` | **새**. `WorldStateOut`(`WorldState` + 지역 이름은 그대로, 번역 없음) |
| `GET /api/gm/sessions/{s}/distortions` | 현재 월드 지역마다 한 행(§4.1). `feedback_share` 필드가 붙는다 |
| `PUT /api/gm/sessions/{s}/regions/{r}/distortion` | 없는 지역 404. 몫 0으로 |
| `POST /api/gm/sessions/{s}/events/suggest?n=` | `n` 1~5 밖이면 400 |
| `POST /api/gm/sessions/{s}/events/{e}/resolve` | SUGGESTED면 400 |
| `DELETE /api/gm/sessions/{s}/events/{e}` | 타임라인 남김(응답 204 그대로) |
| `GET /api/play/sessions/{s}/log` | 플레이어 시점 필터(§5) |
| `POST /api/play/sessions/{s}/npcs/{n}/say` | LLM 실패 503 |
| `GET /api/play/sessions/{s}/npcs` | 응답 그대로, 질의 1회 |

## 10. 동시성과 LLM 없을 때
- 되먹임·복원은 턴 UoW 안에서만 쓴다. GM 왜곡도 설정은 `_idle` 리스 아래에서 쓴다(그대로). 그래서 몫을 두 쪽이 동시에 쓰지 않는다.
- `/state`·`/distortions`·`/log`는 읽기만 하고 가드를 잡지 않는다. `/state`의 다섯 읽기는 묶지 않으므로, 그 사이에 턴이 커밋되면 한 번은 섞인 값(예: 새 왜곡도와 옛 소문 수)이 보일 수 있다. 표시용이라 받아들이고 다음 읽기가 고친다(NFR N7-2). 〔Step 1.3 정정 — 코드 생성 플랜 승인 2026-10-01의 이월 결정 반영〕
- LLM이 없어도 새 결정적 흐름은 모두 돈다. 대상은 되먹임 복원, 상태, 로그, 이름, 사건 전이다. 제안만 503이다.

## 11. 화면 (요약, 자세한 것은 frontend-components.md)
- **플레이 화면**: "GM 모드" 버튼으로 `/gm/:sid`에 간다.
- **GM 화면**
  - "플레이로 돌아가기"와 플레이어 띠(이름·지역 이름·턴), 지도의 플레이어 표시를 둔다.
  - 패널: `ManualTurnPanel`·`EventPanel`·`RumorPanel`·`DistortionPanel`·`TimelinePanel`·`DeedPanel`, 지도 위 `WorldStateOverlay`
- **슬라이더**: `CommitRange`로 마우스·키보드·터치·포커스 해제 모두 저장한다. 같은 값은 보내지 않는다.
