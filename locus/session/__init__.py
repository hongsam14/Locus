"""Game-session layer (Rumor Distortion cycle, Phase 1).

A dynamic, volatile play-through layer (PostgreSQL) over the static canonical
world (Neo4j/OpenSearch). The canonical layer is referenced by id only and is
never mutated by the session layer (NFR-R2). S1 provides the foundation:
models, the ``SessionRepository`` port (+ in-memory adapter) and the
``SessionService`` lifecycle. Rumor generation / promotion / turns land in S2.
"""

from __future__ import annotations

from . import dynamics, rumor_dynamics
from .distortion_service import DistortionService
from .event_service import EventService
from .event_suggester import EventDraft, EventSuggester
from .game_master import GameMasterService, SessionClosedError, TurnResult
from .memory_repo import InMemorySessionRepository
from .models import (
    CATEGORY_DEFAULT_LIFECYCLE,
    DEFAULT_DISTORTION_DEGREE,
    EventCategory,
    EventLifecycle,
    EventStatus,
    GameSession,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
    default_lifecycle,
)
from .promotion import PromotionResult
from .query import SessionQueryEngine
from .repository import SessionRepository
from .rumor_dynamics import DEFAULT_RUMOR_DYNAMICS, RumorDynamicsParams
from .rumor_feedback_service import RumorFeedbackService
from .rumor_generator import RumorDraft, RumorGenerator
from .rumor_service import RumorService
from .service import SessionService, WorldNotFoundError
from .turn import TurnAdvancer

__all__ = [
    "DEFAULT_DISTORTION_DEGREE",
    "GameSession",
    "RegionDistortion",
    "SessionRumor",
    "SessionStatus",
    "TimelineEntry",
    "TimelineKind",
    # Phase 2 — events
    "SessionEvent",
    "EventCategory",
    "EventLifecycle",
    "EventStatus",
    "CATEGORY_DEFAULT_LIFECYCLE",
    "default_lifecycle",
    "SessionRepository",
    "InMemorySessionRepository",
    "SessionService",
    "WorldNotFoundError",
    # S2 — rumor engine
    "RumorGenerator",
    "RumorDraft",
    "PromotionResult",
    "GameMasterService",
    "SessionClosedError",
    "TurnResult",
    # Phase 2 — single-responsibility session services (composed by GameMasterService)
    "RumorService",
    "EventService",
    "DistortionService",
    "TurnAdvancer",
    "SessionQueryEngine",
    # Phase 2 — dynamic engine
    "EventSuggester",
    "EventDraft",
    "dynamics",
    # U-H1 — rumor dynamics (hardening)
    "rumor_dynamics",
    "RumorDynamicsParams",
    "DEFAULT_RUMOR_DYNAMICS",
    "RumorFeedbackService",
]
