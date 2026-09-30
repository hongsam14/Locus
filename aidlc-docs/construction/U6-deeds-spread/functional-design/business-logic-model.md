# U6 행적·전파 — Business Logic Model

근거: `domain-entities.md`, 플랜의 답(Q1 섞은 방식 · Q2=A · Q3=A)과 가정 A6-1~13, services §5, U4 `TurnAdvancer`(`_start` → 배경 `_run_turns` → 턴마다 계산·초안·UoW 하나), U5 `NpcDialogueService`·`build_context`.

## 0. 흐름 한눈에
```
선언   POST act{declare}  → _start(검증·1턴 청구·실행 기록) → 202
       배경: 준비 단계[서술 LLM 1회 → 행적 기록 + ACTION_DECLARED] → 턴 1
대화 마침 POST act{end_talk} → _start(1턴 청구·NPC_TALKED) → 202
       배경: 준비 단계[발언 요약 + 판단 LLM 1회 → 발언 행적 + 판단 + 타임라인] → 턴 1
이동   POST act{move}     → _start(도착 + ARRIVAL 행적) → 202 → 턴 k
턴 한 번: (a) 사건 계산 → (b1) 씨앗(LLM 0) → (b2) 전파(LLM, 먼저) → (b3) 캐노니컬 초안(남은 예산)
         → (c) UoW 하나: 사건·씨앗·전파·초안 저장 → 되먹임·감쇠·가지치기·승격 → 턴 +1
GM     GET deeds · POST deeds/{d}/void (턴 중 409)
```
LLM 호출은 어떤 트랜잭션 안에서도 하지 않는다(services §4). 준비 단계와 턴은 각각 자기 UoW를 연다.

## 1. 행적 기록 — `DeedService` (`locus/play/deeds/service.py`, P16)
```python
class DeedService:
    def __init__(self, repo: PlayRepository, snapshots: SnapshotSource, *, guard: TurnGuard, tuning: PlayTuning)
    def arrival(self, u, session, player, region) -> Deed          # 호출자의 UoW 안
    def current_stay(self, session_id, player) -> list[Deed]       # 가장 최근 ARRIVAL 이후 + 같은 지역, 취소 제외
    def pending_for(self, session_id, player, npc_id) -> list[Deed]
    def seeds_ready(self, session_id) -> list[tuple[Deed, DeedAppraisal]]
    def views(self, session_id) -> list[DeedView]
    def void(self, session_id, deed_id) -> VoidResult
```
- **도착**
  - 세션 시작(`SessionService.start`)과 이동(`TurnAdvancer._start`의 `MoveAction`)이 자기 UoW 안에서 `arrival`을 부른다.
  - 텍스트는 `f"{player.name} arrived in {region.name}."`이다. 목격자는 그 지역 NPC 전원이다.
  - `SESSION_STARTED`·`PLAYER_MOVED` 페이로드에 `deed_id`를 넣는다.
- **체류**: `list_deeds(session, region_id=player.region_id, include_voided=False)` 가운데 `created_at`이 그 지역의 가장 최근 `ARRIVAL` 이후인 것이다. 그 `ARRIVAL`도 포함한다.
- **판단 대기**(`pending_for`): 체류 행적 중 `npc_id ∈ witnessed_npc_ids`이고, 이 NPC의 판단이 아직 없는 것이다(`list_appraisals(deed_ids=…, npc_id=npc_id)`로 뺀다). 최신 순으로 최대 `appraisal_max_deeds`개를 넘긴다. 넘친 오래된 것은 대기로 남는다.
- **씨앗 준비**(`seeds_ready`): 아래 조건을 모두 만족하는 판단이다.
  - `noteworthy ∧ salience ≥ deed_seed_min_salience ∧ retelling.strip() != ""`
  - `seeded_rumor_id is None`
  - 그 행적이 취소되지 않았다.
  - 순서는 `(deed.created_at, appraisal.created_at, appraisal.id)`다.

## 2. 행동 선언 (US-4.5, Q3=A)

### 2.1 요청 — `TurnAdvancer._start` (가드 아래, 동기)
```python
elif isinstance(action, DeclareAction):
    text = action.text.strip()
    if not text: raise InvalidActionError("empty declaration")
    if len(text) > tuning.declare_max_chars: raise InvalidActionError(f"declaration too long (max {…})")
    run.turns_charged = 1; player.turns_spent += 1; u.players.update_player(player)
    run.lang = lang                          # 라우터가 display_lang으로 넘긴 값
```
- 행적은 아직 만들지 않는다. 서술이 없기 때문이다.
- 타임라인도 여기서 남기지 않고, 준비 단계가 `ACTION_DECLARED`를 남긴다.
- 실패한 실행의 보상(U4 `_fail`)이 `turns_charged`를 되돌리는 방식은 그대로다.

