# U4 플레이어 모드 — Business Logic Model

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG.
**이 유닛이 해 주는 것**: 플레이어가 캐릭터로 세션에 들어가 연결을 따라 이동하고, 행동이 턴을 흐르게 하며, 현재 지역을 한 화면에서 본다. 턴 엔진은 행동을 입력으로 받는 단일 진입점이 되고 폭주 상한·동시성 가드·LLM 예산을 갖는다.

근거: FD-U4 답(Q1~Q6), 플랜의 가정, AD services.md §3.3·3.4·3.7·3.9, component-methods P4~P7·P11, 스토리 맵(FR-C6 "U4 기본 → U7 필터", FR-E6 `sync_regions` = U7). 기존 코드: `locus/play/turn/advancer.py`(8단계 턴, `_apply_active_events`가 사건·왜곡도를 즉시 저장), `rumor/service.py`(`append_for_region` → `_generate_for_region`이 체인마다 `upsert_rumor`, `_chain_degrees`가 저장소의 왜곡도를 읽음), `rumor/generator.py`(`generate_chain`은 degree 하나당 LLM 호출 1회, 실패 시 중단), `session_service.py`, `storage/{memory_repo,postgres_repo}.py`(락 없음 / 메서드마다 `engine.begin()`), `knowledge/query.py::level_path`. 설계 이탈은 §11에 모아 둔다.

## 0. 흐름 한눈에 (Q4=A, 플레이어 경로)
```mermaid
sequenceDiagram
    participant UI as PlayPage
    participant API as /api/play
    participant PS as PlayService
    participant TA as TurnAdvancer
    participant BG as TurnExecutor
    UI->>API: POST /sessions/{s}/act {type: move, to}
    API->>PS: act(s, Move)
    PS->>PS: validate (open, player, adjacent, passable)
    PS->>TA: begin(s, Move)
    TA->>TA: guard.acquire(s) → 409 if running
    TA->>TA: UoW: player.region=to, PLAYER_MOVED, TurnRun(running)
    TA-->>API: TurnRun{id, running, cost_turns}
    API-->>UI: 202 TurnRun
    UI->>API: GET /sessions/{s}/region  (즉시: 새 지역 화면)
    TA->>BG: submit(_run, run_id)
    loop cost_turns
        BG->>BG: compute events (memory) → LLM rumors (budget/caps) → UoW: one turn
    end
    BG->>BG: UoW: TurnRun done(ActionResult) ; guard.release
    UI->>API: GET /sessions/{s}/turn-runs/{id} (폴링) → done → TurnSummaryToast
```
GM 경로(§4.1 `advance`)는 같은 엔진을 **동기**로 돈다: 가드 → 턴 루프 → `ActionResult` 반환. 라우트 계약은 그대로다(§8).

## 1. 세션 시작 — `SessionService.start(world_id, player: PlayerCreate) -> tuple[GameSession, Player]` (FR-C1, RE C4)
```
snapshot = snapshots.get(world_id)                      # LookupError → WorldNotFoundError(404)
if player.start_region_id not in snapshot.regions_by_id: raise InvalidActionError("start region not in world")
with repo.uow() as u:                                   # 한 트랜잭션(C4)
    session = u.sessions.create_session(world_id)
    p = u.players.create_player(Player(session_id=session.id, name=player.name, region_id=player.start_region_id))
    for r in snapshot.topo.regions: u.distortions.set_region_distortion(session.id, r.id, DEFAULT_DISTORTION_DEGREE)
    u.timeline.append_timeline(TimelineEntry(kind=SESSION_STARTED, summary=f"{p.name} arrives in {region_name}", payload={player_id, region_id, region_name}))
return session, p
```
- `close(session_id)`: `guard.assert_idle` → 진행 중 TurnRun이 있으면 409; 아니면 닫고 `SESSION_CLOSED` 타임라인.
- 옛 `start_session(world_id)`(플레이어 없음)는 GM 전용으로 남긴다: 플레이어 없는 세션도 유효하다(GM 화면만 쓰는 경우). 그런 세션에서 `act`는 400 "session has no player"; GM `advance`는 정상 동작한다(§4.5 범위 규칙).
- `sync_regions`(FR-E6, C12)는 **U7**이 맡는다(스토리 맵). U4는 왜곡도 행이 없는 지역을 기본값(`DEFAULT_DISTORTION_DEGREE`)으로 **읽기만** 한다(`get_region_distortion` → None → 기본값; 지금 `_chain_degrees`가 이미 그렇게 한다). GET은 쓰지 않는다.

