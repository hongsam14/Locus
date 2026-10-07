# Component Methods — Purpose Restructure (2026-09-29)

> 시그니처와 입출력 타입만 정한다. 규칙·공식·프롬프트는 유닛별 Functional Design에서 정한다.
> 표기: 타입은 `shared/models` 또는 각 경계의 `models.py`에 있다. `*`는 키워드 전용.

## shared

### S1 models (신규·변경 모델)
```python
class NPC(LocusModel):
    id: str; world_id: str; name: str; role: str; description: str
    home_region_id: str; traits: list[str] = []; provenance: Provenance

class WorldSnapshot(BaseModel):   # 로더 출력, 캐시 단위
    world_id: str; kg: KnowledgeGraph; topo: RegionTopology; npcs: list[NPC]
    regions_by_id: dict[str, Region]; npcs_by_region: dict[str, list[NPC]]

class ScopeType(str, Enum): DIRECT | INHERITED | PROPAGATED | GLOBAL | HEARSAY
class ConsensusView: direct, inherited, global_knowledge, propagated, hearsay, unknown_count
class KnowledgeView: knowledge_id, statement, title, scope_type, is_hearsay: bool, confidence, path_decay: float | None, source: str | None, region_id: str | None
class SourceKind(str, Enum): INPUT | INFERRED | AUGMENTATION | SIMULATION | DIALOGUE
class ImportReport(BaseModel): world_id, format_version, counts: dict[str, int], replaced: bool, warnings: list[BuildWarning]
class BuildReport(...): + unscoped_knowledge_ids: list[str], llm_calls: int, ok: bool  # ok = errors 없음
```

### S2 config
```python
def get_settings() -> Settings
Settings.world_tuning() -> WorldTuning          # BASE_WEIGHT, TERRAIN_MODIFIER, dedup_threshold, max_corroborations, low_confidence
Settings.knowledge_tuning() -> KnowledgeTuning  # propagate_min=0.5, hearsay_min=0.15
Settings.play_tuning() -> PlayTuning            # max_event_delta, propagate_min_weight, promotion_threshold, support_decay, prune_floor,
                                                # min_source_support, feedback_weight, high_support_threshold, birth_support,
                                                # max_new_rumors_per_region_turn, max_llm_calls_per_turn, move_cost_base, move_cost_scale
Settings.localization() -> LocalizationSettings # enabled, target_lang, warm_workers
```

### S4 storage (변경분)
```python
class GraphRepository(Protocol):
    upsert_nodes(nodes: list[Node]) -> None; upsert_edges(edges: list[Edge]) -> None
    get_node(world_id, node_id) -> Node | None; find_nodes(world_id, label, filters=None) -> list[Node]
    get_edges(world_id, types: list[str] | None = None) -> list[Edge]
    delete_node(world_id, node_id) -> None; delete_world(world_id) -> None
    list_world_ids() -> list[str]                      # 신규 (월드 목록)
    connect/disconnect/health_check/ensure_schema
graph_mapping: npc_to_node(npc) -> Node; node_to_npc(node) -> NPC; lives_in_edges(npcs) -> list[Edge]; edge_to_relation(edge) -> Relation
persist_graph(graph, search, embedding, world_id, *, regions, entities, knowledge, npcs, priors, prior_links, connections, scopes, relations) -> list[BuildWarning]
```

### S5 sql
```python
def make_engine(url: str, *, echo: bool = False) -> Engine
```

## knowledge