### 2.2 준비 단계 — 서술 (`GmNarrator`, `locus/play/gm/narrator.py`, P17)
```python
def narrate(self, *, declaration: str, scene: SceneBrief, lang: str) -> Narration
    # SceneBrief = 지역 이름·설명·NPC(이름·역할)·아는 사실(최대 8, direct→inherited→global)
    #              ·활성 소문(최대 5, 승격→지지도)  ← region_sources 한 번 (U5)
    # structured 출력 NarrationDraft{narration: str, record: str}, LLM 1회
```
- 시스템 문(A-7)
  - "You are the game master of a solo tabletop RPG. Narrate the immediate, plausible outcome of the traveler's declared action in {LANG}, 2–4 sentences."
  - "No dice, no stats, no success check. Stay inside this scene: do not invent facts about other regions or decide the fate of people not present."
  - "Then write `record`: ONE English sentence, past tense, third person, what the traveler did and its visible result."
- 출력 검사
  - `narration.strip()`이 비면 표시 언어의 고정 문구로 채운다.
  - `record.strip()`이 비면 `f"{player.name} declared: {declaration}"`로 채운다.
  - 둘 다 1,000자에서 자른다.
- 예산: 첫 턴의 `LlmBudget`에서 먼저 1을 예약한다(Q2 주석). 남은 예산이 0이면 LLM 없이 간다(BR-U6-24).
- 저장(UoW 하나)
  - `Deed(kind=DECLARED_ACTION, text=record, declaration=원문, witnessed=지역 NPC 전원, turn=session.turn)`
  - `ACTION_DECLARED`에 `narration`·`lang`·`record`·`deed_id`를 넣는다.
- 결과: `ActionResult.declaration = Narration`. 화면은 실행 결과를 폴링해 `NarrationCard`에 보인다.

## 3. 대화 마침과 판단 (US-4.4, Q1 섞은 방식)

### 3.1 요청 — `_start`
U5와 같다. 1턴을 청구하고 `NPC_TALKED`를 남긴다. 판단은 준비 단계에서 한다.

### 3.2 준비 단계 — `NpcDialogueService.appraise` (P13)
```python
def appraise(self, session_id, npc_id, *, budget: LlmBudget) -> AppraisalOutcome
    # 1) new_lines: 이 NPC와의 대화에서 role=player이고
    #    created_at > (이 NPC의 가장 최근 STATEMENT 행적의 messages_through)인 메시지
    # 2) pending: DeedService.pending_for(session, player, npc_id)
    # 3) new_lines도 pending도 없으면 → 호출 없음 (llm_calls=0)
    # 4) LLM 없음 / 예산 0 → 호출 없음, 아무것도 기록하지 않는다 (행적은 대기로 남는다)
    # 5) structured 출력 AppraisalDraft 1회:
    #    {summary: str|null, appraisals: [{ref, noteworthy, salience, slant, retelling}]}
```
- **프롬프트**(`npc/prompts.py::appraisal_prompt`)
  - 시스템 문은 U5 페르소나에 판단 지시를 더한다.
    - "Decide which of the traveler's deeds you would tell others about, true or not, as {name} would."
    - "`retelling` is ONE English sentence in your own voice, as you would pass it on."
    - "If nothing is worth telling, set noteworthy=false."
  - 사용자 문
    - `KNOWN`: 그 NPC가 아는 사실 최대 8개(U5 `build_context`의 facts)
    - `WHAT THE TRAVELER SAID TO YOU`: `new_lines`
    - `DEEDS`: `d1..dn`과 `kind`·`text`
    - 발언이 있으면 `ref="statement"` 항목을 둔다.
  - id는 넘기지 않는다(U5 원칙). `ref`는 별칭이다.
- **출력 검사**(결정적)
  - `ref`가 모르는 값이면 버린다. `salience`는 `clamp01`로 자른다.
  - `noteworthy=False`면 `retelling=""`이다. `noteworthy=True`인데 `retelling`이 비면 `noteworthy=False`로 본다.
  - `pending`에 있는데 출력에 없는 행적은 `noteworthy=False, salience=0, slant=""`로 기록한다. 같은 NPC가 같은 행적을 다음 대화 마침 때 되풀이 판단하지 않게 한다.
  - 발언 판단은 `summary`가 있을 때만 쓴다.
