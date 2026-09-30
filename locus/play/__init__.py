"""play — sessions, rumors, events, turns (and, from U4 on, players and NPC dialogue).

A dynamic, volatile play-through layer (PostgreSQL) over the static canonical
world. The canonical world is read through ``knowledge`` (ids only, never
mutated, NFR-R2). Services are single-responsibility and composed by
``assemble_play``; there is no facade (AD-R4). Time advances only through
``TurnAdvancer.advance`` (AD-R5).
"""

from __future__ import annotations

from locus.play.base import SessionClosedError
from locus.play.distortion_service import DistortionService
from locus.play.event import dynamics
from locus.play.event.service import EventService
from locus.play.event.suggester import EventDraft, EventSuggester
from locus.play.models import (
    CATEGORY_DEFAULT_LIFECYCLE,
    DEFAULT_DISTORTION_DEGREE,
    EventCategory,
    EventLifecycle,
    EventStatus,
    GameSession,
    RegionDistortion,
    RegionTurnChange,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
    default_lifecycle,
)
from locus.play.npc.dialogue import NpcDialogueService
from locus.play.npc.scope import build_context
from locus.play.ports import (
    DistortionStore,
    EventStore,
    PlayRepository,
    PlayStorage,
    PlayUnitOfWork,
    RumorStore,
    SessionRumorStore,
    SessionStore,
    TimelineStore,
)
from locus.play.region_knowledge import RegionSources, SessionKnowledgeService, is_rumor_view
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor import promotion
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS
from locus.play.rumor.feedback import RumorFeedbackService
from locus.play.rumor.generator import RumorDraft, RumorGenerator
from locus.play.rumor.promotion import PromotionResult
from locus.play.rumor.service import RumorService
from locus.play.session_service import SessionService, WorldNotFoundError
from locus.play.storage.memory_repo import InMemoryPlayRepository
from locus.play.storage.postgres_repo import PostgresPlayRepository
from locus.play.turn.advancer import TurnAdvancer, TurnResult
from locus.play.wiring import PlayContainer, assemble_play
from locus.shared.config.tuning import PlayTuning

__all__ = [
    # models
    "DEFAULT_DISTORTION_DEGREE",
    "GameSession",
    "RegionDistortion",
    "SessionRumor",
    "SessionStatus",
    "TimelineEntry",
    "TimelineKind",
    "SessionEvent",
    "EventCategory",
    "EventLifecycle",
    "EventStatus",
    "CATEGORY_DEFAULT_LIFECYCLE",
    "default_lifecycle",
    "RegionTurnChange",
    "NpcDialogueService",
    "build_context",
    "RegionSources",
    # ports + adapters
    "PlayStorage",
    "SessionStore",
    "RumorStore",
    "DistortionStore",
    "TimelineStore",
    "EventStore",
    "SessionRumorStore",
    "PlayUnitOfWork",
    "PlayRepository",
    "InMemoryPlayRepository",
    "PostgresPlayRepository",
    # services
    "SessionService",
    "WorldNotFoundError",
    "SessionClosedError",
    "RumorGenerator",
    "RumorDraft",
    "PromotionResult",
    "RumorService",
    "EventService",
    "EventSuggester",
    "EventDraft",
    "DistortionService",
    "RumorFeedbackService",
    "TurnAdvancer",
    "TurnResult",
    "SessionKnowledgeService",
    "is_rumor_view",
    # pure modules + tuning
    "dynamics",
    "rumor_dynamics",
    "promotion",
    "PlayTuning",
    "DEFAULT_RUMOR_DYNAMICS",
    # composition
    "PlayContainer",
    "assemble_play",
]
