"""Session-layer domain models (Pydantic v2).

Pure data for the game-session layer (FD: domain-entities.md). Canonical
references (world / region / knowledge ids) are held as **strings only** — the
session layer never copies or snapshots canonical nodes (FR-R1.2, BR-S1-9).

Field ranges (distortion_degree / support / confidence in [0,1]) are enforced
here (BR-S1-10). Persistence mapping lives in the repository adapters.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from ..models import LocusModel, Provenance, new_id

# Default per-region distortion when a session is started (FD-S1 Q1=B / BR-S1-3).
DEFAULT_DISTORTION_DEGREE = 0.3


class SessionStatus(str, Enum):
    """Lifecycle state of a GameSession."""

    OPEN = "open"
    CLOSED = "closed"


class TimelineKind(str, Enum):
    """The kind of GameMaster action recorded in the timeline (one per entry).

    S1 defines the enum/structure; the actions themselves are produced in S2.
    """

    GENERATE = "generate"
    REGENERATE = "regenerate"
    PROMOTE = "promote"
    DEMOTE = "demote"
    ADJUST_SUPPORT = "adjust_support"
    ADVANCE_TURN = "advance_turn"
    SET_DISTORTION = "set_distortion"
    # Phase 2 — event lifecycle (additive; existing values/order unchanged, BR-P1-13)
    EVENT_CREATED = "event_created"
    EVENT_APPLIED = "event_applied"  # produced by P2 advance_turn
    EVENT_RESOLVED = "event_resolved"


class GameSession(LocusModel):
    """One play-through of a world (FR-R1.1). Many sessions per world (history)."""

    id: str = Field(default_factory=new_id)
    world_id: str
    status: SessionStatus = SessionStatus.OPEN
    turn: int = Field(default=0, ge=0)
    created_at: datetime | None = None  # set by DB server time (BR-S1-8)
    closed_at: datetime | None = None


class SessionRumor(LocusModel):
    """A session-scoped distorted statement (FR-R2). Statement/text filled in S2."""

    id: str = Field(default_factory=new_id)
    session_id: str
    region_id: str
    distorted_from_id: str  # canonical Knowledge id OR another SessionRumor id (FR-R2.2)
    distorted_from_kind: str = "knowledge"  # "knowledge" | "rumor" (BR-S1-11)
    statement: str = ""
    distortion_degree: float = Field(default=DEFAULT_DISTORTION_DEGREE, ge=0.0, le=1.0)
    support: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    promoted: bool = False  # promotion state (FR-R3.2/3.3); persisted in the session store
    provenance: Provenance


class RegionDistortion(LocusModel):
    """Per-region distortion strength held by the GameMaster (FR-R2.5).

    Exactly one row per (session_id, region_id) (BR-S1-12); seeded with
    ``DEFAULT_DISTORTION_DEGREE`` for every region at session start (BR-S1-3).
    """

    session_id: str
    region_id: str
    distortion_degree: float = Field(default=DEFAULT_DISTORTION_DEGREE, ge=0.0, le=1.0)


class TimelineEntry(LocusModel):
    """A time-ordered record of one GameMaster change within a turn (FR-R4.2)."""

    id: str = Field(default_factory=new_id)
    session_id: str
    turn: int = Field(default=0, ge=0)
    kind: TimelineKind
    summary: str = ""
    payload: dict = Field(default_factory=dict)
    created_at: datetime | None = None  # set by DB server time (BR-S1-8)


# --------------------------------------------------------------------------- #
# Phase 2 — Event + dynamic distortion (P1 Event Foundation)
# --------------------------------------------------------------------------- #
class EventCategory(str, Enum):
    """Pre-defined classification of a SessionEvent (FD-P1 Q1=A)."""

    WAR = "war"
    PLAGUE = "plague"
    POLITICS = "politics"
    DISASTER = "disaster"
    FESTIVAL = "festival"
    DISCOVERY = "discovery"


class EventLifecycle(str, Enum):
    """Whether an event applies once or persists each turn until resolved (CL1)."""

    ONE_SHOT = "one_shot"
    PERSISTENT = "persistent"


class EventStatus(str, Enum):
    """Lifecycle state of a SessionEvent (AD-P Q4=A)."""

    SUGGESTED = "suggested"  # LLM proposal awaiting approval (P2)
    ACTIVE = "active"  # in effect (manual create = active directly)
    RESOLVED = "resolved"


# category -> default lifecycle (BR-P1-3 / CL1.3). Overridable at creation.
CATEGORY_DEFAULT_LIFECYCLE: dict[EventCategory, EventLifecycle] = {
    EventCategory.WAR: EventLifecycle.PERSISTENT,
    EventCategory.PLAGUE: EventLifecycle.PERSISTENT,
    EventCategory.POLITICS: EventLifecycle.PERSISTENT,
    EventCategory.DISASTER: EventLifecycle.ONE_SHOT,
    EventCategory.FESTIVAL: EventLifecycle.ONE_SHOT,
    EventCategory.DISCOVERY: EventLifecycle.ONE_SHOT,
}


def default_lifecycle(category: EventCategory) -> EventLifecycle:
    """Default lifecycle for a category (pure; BR-P1-3). PERSISTENT if unmapped."""
    return CATEGORY_DEFAULT_LIFECYCLE.get(EventCategory(category), EventLifecycle.PERSISTENT)


class SessionEvent(LocusModel):
    """A session-scoped event affecting a region's distortion (FR-P1, Phase 2).

    Canonical ``region_id`` is referenced by string only (BR-P1-11). Distortion
    application and accumulated-delta restore live in P2; in P1 ``contributions``
    stays empty (BR-P1-12).
    """

    id: str = Field(default_factory=new_id)
    session_id: str
    region_id: str  # primary target region (canonical id, reference only)
    category: EventCategory
    description: str = ""
    magnitude: float = Field(ge=0.0, le=1.0)  # required, BR-P1-1
    lifecycle: EventLifecycle = EventLifecycle.ONE_SHOT  # set by default_lifecycle at create
    status: EventStatus = EventStatus.ACTIVE
    created_turn: int = Field(default=0, ge=0)
    resolved_turn: int | None = None
    # region_id -> accumulated applied delta (restore on resolve); filled in P2 (BR-P1-12)
    contributions: dict[str, float] = Field(default_factory=dict)
    provenance: Provenance
