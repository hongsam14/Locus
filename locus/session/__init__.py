"""Game-session layer (Rumor Distortion cycle, Phase 1).

A dynamic, volatile play-through layer (PostgreSQL) over the static canonical
world (Neo4j/OpenSearch). The canonical layer is referenced by id only and is
never mutated by the session layer (NFR-R2). S1 provides the foundation:
models, the ``SessionRepository`` port (+ in-memory adapter) and the
``SessionService`` lifecycle. Rumor generation / promotion / turns land in S2.
"""

from __future__ import annotations

from .game_master import GameMasterService, SessionClosedError, TurnResult
from .memory_repo import InMemorySessionRepository
from .models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    RegionDistortion,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from .promotion import PromotionResult
from .query import SessionQueryEngine
from .repository import SessionRepository
from .rumor_generator import RumorDraft, RumorGenerator
from .service import SessionService, WorldNotFoundError

__all__ = [
    "DEFAULT_DISTORTION_DEGREE",
    "GameSession",
    "RegionDistortion",
    "SessionRumor",
    "SessionStatus",
    "TimelineEntry",
    "TimelineKind",
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
    "SessionQueryEngine",
]