```python
# K1
class ConsensusParams: propagate_min: float; hearsay_min: float
def compute_consensus(region_id: str, *, snapshot: WorldSnapshot, params: ConsensusParams) -> ConsensusView
class ConsensusEngine:  __init__(snapshot, params);  resolve(region_id) -> ConsensusView
# K2
def best_path_weights(start_id: str, connections: list[ConnectionEdge]) -> dict[str, float]
# K3
class WorldLoader:  __init__(graph: GraphRepository);  load(world_id) -> WorldSnapshot
# K4
class WorldCache:   __init__(loader);  get(world_id) -> WorldSnapshot;  invalidate(world_id) -> None;  clear() -> None
# K5
class QueryEngine:
    __init__(cache: WorldCache, params: ConsensusParams)
    knowledge_for_region(world_id, region_id, *, include_hearsay: bool = True) -> QueryResult
    diff_regions(world_id, region_a, region_b) -> RegionDiff
    region_known(view: ConsensusView) -> list[KnowledgeView]        # direct + inherited + global (옛 canonical_known)
    region_briefs(world_id, *, top_k: int = 3) -> list[RegionBrief]  # RegionBrief(region_id, name, description, level_path, top_knowledge: list[str])
# K6
def assemble_knowledge(shared: SharedContainer) -> KnowledgeContainer
@dataclass class KnowledgeContainer: loader: WorldLoader; cache: WorldCache; query: QueryEngine; params: ConsensusParams
```

## world

```python
# W1
class WorldInputs(BaseModel): memos: list[str]; map_images_b64: list[str]; structured_maps: list[dict]; concept_arts_b64: list[str]
class IngestionService: ingest_all(world_id, inputs: WorldInputs) -> IngestionResult
def merge_results(world_id, results: list[IngestionResult]) -> IngestionResult   # 힌트·parent 보존, id 재매핑 적용
# W2
class TopologyBuilder: __init__(tuning: WorldTuning, wiki: CommonsenseWiki | None); build(ingestion, *, world_id) -> tuple[RegionTopology, list[BuildWarning]]
# W3
class OntologyBuilder: __init__(llm, embedding, wiki, tuning); build(ingestion, topology, *, world_id) -> tuple[KnowledgeGraph, list[str]]  # (kg, unscoped_ids)
# W4
class WikiAdmin: upsert_prior(prior) -> WikiPrior; list_priors(world_id) -> list[WikiPrior]; prior_refs(world_id, *, edge=None, knowledge_id=None) -> list[PriorRef]
# W5
class AugmentationRun(BaseModel): id, world_id, status: RunStatus, questions: list[AugmentationQuestion], history: list[ChangeSet], round: int
class AugmentationQuestion: id, issue_type, target_ids: list[str], region_id: str | None, text, options: list[AnswerAction]
class AugmentationService:
    start_run(world_id) -> AugmentationRun; answer(run_id, answer: AugmentationAnswer) -> ChangeSet
    revert(run_id, change_id) -> None; get_run(run_id) -> AugmentationRun
# W6
class WorldBuilder:
    __init__(ingestion, topology_factory, ontology_factory, wiki_factory, distiller, linker, graph, search, embedding, cache: WorldCache, tuning)
    build(world_id, inputs: WorldInputs, *, replace: bool = False) -> BuildReport
# W7
class WorldEditor:
    __init__(graph, search, embedding, cache: WorldCache)
    list_worlds() -> list[WorldInfo]                                  # WorldInfo(world_id, name, region_count, updated_at)
    upsert_region(region: Region) -> Region; delete_region(world_id, region_id, *, cascade: CascadePolicy) -> DeleteReport
    upsert_connection(edge: ConnectionEdge) -> ConnectionEdge; delete_connection(world_id, a: str, b: str) -> None
    upsert_knowledge(k: Knowledge, *, scope_region_ids: list[str] | None = None) -> Knowledge
    set_scopes(world_id, knowledge_id, region_ids: list[str]) -> list[ScopeLink]
    list_unscoped(world_id) -> list[Knowledge]
    upsert_npc(npc: NPC) -> NPC; delete_npc(world_id, npc_id) -> None
    delete_node(world_id, node_id) -> None                            # Neo4j + OpenSearch 함께
# W8
class NpcDraftService: __init__(llm, cache); suggest(world_id, region_id, *, n: int = 3) -> list[NpcDraft]
# W9
class WorldFile(BaseModel): format_version: int; world: WorldMeta; regions; connections; entities; relations; knowledge; scopes; priors; prior_links; npcs
class WorldFileExporter: __init__(cache); export(world_id) -> WorldFile
class WorldFileImporter: __init__(graph, search, embedding, cache); import_(world_id, file: WorldFile, *, replace: bool = True) -> ImportReport
# W10
class DemoWorlds: list() -> list[DemoInfo]; load(name, world_id, *, replace: bool = True) -> ImportReport; build_from_sources(name, world_id) -> BuildReport
# W11
def assemble_world(shared, knowledge) -> WorldContainer
@dataclass class WorldContainer: builder; editor; augmentation; wiki_admin; cross_world; exporter; importer; demo; npc_drafts
```