## 2. 이동 규칙 — `locus/play/player/movement.py` (순수, Q1=A, A-2)
```python
def is_passable(edge: ConnectionEdge) -> bool:
    return str(edge.kind) != "blocked" and edge.weight > 0.0

def move_cost(edge: ConnectionEdge, tuning: PlayTuning) -> int:
    if not is_passable(edge): return 0
    return max(1, min(tuning.max_move_cost, math.ceil(1.0 / edge.weight)))     # 1.0→1, 0.5→2, 0.34→3, 0.2→5

def move_options(snapshot: WorldSnapshot, from_region_id: str, tuning: PlayTuning) -> list[MoveOption]:
    edges = [c for c in snapshot.topo.connections if c.source_region_id == from_region_id]   # 연결은 양방향 엣지로 저장됨
    options = {}
    for c in edges:                                   # 같은 목적지에 연결이 여럿이면 통과 가능한 것 중 최소 비용
        opt = MoveOption(region_id=c.target_region_id, region_name=snapshot.regions_by_id[c.target_region_id].name,
                         kind=c.kind, weight=c.weight, cost_turns=move_cost(c, tuning), passable=is_passable(c),
                         reason=None if is_passable(c) else "blocked pass")
        prev = options.get(opt.region_id)
        options[opt.region_id] = opt if prev is None or (opt.passable and (not prev.passable or opt.cost_turns < prev.cost_turns)) else prev
    return sorted(options.values(), key=lambda o: (not o.passable, o.cost_turns, o.region_name))

def neighbours(snapshot: WorldSnapshot, region_id: str) -> set[str]:
    return {c.target_region_id for c in snapshot.topo.connections if c.source_region_id == region_id}
```
- 불변식(TP-U4-1/2): 가중치가 낮을수록 `cost_turns`가 크거나 같다; `cost_turns ∈ [1, max_move_cost]`; `blocked`·가중치 0은 `passable=False`.

## 3. 플레이어 시점 서비스 — `PlayService(repo, snapshots, query_params, guard, turns, tuning)` (P6)
### 3.1 `current_region(session_id) -> RegionView` (읽기만)
```
session = require(session_id); player = repo.get_player(session_id) or InvalidActionError("session has no player")   # 400
snapshot = snapshots.get(session.world_id)
region = snapshot.regions_by_id[player.region_id]
view = ConsensusEngine.from_snapshot(snapshot, params).resolve(region.id)
facts = region_known(view); hearsay = view.hearsay
rumors = repo.list_rumors(session_id, region.id)                       # 활성만
return RegionView(..., level_path=level_path(region, snapshot), npcs=snapshot.npcs_by_region.get(region.id, []),
                  facts, hearsay, rumors, moves=move_options(snapshot, region.id, tuning),
                  turn_running=guard.is_running(session_id), llm_available=turns.llm_available)
```
### 3.2 `act(session_id, action: PlayerAction) -> TurnRun`
```
session = require_open(session_id); player = require_player(session_id)                      # 409 / 400
match action:
  Move:    opt = next(o for o in move_options(...) if o.region_id == action.to_region_id) or InvalidActionError("not connected")
           if not opt.passable: raise InvalidActionError("blocked pass")
  EndTalk: if action.npc_id not in {n.id for n in snapshot.npcs_by_region.get(player.region_id, [])}: raise InvalidActionError("npc not here")
  Wait:    pass
return turns.begin(session_id, action)                                  # TurnInProgressError → 409
```
### 3.3 `turn_run(session_id, run_id) -> TurnRun` — 저장된 실행 기록(폴링; 없으면 404). `list_runs(session_id, status)`.
### 3.4 `log(session_id) -> list[TimelineEntry]` — U4는 세션 타임라인 전체를 시간순으로 돌려준다(FR-C6 "기본"). 플레이어 시점 필터는 **U7**(스토리 맵 "U7 필터"). 새 종류(`SESSION_STARTED/CLOSED`, `PLAYER_MOVED/WAITED`, `TURN_RUN_FAILED`)는 payload에 `region_name`을 넣어 화면이 이름으로 그린다.

## 4. 턴 엔진 — `TurnAdvancer` (P7; 단일 진입점, AD-R5=B)
생성자: `TurnAdvancer(repo, snapshots, rumors: RumorService | None, feedback, guard: TurnGuard, executor: TurnExecutor, params: PlayTuning)`. `llm_available = rumors is not None`.