- **저장**(UoW 하나)
  - `summary`가 있고 `new_lines`가 있으면 `Deed(kind=STATEMENT, text=summary, witnessed=[npc_id], messages_through=max(new_lines.created_at))`를 남긴다. `DEED_RECORDED`도 남긴다.
  - `save_appraisals(...)`를 부른다. 판단마다 `DEED_APPRAISED`를 남긴다.
  - `AppraisalExistsError`가 나면 UoW 밖에서 잡고, 이미 있는 짝을 뺀 뒤 한 번 더 저장한다(U5 R-03과 같은 방식). 판단은 턴 가드 아래에서만 저장되므로 이 경로는 방어용이다. 가드 밖에서 쓰는 CLI나 둘째 워커를 막으려는 것이다.
- **Q1 섞은 방식의 효과**
  - 발언은 목격자가 대화 상대 한 명이다. 그래서 판단은 하나이고 씨앗도 최대 하나다.
  - 도착과 선언은 같은 체류 동안 대화를 마친 NPC마다 판단이 하나씩 생긴다. 전할 만하다는 판단마다 그 NPC 판본이 씨앗이 된다.
  - 대화하지 않은 NPC는 판단하지 않는다(A-6).
- **LLM 실패**: 기록하지 않고, 턴은 그대로 진행한다. 이 턴에서 대기 행적은 다음 대화 마침까지 남는다. `ActionResult.llm_failed`를 참으로 둔다.

## 4. 턴 루프 (US-6.5, US-8.6, Q2=A) — `TurnAdvancer._one_turn` 확장
```text
(a) 사건 계산                                         (기존)
(b1) 씨앗: DeedService.seeds_ready(session)            LLM 0
     for (deed, ap) in 준비된 판단:
         region = deed.region_id; 스냅샷에 없으면 건너뛴다 (U4-2 #4 패턴)
         활성 소문 수(region) + 이번 턴 추가 ≥ max_active_rumors_per_region → 건너뛴다 (다음 턴 재시도)
         rumor = RumorService.seed(session, deed, ap, distortion=사건 후 왜곡도(region))
(b2) 전파: 예산이 먼저 여기에 쓰인다                     LLM 1 / 대상
     parents = 행적 기원 활성 소문 (list_rumors_by_origin), 정렬 (−support, id)
     reached[ap] = 그 판단 기원 소문의 지역 집합 (비활성 포함) + 이번 턴 씨앗
     per_region = Counter()
     for p in parents:
         for t in plan_spread(snapshot, p, origin_region_id=deed(p).region_id, reached=reached[p.origin_appraisal_id], tuning):
             if per_region[t.region_id] ≥ max_spread_per_region_turn: continue
             if 활성 상한(t.region_id): continue
             if llm_failed or budget.exhausted: 멈춘다
             budget.take(1); child = RumorService.spread(session, p, t)   # 왜곡 한 단계
             child 없음(LLM 실패) → llm_failed = True (회로 차단, NFR R-02)
             reached[…].add(t.region_id); per_region[t.region_id] += 1
(b3) 캐노니컬 초안                                     (기존, 남은 예산)
(c) UoW 하나: 사건 → 씨앗 upsert + mark_seeded + DEED_SEEDED → 전파 upsert + RUMOR_SPREAD
             → 캐노니컬 초안 → 되먹임 → 강화/감쇠 → 가지치기 → 승격 → 턴 +1 (기존 순서)
```
- 이번 턴의 씨앗은 (c)에서 저장되므로, 다음 턴부터 전파 부모가 된다. 한 턴에 한 칸이다(A6-5).
- 씨앗이 생긴 지역은 그 판단의 `reached`에 곧바로 들어간다. 판본이 원점으로 되돌아오지 않는다.
- 전파한 소문도 지지도·가지치기·승격·되먹임 규칙을 그대로 따른다(FR-E7).
- `TurnResult.seeded_rumor_ids`·`spread_rumor_ids`를 채우고, `rumors_added`(지역별)에도 넣는다.

### 4.1 씨앗 — `RumorService.seed` (LLM 0, 이탈 2)
```python
SessionRumor(
    session_id, region_id=deed.region_id, statement=ap.retelling,
    distorted_from_id=deed.id, distorted_from_kind="deed",
    distortion_degree=distortion, support=clamp01(birth_support * (1 + ap.salience)),
    confidence=clamp01(1 - distortion), origin_kind="deed", origin_deed_id=deed.id,
    origin_appraisal_id=ap.id, spread_from_region_id=None,
    provenance=Provenance(source=SIMULATION, generated_by="deed:appraisal"))
```