## play

```python
# P1 (발췌)
class Player(LocusModel): id; session_id; name; region_id; turns_spent: int
class PlayerCreate(BaseModel): name: str; start_region_id: str
class PlayerAction: Move(to_region_id: str) | Wait() | EndTalk(npc_id: str)
class ActionResult(BaseModel): session: GameSession; player: Player; turns: list[TurnResult]; changes: list[RegionTurnChange]; llm_calls: int; narration: list[str]
class Conversation(LocusModel): id; session_id; npc_id; started_turn; messages: list[Message]
class Message(LocusModel): role: Literal["player","npc"]; text; turn; created_at
class RegionView(BaseModel): region: Region; level_path: list[str]; npcs: list[NPC]; facts: list[KnowledgeView]; hearsay: list[KnowledgeView]; rumors: list[SessionRumor]; moves: list[MoveOption]
class MoveOption(BaseModel): region_id; region_name; kind: ConnectionKind; weight: float; cost_turns: int; passable: bool

# P2 ports (Protocol, 요약)
SessionStore: create/get/list_by_world/close/bump_turn
PlayerStore: create/get_by_session/update
RumorStore: upsert_many/list_by_region(active_only)/list_by_session/deactivate_many
EventStore: insert/update/list(status)/get/delete
DistortionStore: get/set/list/set_many
TimelineStore: append/list
ConversationStore: get_or_create/append_message/list_by_session
class PlayUnitOfWork(Protocol): __enter__/__exit__; sessions; players; rumors; events; distortions; timeline; conversations

# P3
class PostgresPlayRepository(SessionStore, PlayerStore, RumorStore, EventStore, DistortionStore, TimelineStore, ConversationStore):
    __init__(engine: Engine); uow() -> PlayUnitOfWork; ensure_schema() -> None
class InMemoryPlayRepository: (동일 인터페이스)

# P4
class SessionService:
    __init__(uow_factory, cache: WorldCache)
    start(world_id, player: PlayerCreate) -> tuple[GameSession, Player]
    close(session_id) -> GameSession; get(session_id) -> GameSession; list(world_id) -> list[GameSession]
    timeline(session_id) -> list[TimelineEntry]; sync_regions(session_id) -> int

# P5 movement (pure)
def move_options(snapshot: WorldSnapshot, from_region_id: str, tuning: PlayTuning) -> list[MoveOption]
def move_cost(edge: ConnectionEdge, tuning: PlayTuning) -> int
def is_passable(edge: ConnectionEdge) -> bool

# P6
class PlayService:
    __init__(uow_factory, cache, query: QueryEngine, rumors: RumorService, turns: TurnAdvancer, tuning)
    current_region(session_id) -> RegionView
    act(session_id, action: PlayerAction) -> ActionResult
    log(session_id) -> list[TimelineEntry]

# P7
class TurnAdvancer:
    __init__(uow_factory, cache, rumors, events, feedback, distortions, guard: TurnGuard, tuning)
    advance(session_id, action: PlayerAction | None = None) -> ActionResult
class TurnGuard: acquire(session_id) -> ContextManager   # 잠금 실패 → TurnInProgressError(409)

# P8 (변경 시그니처만)
class RumorService:
    generate(session_id, region_id, *, degrees=None) -> list[SessionRumor]
    regenerate(session_id, region_id) -> list[SessionRumor]          # 부모 deactivate
    append_for_turn(session, region_ids, *, budget: LlmBudget) -> list[SessionRumor]   # 상한·씨앗 제외 규칙
    adjust_support(session_id, rumor_id, support) -> SessionRumor
    list_active(session_id, region_id) -> list[SessionRumor]

# P9
class EventSuggester: suggest(*, briefs: list[RegionBrief], recent_events: list[SessionEvent], turn: int, n: int) -> list[EventDraft]
class EventService:
    create(session_id, draft: EventCreate) -> SessionEvent; suggest(session_id, *, n) -> list[SessionEvent]
    approve(session_id, event_id) -> SessionEvent; resolve(session_id, event_id) -> SessionEvent; discard(session_id, event_id) -> None
    list(session_id, status=None) -> list[SessionEvent]

# P10
class DistortionService: list(session_id) -> list[RegionDistortion]; set(session_id, region_id, degree) -> RegionDistortion

# P11
def shape_region_changes(*, snapshot, promoted, demoted, pruned, applied_events, resolved_events, added_by_region, feedback_regions) -> list[RegionTurnChange]

# P12 (pure)
class NpcContext(BaseModel): npc: NPC; facts: list[KnowledgeView]; hearsay: list[KnowledgeView]; rumors: list[SessionRumor]; recent: list[Message]; allowed_ids: set[str]
def build_context(*, npc: NPC, known: list[KnowledgeView], rumors: list[SessionRumor], recent: list[Message], limits: ScopeLimits) -> NpcContext

# P13
class NpcDialogueService:
    __init__(llm, uow_factory, cache, region_knowledge: SessionKnowledgeService, tuning, lang: str)
    start(session_id, npc_id) -> Conversation
    say(session_id, npc_id, text: str) -> NpcReply            # NpcReply(message: Message, llm_calls: int)
    history(session_id, npc_id) -> Conversation

# P14
class SessionKnowledgeService:
    __init__(uow_factory, cache, query: QueryEngine)
    for_region(session_id, region_id) -> QueryResult           # source: "canonical" | "rumor" | "rumor:promoted"

# P15
def assemble_play(shared, knowledge) -> PlayContainer
@dataclass class PlayContainer: sessions; play; turns; rumors; events; distortions; dialogue; region_knowledge; repo
```