### 4.1 두 진입점 — 시그니처 확정 (R-03)
| 메서드 | 시그니처 | 동작 | 쓰는 곳 |
|---|---|---|---|
| `advance` | `advance(session_id, action: PlayerAction \| None = None, *, promotion_threshold=DEFAULT) -> ActionResult` | **동기**. `_start(session_id, action)`(가드 + 즉시 상태) → `_run_turns(run)` → `ActionResult`. P7 형태 그대로 | GM 라우트(`action=None`), 기존 테스트, U5·U6 |
| `begin` | `begin(session_id, action: PlayerAction, *, promotion_threshold=DEFAULT) -> TurnRun` | `_start` 뒤 `executor.submit(self._run, run.id)`로 배경 실행. `TurnRun{running}`을 바로 돌려준다(Q4=A) | `PlayService.act` |

```
def _start(session_id, action) -> TurnRun:                       # 공통 첫 단계
    session = require_open(session_id)
    player = repo.get_player(session_id)                            # GM 세션이면 None
    run = TurnRun(session_id, action, cost_turns=cost(action, player), status="running", started_turn=session.turn)
    guard.acquire(session_id, run.id)                               # TurnInProgressError → 409
    try:
        with repo.uow() as u:
            if Move:    player.region_id = to; player.turns_spent += run.cost_turns; u.players.update_player(player)
                        u.timeline.append_timeline(PLAYER_MOVED, f"{player.name} → {to_name}", {from, to, from_name, to_name, cost})
            elif Wait:  player.turns_spent += 1; u.players.update_player(player); u.timeline.append_timeline(PLAYER_WAITED, ...)
            elif EndTalk: player.turns_spent += 1; u.players.update_player(player)      # NPC_TALKED 등은 U5
            u.runs.create_run(run)
    except BaseException: guard.release(session_id); raise
    return run
```
- 위치는 **즉시** 갱신된다(Q4=A): 플레이어는 도착했고, 세계가 `cost_turns`만큼 뒤따라 움직인다(§11 이탈 1).
- 기존 호출처 `advance(session_id)` / `advance(session_id, promotion_threshold=…)`는 그대로 호출되지만 반환형이 `TurnResult` → `ActionResult`로 바뀐다. 영향: `api/routers/gm.py:179`(라우트는 `result.turns[-1]`을 돌려주어 응답 계약 `TurnResult` 유지), `tests/play/test_advance_turn.py` 21곳 + `tests/play/test_play_services.py` 3곳(`.turns[-1]`로 읽도록 기계적 갱신; 단언 내용은 그대로). 프론트엔드는 영향 없음. 이 목록이 코드 생성 플랜의 호출처 표가 된다.

### 4.2 `_run_turns(run) -> ActionResult` / `_run(run_id)` — 턴 루프
```
def _run_turns(run, *, promotion_threshold) -> ActionResult:        # 가드는 호출자가 잡고 있다
    results = []; used = 0; exhausted = False
    for _ in range(run.cost_turns):
        session = repo.get_session(run.session_id)
        budget = LlmBudget(params.max_llm_calls_per_turn)
        results.append(self._one_turn(session, budget, promotion_threshold))     # §4.3, 자기 UoW로 커밋
        used += budget.used; exhausted |= budget.exhausted
    snapshot = snapshots.get(session.world_id); player = repo.get_player(run.session_id)
    changes = scope_changes(merge_changes(results), snapshot, player.region_id if player else None)      # §4.5
    return ActionResult(session=repo.get_session(sid), player=player, turns=results, changes=changes,
                        narration=narrate(changes), llm_calls=used, budget_exhausted=exhausted, llm_available=self.llm_available)

def advance(session_id, action=None, *, promotion_threshold):        # 동기
    run = self._start(session_id, action)
    try:
        result = self._run_turns(run, promotion_threshold=...)
        with repo.uow() as u: run.status="done"; run.result=result; run.finished_at=now; u.runs.update_run(run)
        return result
    except Exception as exc: self._fail(run, exc); raise
    finally: guard.release(session_id)

def _run(run_id, *, promotion_threshold):                            # 배경(begin이 submit)
    run = repo.get_run(...)
    try:
        result = self._run_turns(run, ...)
        with repo.uow() as u: run.status="done"; run.result=result; run.finished_at=now; u.runs.update_run(run)
    except Exception as exc: self._fail(run, exc); logger.exception(...)
    finally: guard.release(run.session_id)

def _fail(run, exc):
    with repo.uow() as u:
        run.status="failed"; run.error="turn processing failed"; run.finished_at=now; u.runs.update_run(run)
        u.timeline.append_timeline(TURN_RUN_FAILED, "turn processing failed", {run_id, error: str(exc)[:200]})
```
- 이미 흐른 턴은 남는다(각 턴이 자기 UoW로 커밋됨). 실패한 실행은 `failed`로 보이고 플레이어는 다시 행동할 수 있다. 동기 `advance`는 실패를 예외로 올리고(기존 동작) 기록도 남긴다.

