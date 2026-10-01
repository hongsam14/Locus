"""play boundary composition (AD-R2/R4): ``assemble_play(shared, knowledge) -> PlayContainer``.

No facade: routers receive the single-responsibility services directly from
the container. The play adapter is one object implementing every play port.
"""

from __future__ import annotations

from dataclasses import dataclass

from locus.knowledge.wiring import KnowledgeContainer
from locus.play.deeds.service import DeedService
from locus.play.distortion_service import DistortionService
from locus.play.event.seeds import SeedService
from locus.play.event.service import EventService
from locus.play.event.suggester import EventSuggester
from locus.play.gm.narrator import GmNarrator
from locus.play.npc.dialogue import NpcDialogueService
from locus.play.player.service import PlayService
from locus.play.ports import PlayRepository
from locus.play.region_knowledge import SessionKnowledgeService
from locus.play.rumor.feedback import RumorFeedbackService
from locus.play.rumor.generator import RumorGenerator
from locus.play.rumor.service import RumorService
from locus.play.session_service import SessionService
from locus.play.storage.postgres_repo import PostgresPlayRepository
from locus.play.turn.advancer import TurnAdvancer
from locus.play.turn.executor import ThreadTurnExecutor, TurnExecutor
from locus.play.turn.guard import TurnGuard
from locus.play.world_state import WorldStateService
from locus.shared.config.tuning import PlayTuning
from locus.shared.llm.base import LLMProvider
from locus.shared.wiring import SharedContainer


@dataclass
class PlayContainer:
    repo: PlayRepository
    sessions: SessionService
    distortions: DistortionService
    region_knowledge: SessionKnowledgeService
    # U4 — always present: the turn engine runs without an LLM (rumor drafts skipped, Q6)
    feedback: RumorFeedbackService
    turns: TurnAdvancer
    play: PlayService
    guard: TurnGuard
    executor: TurnExecutor
    # Always assembled: their deterministic methods (reads, event lifecycle) work
    # without a provider and only the LLM-needing ones raise 503 (code review U4-2 #13).
    rumors: RumorService
    events: EventService
    seeds: SeedService  # U8: world event seeds started by the GM (BR-U8-15)
    # U5 — always assembled; without a provider only `say` answers 503 (BR-U5-29)
    dialogue: NpcDialogueService
    # U6 — deeds, appraisals and the GM's view; no LLM needed
    deeds: DeedService
    # U7 — the GM map overlay (FR-D4); no LLM needed
    world_state: WorldStateService


def assemble_play(
    shared: SharedContainer,
    knowledge: KnowledgeContainer,
    *,
    repo: PlayRepository | None = None,
    generator: RumorGenerator | None = None,
    suggester: EventSuggester | None = None,
    tuning: PlayTuning | None = None,
    executor: TurnExecutor | None = None,
    dialogue_llm: LLMProvider | None = None,
) -> PlayContainer:
    """Build the play services. Pass ``repo`` (e.g. in-memory) to bypass PostgreSQL;
    ``generator``/``suggester``/``tuning`` override the LLM-backed defaults (tests
    compose through this same root, review U1 #15); ``executor`` replaces the
    daemon-thread turn executor (tests pass ``SyncTurnExecutor``)."""
    store: PlayRepository
    if repo is None:
        if shared.sql_engine is None:
            raise RuntimeError("play boundary needs a SQL engine (SESSION_DB_URL) or a repo")
        pg = PostgresPlayRepository(engine=shared.sql_engine)
        pg.ensure_schema()
        store = pg
    else:
        store = repo
    tuning = tuning or shared.settings.play_tuning()
    if knowledge.cache is None:
        raise RuntimeError("play boundary needs a snapshot source (knowledge.cache)")
    loader = knowledge.cache  # SnapshotSource: play reads the cached snapshot (NFR-3)
    guard = TurnGuard()
    executor = executor if executor is not None else ThreadTurnExecutor()
    # Session lifecycle, distortion, the region view and the turn engine need no
    # LLM (NFR-4 / US-1.4); without a provider only rumor generation and event
    # suggestion stay None and answer 503.
    if generator is None and shared.llm is not None:
        generator = RumorGenerator(shared.llm)
    if suggester is None and shared.llm is not None:
        suggester = EventSuggester(shared.llm)
    rumors = RumorService(
        store, generator, loader, knowledge.params, birth_support=tuning.birth_support
    )
    feedback = RumorFeedbackService(store, tuning)
    deeds = DeedService(store, loader, tuning=tuning)  # U6: records deeds and appraisals
    region_knowledge = SessionKnowledgeService(store, loader, knowledge.params)
    # One LLM speaks for the NPCs and the GM: dialogue, deed appraisal and narration
    # (U6 code-plan review R-02 — `dialogue_llm` is the single injection point).
    voice_llm = dialogue_llm if dialogue_llm is not None else shared.llm
    dialogue = NpcDialogueService(
        store,
        loader,
        region_knowledge,
        voice_llm,
        tuning,
        default_lang=shared.settings.translation_target_lang,
        supported_langs=shared.settings.supported_langs,
        deeds=deeds,
    )
    turns = TurnAdvancer(
        store,
        loader,
        rumors,
        feedback,
        tuning,
        guard=guard,
        executor=executor,
        deeds=deeds,
        dialogue=dialogue,
        narrator=GmNarrator(voice_llm) if voice_llm is not None else None,
        region_knowledge=region_knowledge,
        default_lang=shared.settings.translation_target_lang,
    )
    events = EventService(store, loader, suggester=suggester, deeds=deeds, tuning=tuning)
    container = PlayContainer(
        repo=store,
        sessions=SessionService(store, loader, guard, deeds=deeds),
        distortions=DistortionService(store, loader),
        world_state=WorldStateService(store, loader, max_suggestions=tuning.max_event_suggestions),
        region_knowledge=region_knowledge,
        feedback=feedback,
        turns=turns,
        play=PlayService(
            store,
            loader,
            region_knowledge,
            guard=guard,
            turns=turns,
            tuning=tuning,
        ),
        guard=guard,
        executor=executor,
        rumors=rumors,
        events=events,
        seeds=SeedService(store, loader, events),
        dialogue=dialogue,
        deeds=deeds,
    )
    return container