### 4.2 전파 계획 — `plan_spread` (순수, `locus/play/rumor/spread.py`, P19)
```python
def plan_spread(snapshot, rumor, *, origin_region_id, reached, tuning) -> list[SpreadTarget]:
    if not is_session_origin(rumor): return []                      # 캐노니컬은 전파하지 않는다
    edges = [c for c in snapshot.topo.connections if is_passable(c)]  # 이동과 같은 통행 규칙
    edges = edges + [reversed_edge(c) for c in edges]                 # 이동처럼 양방향
    reach = best_path_weights(origin_region_id, edges)                # knowledge의 최대 곱 경로
    x = rumor.region_id; wx = reach.get(x, 0.0)
    out = []
    for y, edge_w in neighbours(edges, x):        # 같은 이웃이 여럿이면 가장 큰 가중치
        if y in reached or y not in snapshot.regions_by_id: continue
        w = wx * edge_w
        if w < tuning.spread_min_weight: continue
        out.append(SpreadTarget(region_id=y, from_region_id=x, weight=w,
                                degree=max(rumor.distortion_degree, 1 - w),
                                support=clamp01(rumor.support * edge_w)))
    return sorted(out, key=lambda t: (-t.weight, t.region_id))
```
- 막힌 길은 통행 규칙에서 빠지므로, 막힌 길로만 이어진 지역에는 닿지 않는다. 우회로가 있으면 그 경로의 곱만큼 늦게, 더 약하게 닿는다(US-6.5 둘째).
- 연결은 이동(`move_options`의 `_other_end`)처럼 양방향으로 본다. knowledge의 `best_path_weights`는 방향을 따르므로(hearsay 계산), 역방향 연결을 더해 넘긴다. 사람이 다니는 길이면 소문도 양쪽으로 다닌다.

### 4.3 전파 한 칸 — `RumorService.spread` (LLM 1)
- 부모 문장을 `RumorGenerator.generate_chain(source_text=p.statement, degrees=[t.degree], source_confidence=p.confidence, birth_support=t.support, …)`로 한 단계 왜곡한다.
- 결과에 기원 필드를 붙인다: `origin_*`는 부모에서 복사하고, `spread_from_region_id=t.from_region_id`, `distorted_from_kind="rumor"`로 둔다.
- 생성기가 빈 목록을 돌려주면 `None`이다.

## 5. 취소 — `DeedService.void` (US-5.6, FR-D6)
```python
session = require_open(session_id); guard.assert_idle(session_id)      # 턴 중 409 (U4 GM 쓰기 규칙)
deed = get_deed → 없으면 LookupError (404)
if deed.voided: return VoidResult(deed_id, rumor_ids=[])               # 멱등
with uow: deed.voided=True; deed.voided_turn=session.turn; update_deed
          rs = list_rumors_by_origin(deed_id=deed.id, include_inactive=False)
          for r in rs: r.active=False
          upsert_rumors(rs); DEED_VOIDED{deed_id, rumor_ids, region_ids}
```
- 승격된 소문도 비활성이 된다. 지역 지식은 활성 소문만 읽으므로 "사실"에서 사라진다.
- 번역 행은 지우지 않는다. 소문 행이 남아 있기 때문이다.
- 이후 이 행적의 판단은 씨앗이 되지 않고(`seeds_ready`가 취소 행적을 뺀다), 비활성 소문은 전파 부모가 아니다.

## 6. 재생성은 행적 기원 소문을 지킨다 (services §5.5)
`RumorService.regenerate_region`에서 `dropped`는 `not r.promoted and r.origin_kind == "canonical"`인 것만이다. 행적 기원 소문은 `kept`로 가고, 체인 원천에도 쓰지 않는다(`include_existing=False` 유지). `RegenerateResult.deleted_ids`에는 캐노니컬 소문만 들어간다.

## 7. 컨텍스트 두 곳

### 7.1 NPC 대화 (P12 확장, A6-9)
`build_context(*, npc, facts, rumors, recent, deeds, limits)`에 `deeds: list[DeedMemory]`를 더한다.
- `DeedMemory(deed_id, text, slant)`는 `NpcDialogueService`가 만든다. 재료는 두 가지다.
  - 이 NPC가 판단한 행적(취소 제외)이다. 텍스트는 `retelling`이고, 그것이 비었으면 `deed.text`다.
  - 현재 체류 중 이 NPC가 목격했지만 아직 판단하지 않은 행적이다(`deed.text`). 방금 눈앞에서 한 일을 NPC가 아는 것이 자연스럽다.