### 4.3 `_one_turn(session, budget, promotion_threshold) -> TurnResult` — 기존 8단계 + 상한·예산 (FR-E1, US-8.1; R-01)
세 단계로 나눈다. **계산 단계와 LLM 단계는 UoW 밖**, 저장은 **UoW 하나**.
```
snapshot = snapshots.get(session.world_id)
# ── (a) 계산 단계: 사건 적용을 메모리에서 ──
events = compute_event_application(session, repo)      # 기존 _apply_active_events에서 쓰기를 떼어낸 것: 읽기(list_events, list_region_distortions)만 하고
                                                        # _EventApplication에 + distortions: dict[region_id, float](사건 적용 뒤 값), + event_updates: list[SessionEvent],
                                                        # + timeline: list[TimelineEntry](EVENT_APPLIED/RESOLVED)를 담아 돌려준다. 저장 없음.
# ── (b) LLM 단계: 소문 초안 ──
drafts: dict[str, list[SessionRumor]] = {}; skipped: list[str] = []
if self._rumors is not None:                            # Q6: LLM 없으면 건너뜀
    for region_id in sorted(events.target_regions):
        if budget.exhausted: skipped.append(region_id); continue
        d = events.distortions.get(region_id)
        if d is None: d = repo.get_region_distortion(session.id, region_id) or DEFAULT_DISTORTION_DEGREE
        new = self._rumors.append_for_turn(session, region_id, distortion=d, budget=budget,          # §4.4: 저장하지 않는다
                                           max_new=params.max_new_rumors_per_region_turn, min_source_support=params.min_source_support)
        if new: drafts[region_id] = new
# ── (c) 저장 단계: UoW 하나 ──
with repo.uow() as u:
    for ev in events.event_updates: u.events.update_event(ev)
    for rid, deg in events.distortions.items(): u.distortions.set_region_distortion(session.id, rid, deg)
    for e in events.timeline: u.timeline.append_timeline(e)
    for rs in drafts.values(): u.rumors.upsert_rumors(rs)
    rumors = u.rumors.list_rumors(session.id)                                                  # 활성 전부(새 초안 포함)
    feedback_deltas = self._feedback.apply_feedback(session, rumors, store=u.distortions)     # 되먹임의 왜곡도 쓰기는 UoW store로
    evolve/decay/prune/promote  (기존 3~6단계, 메모리)  → PRUNE/PROMOTE/DEMOTE 타임라인은 u.timeline
    u.rumors.upsert_rumors(rumors)
    new_turn = u.sessions.bump_turn(session.id); u.timeline.append_timeline(ADVANCE_TURN, ..., turn=new_turn)
return TurnResult(..., region_changes=shape_region_changes(..., region_names={r.id: r.name for r in snapshot.topo.regions}),
                  llm_calls=budget.used, budget_exhausted=budget.exhausted, rumors_skipped_regions=skipped)
```
- 규칙: **UoW 안에서 부르는 협력자는 `self._repo`로 쓰지 않는다.** 저장이 필요하면 UoW의 store를 인자로 받는다(`apply_feedback(..., store=)`). 읽기는 UoW 안에서 `u.*`로 한다. PG에서는 `u.*`가 같은 connection(같은 트랜잭션)이고 `self._repo.*`는 다른 connection이라 원자성이 깨지기 때문이다.
- 소문 체인의 degree는 **사건 적용 뒤** 왜곡도로 계산된다(`events.distortions` 우선). 지금 코드가 저장 → 읽기로 얻던 값과 같다.