## localization

```python
class Translation(LocusModel): id; source_kind: str; source_id: str; source_field: str; target_lang: str; text: str; source_hash: str; world_id: str | None; session_id: str | None
class TranslationStore(Protocol): get_many(keys) -> dict[key, Translation]; upsert_many(items) -> None; purge(source_kind, source_ids) -> None
class Translator: __init__(llm); try_translate(text, *, target_lang) -> str | None
class TranslationService:
    __init__(store, translator, *, settings: LocalizationSettings, warm_executor)
    enrich(items: Sequence[Any], *, kind: str, fields: Sequence[str], lang: str | None = None, world_id: str | None = None, session_id: str | None = None, id_attr="id") -> dict[str, dict[str, str]]
    purge(kind, ids) -> None; shutdown() -> None
def assemble_localization(shared) -> LocalizationContainer
```

## api

```python
def create_app(*, shared: SharedContainer | None = None, knowledge=None, world=None, play=None, localization=None) -> FastAPI
# deps.py
def get_world(request) -> WorldContainer   # 없으면 HTTPException(503, "world boundary unavailable")
def get_knowledge(request) -> KnowledgeContainer; get_play(request) -> PlayContainer; get_localization(request) -> LocalizationContainer | None
# schemas.py (발췌)
class LocalizedKnowledgeView(KnowledgeView): statement_ko: str | None; title_ko: str | None
class RumorOut(SessionRumor): statement_ko: str | None; region_name: str
class EventOut(SessionEvent): description_ko: str | None; region_name: str
class WorldStateOut: regions: list[RegionStateOut(region_id, name, distortion, active_rumors, promoted)]
```

## web (요약)
```ts
// api/world.ts
listWorlds(); loadDemo(name, worldId); buildWorld(worldId, form: FormData); exportWorld(worldId); importWorld(worldId, file);
upsertRegion/deleteRegion/upsertConnection/deleteConnection/upsertKnowledge/setScopes/listUnscoped/upsertNpc/deleteNpc/suggestNpcs;
startAugmentation/answerAugmentation/revertAugmentation; listPriors/priorRefs
// api/knowledge.ts
regionKnowledge(worldId, regionId, includeHearsay); diffRegions(...)
// api/play.ts
startSession(worldId, {name, startRegionId}); closeSession; listSessions; currentRegion(sid); act(sid, action); startTalk(sid, npcId); say(sid, npcId, text); talkHistory; playLog; sessionRegionKnowledge
// api/gm.ts
events.*; rumors.*; distortions.*; manualTurn(sid); timeline(sid); worldState(sid)
```