- 최신 순으로 `npc_max_deeds`개까지 넣는다. `allowed_ids`에는 그 행적 id도 들어간다.
- 프롬프트 절은 `WHAT YOU SAW OR HEARD OF THE TRAVELER:`이고, 줄은 `- {text}`에 `slant`가 있으면 ` ({slant})`를 붙인다.

### 7.2 사건 제안 (FR-D2 보강, A6-10)
`EventService.suggest_events`가 `context`를 채운다. 취소되지 않은 최근 행적 5개를 `created_at` 역순으로 넣는다.
- 줄 형식은 `- [{region_name}] {deed.text}`다. 전할 만하다는 판단이 있으면 ` (retold: {retelling})`를 붙인다.
- 지역 이름·설명 같은 FR-D2 본체는 U7이다.

## 8. API (A6·A7)
| 경로 | 동작 |
|---|---|
| `POST /api/play/sessions/{s}/act?lang=` `{type:"declare", text}` | 202 `TurnRun`. `lang`은 `display_lang`(U5)이고 선언에서만 쓴다. 400 빈/긴 선언, 409 턴 진행 중·닫힌 세션. **LLM이 없어도 202다**(BR-U6-24) |
| `GET /api/play/sessions/{s}/turn-runs/{id}` | 결과에 `declaration: Narration | null` |
| `GET /api/gm/sessions/{s}/deeds?lang=` | `list[DeedViewOut]`, `created_at` 역순. `text_ko`, 판단 `retelling_ko`, 소문 `statement_ko`, `region_name`·`npc_name`을 채운다. 번역은 캐시 우선·비차단이다(U5와 같음) |
| `POST /api/gm/sessions/{s}/deeds/{d}/void` | `{deed_id, deactivated_rumor_ids: [...]}` 200. 404 없음, 409 턴 진행 중·닫힌 세션. 멱등 |
| 소문 DTO(`RumorOut`, `RegionView.rumors`) | 기원 필드 넷이 모델에서 그대로 나간다(추가만) |
- 번역 kind를 더한다. `deed`의 `text`, `deed_appraisal`의 `retelling`이다. 조립 루트(`api/schemas.py`)에서만 붙인다. play는 localization을 모른다.
- `DeedViewOut`(api DTO) 필드
  - 행적 필드 전부에 `text_ko`, `region_name`, `witness_names`를 더한다.
  - `appraisals`는 판단 필드에 `npc_name`·`retelling_ko`를 더한다.
  - `rumors`는 `RumorOut`이다.
  - `reached_region_ids`·`reached_region_names`를 둔다.
  - 이름은 스냅샷에서 채우고, 사라진 지역이나 NPC는 id를 그대로 쓴다.

## 9. LLM 없을 때 (NFR-4, A6-8)
- **선언**: 받아들인다. `Narration(text=표시 언어 고정 문구, record=f"{player.name} declared: {declaration}", llm_calls=0)`를 만든다. 행적 텍스트에 원문 언어가 섞이는 유일한 경우다(BR-U6-24). 1턴을 쓴다.
- **대화 마침**: 판단 없이 1턴이다. 행적은 대기로 남는다.
- **씨앗**: 판단이 없으니 생기지 않는다.
- **전파**: `rumor_service.llm_available`이 거짓이면 (b2)를 통째로 건너뛴다.
- GM 행적 패널과 취소는 LLM과 무관하게 동작한다.

## 10. 동시성
- 준비 단계는 실행이 가진 턴 가드 아래에서 돈다. 같은 세션의 다른 행동·GM 쓰기·취소는 409다.
- U5 `say`는 가드를 잡지 않으므로 준비 단계와 겹칠 수 있다. 요약 커서 `messages_through`가 요약에 실제로 넣은 마지막 메시지 시각이라, 겹친 발언은 다음 대화 마침 때 요약된다. 잃지 않는다.
- 판단은 가드 아래에서만 저장되므로 같은 세션 안에서는 경합이 없다. `UNIQUE (deed_id, npc_id)`는 가드 밖의 쓰기(CLI, 둘째 워커)에 대한 마지막 방어이고, 복구는 §3.2의 방식이다.