### 4.4 소문 초안 — `RumorService.append_for_turn(session, region_id, *, distortion, budget, max_new, min_source_support) -> list[SessionRumor]` (FR-E1; R-01, R-05)
```
degrees = chain_degrees_for(distortion)                                          # 순수: [clamp01(f * distortion) for f in DEFAULT_CHAIN_FRACTIONS]; _chain_degrees도 이것을 쓴다
existing = repo.list_rumors(session.id, region_id)                              # 활성
seeded = {r.distorted_from_id for r in existing if r.distorted_from_kind == "knowledge"}
sources = self._collect_sources(world_id, region_id, session.id, min_source_support=..., exclude_knowledge_ids=seeded)   # 캐노니컬 중 이미 파생 소문을 낳은 원본 제외 + 기존 소문 지지도 게이트
out = []
for src in sources:
    n = min(len(degrees), budget.remaining, max_new - len(out))
    if n <= 0: break
    chain = self._gen.generate_chain(..., degrees=degrees[:n], birth_support=...)   # 앞 n단계(가장 낮은 degree부터), 시그니처 변경 없음
    budget.take(n)                                                                  # 시도한 호출 수 = degree 단계 수(generator.py 루프; 실패해도 시도는 계수)
    out.extend(chain)                                                               # 실패 시 chain이 짧을 수 있다(graceful)
return out                                                                          # 저장하지 않는다(초안). len(out) ≤ max_new
```
- `append_for_region`·`generate_rumors`·`regenerate_region`(GM 수동 경로)은 지금처럼 `_generate_for_region`이 체인마다 `upsert_rumor`로 저장한다 — 동작 불변(BR-U4-20). 공통 부분은 `_collect_sources`와 `chain_degrees_for`뿐이고 `_generate_for_region`은 손대지 않는다.
- `LlmBudget`: `remaining`, `take(n)`, `used`, `exhausted`(`remaining == 0`). `TurnResult.llm_calls == budget.used` = 그 턴에 시도한 LLM 호출 수(BR-U4-21).

### 4.5 요약 범위 — `scope_changes(changes, snapshot, player_region_id | None)` (Q5=A; R-02, 순수)
```
if player_region_id is None: return changes                                                   # GM 세션: 모든 지역
keep = {player_region_id} | neighbours(snapshot, player_region_id)                            # 통과 가능 여부 무관
return [rc for rc in changes if rc.region_id in keep]
```
`merge_changes(results)`: 여러 턴의 `RegionTurnChange`를 지역별로 합친다(id 리스트 이어붙임, 중복 제거, `region_name` 유지). `narrate(changes) -> list[str]`: 지역마다 한 문장 템플릿("Riverton: 2 new rumors, 1 promoted, event applied").

## 5. 동시성 가드 — `TurnGuard` (Q3=A, FR-E3; R-06, R-08)
- `acquire(session_id, run_id)`: 락 안에서 `running[session_id]` 검사 → 있으면 `TurnInProgressError`; 없으면 등록. `release(session_id)`, `is_running(session_id)`, `assert_idle(session_id)`.
- **GM의 세션 상태 쓰기**도 가드를 본다: `api/routers/gm.py`의 소문 생성·재생성·지지도·왜곡도·사건 생성/승인/해결/삭제 라우트는 의존성 `_idle(session_id)`(= `guard.assert_idle`)를 거쳐 진행 중이면 409. 그래야 턴이 계산해 둔 왜곡도가 GM의 편집을 덮어쓰지 않는다. 읽기 라우트는 막지 않는다. GM `advance`·`close`도 같은 가드.
- 프로세스 재시작 정리: `repo.fail_stale_runs(reason="interrupted")`는 **API lifespan 시작 시에만**(`api/main.py`) 부른다. `assemble_play`·CLI는 부르지 않는다(다른 프로세스의 실행을 실패시키지 않도록). 단일 워커 전제(운영 문서).

## 6. LLM 없을 때 (Q6=A, US-1.4)
- `PlayContainer.rumors is None`이면 `TurnAdvancer.llm_available=False`: 소문 초안 단계를 건너뛰고 결정적 단계는 돈다. `RegionView.llm_available=False`, `ActionResult.llm_available=False`; 프론트는 배너 "LLM 키가 없어 소문·대화가 생성되지 않습니다".
- `TurnAdvancer`는 항상 조립된다(`rumors=None` 허용). GM `advance`·플레이어 `act`는 200/202로 동작한다; 소문·사건 제안 라우트만 503(U2 그대로).

## 7. 지역 이름 주입 (FR-D3, P11)
`shape_region_changes(..., region_names: dict[str, str])`가 `RegionTurnChange.region_name`을 채운다(없으면 id). 새 타임라인 종류의 payload에도 `region_name`을 함께 넣는다.