## play — 변경 (2026-09-29): 행적·판단·전파

```python
# P1 추가
class Deed(LocusModel): id; session_id; player_id; region_id; turn: int; kind: Literal["arrival","statement","declared_action"]; text: str; witnessed_npc_ids: list[str]; voided: bool = False
class DeedAppraisal(LocusModel): deed_id; npc_id; noteworthy: bool; salience: float; slant: str; retelling: str; turn: int
class PlayerAction: Move(to_region_id) | Wait() | EndTalk(npc_id) | Declare(text: str)
class SessionRumor: + origin_kind: Literal["canonical","deed"] = "canonical"; origin_deed_id: str | None; spread_from_region_id: str | None
class Narration(BaseModel): text: str; llm_calls: int
class SpreadTarget(BaseModel): region_id: str; degree: float; support: float

# P2 추가
DeedStore: record(deed) -> Deed; get(deed_id); list_by_session(session_id); list_pending_by_region(session_id, region_id) -> list[Deed]; save_appraisals(list[DeedAppraisal]); void(deed_id)
RumorStore: + list_session_origin(session_id, *, active_only=True) -> list[SessionRumor]; deactivate_by_deed(deed_id) -> int

# P16
class DeedService:
    __init__(uow_factory)
    record(session_id, *, player_id, region_id, turn, kind, text, witnessed_npc_ids) -> Deed
    pending_for(session_id, region_id) -> list[Deed]                 # 판단 없는 행적
    attach_appraisals(appraisals: list[DeedAppraisal]) -> None
    seeds_for_turn(session_id) -> list[tuple[Deed, DeedAppraisal]]    # noteworthy and not yet seeded
    void(session_id, deed_id) -> int                                  # 비활성화된 소문 수
    list(session_id) -> list[DeedView]                                # DeedView(deed, appraisals, reached_region_ids)

# P17
class GmNarrator: __init__(llm, lang); narrate(*, declaration: str, region_view: RegionView, lang: str | None = None) -> Narration

# P19 (pure)
def plan_spread(snapshot: WorldSnapshot, rumor: SessionRumor, reached: set[str], tuning: PlayTuning) -> list[SpreadTarget]
def is_session_origin(rumor: SessionRumor) -> bool

# P8 추가
RumorService.seed_from_appraisal(session, deed, appraisal, *, budget: LlmBudget) -> list[SessionRumor]
RumorService.spread(session, rumor, targets: list[SpreadTarget], *, budget: LlmBudget) -> list[SessionRumor]

# P13 추가
NpcDialogueService.appraise(session_id, npc_id, deeds: list[Deed]) -> list[DeedAppraisal]   # LLM 1회

# P6 act 분기 (요약)
Move     -> validate -> TurnAdvancer.advance(Move)  (advance 안에서 arrival 행적 기록 후 턴 루프)
Wait     -> TurnAdvancer.advance(Wait)
EndTalk  -> statement 행적 기록(대화 요약) -> NpcDialogueService.appraise(pending deeds) -> TurnAdvancer.advance(EndTalk)
Declare  -> GmNarrator.narrate -> declared_action 행적 기록 -> TurnAdvancer.advance(Declare)

# S2 PlayTuning 추가
spread_min_weight: float = 0.15; deed_seed_min_salience: float = 0.5; max_spread_per_region_turn: int = 1; declare_max_chars: int = 300
```

## api — 변경
```python
POST /api/play/sessions/{s}/act   body {type:"declare", text}  -> ActionResult (narration 포함)
GET  /api/gm/sessions/{s}/deeds                                -> list[DeedViewOut]
POST /api/gm/sessions/{s}/deeds/{d}/void                       -> {deactivated_rumors: int}
```