## 8. API (A6·A7)
| 경로 | 동작 |
|---|---|
| `POST /api/play/worlds/{w}/sessions` `{name, start_region_id}` | `SessionService.start` → `{session, player}` (201). 본문 없으면(기존 호출) 플레이어 없는 GM 세션 |
| `GET /api/play/sessions/{s}/player` | Player (404 없으면) |
| `GET /api/play/sessions/{s}/region` | `RegionView` (번역 입힘: facts/hearsay/rumors `*_ko`); 플레이어 없으면 400 |
| `POST /api/play/sessions/{s}/act` `PlayerAction` | **202** `TurnRun`; 400 잘못된 행동/플레이어 없음; 409 진행 중/닫힌 세션 |
| `GET /api/play/sessions/{s}/turn-runs/{id}` · `GET .../turn-runs?status=` | `TurnRun`(result 포함) |
| `GET /api/play/sessions/{s}/log` | 세션 타임라인 전체(§3.4) |
| `POST /api/gm/sessions/{s}/advance` | **변경 없음**: 동기, `TurnResult`(= `advance(s).turns[-1]`). 409 `turn in progress` 추가 |
| GM 쓰기 라우트(소문 생성/재생성/지지도/왜곡도/사건) | 기존 계약 + 409 `turn in progress`(§5) |
| 기존 `GET /api/play/sessions/{s}/regions/{r}/knowledge` | 유지(FR-F5) |

## 9. CLI
변경 없음(플레이는 API/UI). `locus world ...` 그대로.

## 10. 배경 실행기 — `TurnExecutor` (R-04, R-08)
- 포트 `TurnExecutor(Protocol)`: `submit(fn, *args) -> None`, `shutdown(timeout: float) -> None`. 구현 `ThreadTurnExecutor`(`ThreadPoolExecutor(max_workers=1, thread_name_prefix="turn")`; 세션 간 직렬 — 단일 워커·데모 규모) 와 테스트용 `SyncTurnExecutor`(`submit`이 즉시 실행). `PlayContainer.executor`.
- 종료: `api/main.py` lifespan이 `executor.shutdown(timeout=settings.turn_shutdown_timeout_s)`(기본 30초)를 부른다: 새 제출을 막고 진행 중 실행을 최대 timeout까지 기다린 뒤 돌아온다. 그 안에 못 끝난 실행은 다음 시작 때 `fail_stale_runs`가 `failed("interrupted")`로 닫는다(§5).
- 저장소 스레드 안전: 인메모리 리포지토리는 전역 `RLock`(UoW 동안 보유), PG는 트랜잭션 한 connection(`_PgStores(conn)`) — domain-entities §4.

## 11. 설계 이탈 기록 (승인 시 함께 받는 것)
| # | 상위 산출물이 말한 것 | 이 설계 | 까닭 |
|---|---|---|---|
| 1 | services.md §3.4: 이동 뒤 턴 루프를 돌고 마지막에 위치 갱신 | 위치는 `_start`에서 즉시 갱신, 세계는 배경에서 뒤따름 | Q4=A(즉시 응답). 플레이어가 도착 화면을 바로 본다 |
| 2 | services.md §3.4·§3.7: `act`가 `TurnAdvancer.advance`를 부르고 결과를 응답 | `act`는 `begin` → 202 `TurnRun` + 폴링; GM `advance`는 동기 그대로 | Q4=A는 플레이어 경로에만 적용. GM 화면(U7)과 기존 테스트·계약을 깨지 않는다 |
| 3 | P7 `advance(session_id, action) -> ActionResult` | 그대로 채택(반환형 `TurnResult` → `ActionResult`), 호출처 24곳 + gm 라우트 매핑 | P7 정합. 갱신 목록은 §4.1 |
| 4 | services.md §3.9·플랜 가정: `sync_regions`를 세션 조회 때 lazily 호출 | U4는 부르지 않음(기본값으로 읽기만); `sync_regions`와 그 호출 지점은 U7(FR-E6) | 스토리 맵의 유닛 배정을 따른다(R-07) |
| 5 | 플랜 가정: 플레이 로그를 플레이어 시점으로 필터 | U4는 타임라인 전체; 필터는 U7 | 스토리 맵 "U4 기본 → U7 필터"(R-07) |
| 6 | 플랜 가정: `TurnGuard`는 `act`/`advance`/`close`만 | GM 쓰기 라우트도 `assert_idle` | 턴 계산값이 GM 편집을 덮어쓰지 않도록(R-06) |
