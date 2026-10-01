"""play boundary domain models (Pydantic v2).

Pure data for the game-session layer (FD: domain-entities.md). Canonical
references (world / region / knowledge ids) are held as **strings only** — the
session layer never copies or snapshots canonical nodes (FR-R1.2, BR-S1-9).

Field ranges (distortion_degree / support / confidence in [0,1]) are enforced
here (BR-S1-10). Persistence mapping lives in the repository adapters.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import Field

from locus.shared.config.tuning import PlayTuning
from locus.shared.models import NPC, KnowledgeView, LocusModel, Provenance, new_id

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
    PRUNE = "prune"  # U-H1 — rumor pruned below support floor (BR-H1-5)
    # Phase 2 — event lifecycle (additive; existing values/order unchanged, BR-P1-13)
    EVENT_CREATED = "event_created"
    EVENT_APPLIED = "event_applied"  # produced by P2 advance_turn
    EVENT_RESOLVED = "event_resolved"
    # U4 player mode (additive; BR-U4-29). Payloads carry ``region_name`` (FR-D3).
    SESSION_STARTED = "session_started"
    SESSION_CLOSED = "session_closed"
    PLAYER_MOVED = "player_moved"
    PLAYER_WAITED = "player_waited"
    TURN_RUN_FAILED = "turn_run_failed"
    # U5 NPC dialogue (additive): an EndTalk action closes a conversation (FR-C4)
    NPC_TALKED = "npc_talked"
    # U6 deeds & spread (additive). Payloads carry ``region_name`` (FR-D3).
    ACTION_DECLARED = "action_declared"
    DEED_RECORDED = "deed_recorded"
    DEED_APPRAISED = "deed_appraised"
    DEED_SEEDED = "deed_seeded"
    RUMOR_SPREAD = "rumor_spread"
    DEED_VOIDED = "deed_voided"


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
    active: bool = True  # soft-flag; prune sets False, row kept for history (BR-H1-5/6)
    # U6: where the rumor came from. "canonical" = drafted from canonical knowledge or a
    # canonical chain; "deed" = a player's deed, born from an NPC's retelling and spread
    # along the connections (BR-U6-14/16). Only deed rumors spread; a void reaches them all.
    origin_kind: Literal["canonical", "deed"] = "canonical"
    origin_deed_id: str | None = None
    origin_appraisal_id: str | None = None  # which NPC's version (FD-U6 Q1 hybrid)
    spread_from_region_id: str | None = None  # None for a seed, the parent region otherwise
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

    # -- domain behavior (aggregate) ------------------------------------------
    # Status/lifecycle are stored as string values (use_enum_values=True); these
    # methods normalize back to enums so callers never compare against ``.value``
    # by hand (which silently fails if the ``.value`` is forgotten).
    def is_one_shot(self) -> bool:
        """Whether this event applies once then auto-resolves (BR-P2-4)."""
        return EventLifecycle(self.lifecycle) is EventLifecycle.ONE_SHOT

    def is_suggested(self) -> bool:
        """Whether this event is an unapproved LLM proposal (BR-P1-8)."""
        return EventStatus(self.status) is EventStatus.SUGGESTED

    def is_resolved(self) -> bool:
        """Whether this event has already been resolved (idempotency guard)."""
        return EventStatus(self.status) is EventStatus.RESOLVED

    def approve(self) -> None:
        """Transition a SUGGESTED proposal to ACTIVE (FR-P2.3, CL2.1)."""
        self.status = EventStatus.ACTIVE

    def resolve(self, turn: int) -> None:
        """Mark the event resolved at ``turn`` (FR-P3.6 / BR-P2-4)."""
        self.status = EventStatus.RESOLVED
        self.resolved_turn = turn

    def accumulate(self, deltas: dict[str, float]) -> None:
        """Add this turn's applied per-region deltas to ``contributions`` so the
        total can be symmetrically restored when the event resolves (BR-P2-3/5)."""
        merged = dict(self.contributions)
        for region_id, delta in deltas.items():
            merged[region_id] = merged.get(region_id, 0.0) + delta
        self.contributions = merged


# --------------------------------------------------------------------------- #
# UX Improvement (X3) — per-region turn-change summary (translation moved to localization)
# --------------------------------------------------------------------------- #


class RegionTurnChange(LocusModel):
    """Per-region merge of one turn's changes (X1, C6 / FR-UX2.6).

    Emitted only for regions that actually changed this turn; a region with all
    six lists empty is omitted upstream (BR-X1-21).
    """

    region_id: str
    region_name: str = ""  # U4 (FR-D3): filled by shape_region_changes from the snapshot
    promoted: list[str] = Field(default_factory=list)
    demoted: list[str] = Field(default_factory=list)
    pruned: list[str] = Field(default_factory=list)
    events_applied: list[str] = Field(default_factory=list)
    events_resolved: list[str] = Field(default_factory=list)
    rumors_added: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# U4 — player mode (FD: construction/U4-player-mode/functional-design/domain-entities.md)
# --------------------------------------------------------------------------- #
class TurnResult(LocusModel):
    """Summary of one advanced turn (was ``turn/advancer.py``; moved here so
    ``ActionResult`` can hold a list of them — re-exported from the advancer)."""

    session_id: str
    turn: int
    promoted_ids: list[str] = Field(default_factory=list)
    demoted_ids: list[str] = Field(default_factory=list)
    # Phase 2 (additive) — events applied / auto-resolved (one_shot) this turn
    applied_event_ids: list[str] = Field(default_factory=list)
    resolved_event_ids: list[str] = Field(default_factory=list)
    # U-H1 (additive) — rumors pruned + regions moved by rumor feedback this turn
    pruned_rumor_ids: list[str] = Field(default_factory=list)
    feedback_regions: list[str] = Field(default_factory=list)
    # X1 (additive) — per-region merge of this turn's changes (FR-UX2.6)
    region_changes: list[RegionTurnChange] = Field(default_factory=list)
    # U4 (additive) — LLM budget accounting (BR-U4-17/21; llm_calls = reserved calls)
    llm_calls: int = Field(default=0, ge=0)
    budget_exhausted: bool = False
    llm_failed: bool = False  # circuit breaker tripped: remaining drafts abandoned (NFR R-02)
    rumors_skipped_regions: list[str] = Field(default_factory=list)  # budget exhausted
    rumors_capped_regions: list[str] = Field(default_factory=list)  # active cap reached
    seeded_rumor_ids: list[str] = Field(default_factory=list)  # U6: deed rumors born
    spread_rumor_ids: list[str] = Field(default_factory=list)  # U6: one hop this turn


class Player(LocusModel):
    """The solo player character of a session (FR-C1, BR-U4-1/3)."""

    id: str = Field(default_factory=new_id)
    session_id: str
    name: str = Field(min_length=1, max_length=40)
    region_id: str  # current position (canonical region id, reference only)
    turns_spent: int = Field(default=0, ge=0)
    created_at: datetime | None = None  # DB server time


class PlayerCreate(LocusModel):
    """Session-start input: both fields required (US-3.1)."""

    name: str = Field(min_length=1, max_length=40)
    start_region_id: str = Field(min_length=1)


class MoveAction(LocusModel):
    type: Literal["move"] = "move"
    to_region_id: str = Field(min_length=1)


class WaitAction(LocusModel):
    type: Literal["wait"] = "wait"


class EndTalkAction(LocusModel):
    """End a conversation (1 turn). Dialogue itself is U5; U4 only spends the turn."""

    type: Literal["end_talk"] = "end_talk"
    npc_id: str = Field(min_length=1)


# Discriminated by ``type`` (FR-C3); an unknown type fails validation (422 at the API).
class DeclareAction(LocusModel):
    """Declare a free-text action (U6, FR-C9): the GM narrates, it becomes a deed, 1 turn.
    No ``min_length``: an empty or too long text is the service's 400 (BR-U6-5), a model
    constraint would be FastAPI's 422."""

    type: Literal["declare"] = "declare"
    text: str


PlayerAction = Annotated[
    Union[MoveAction, WaitAction, EndTalkAction, DeclareAction], Field(discriminator="type")
]


class Narration(LocusModel):
    """A declaration's outcome (FD-U6 Q3=A): ``text`` for the player in the display
    language, ``record`` as the English deed text. ``llm_calls`` is 0 on the fallback."""

    text: str
    record: str
    lang: str
    llm_calls: int = Field(default=1, ge=0)


class MoveOption(LocusModel):
    """One reachable neighbour of the player's region (FR-C2/C5)."""

    region_id: str
    region_name: str
    kind: str
    weight: float = Field(ge=0.0, le=1.0)
    cost_turns: int = Field(default=0, ge=0)  # 0 when not passable
    passable: bool = True
    reason: str | None = None


class TurnRunStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ActionResult(LocusModel):
    """What one action did to the world (US-3.4). ``player`` is None for a
    player-less GM session (BR-U4-30); then ``changes`` covers every region."""

    session: GameSession
    player: Player | None = None
    turns: list[TurnResult] = Field(default_factory=list)
    changes: list[RegionTurnChange] = Field(default_factory=list)  # player-scoped (Q5)
    narration: list[str] = Field(default_factory=list)  # deterministic templates (BR-U4-24)
    llm_calls: int = Field(default=0, ge=0)
    budget_exhausted: bool = False
    llm_failed: bool = False
    llm_available: bool = True
    declaration: Narration | None = None  # U6: a declare action's narration


class TurnRun(LocusModel):
    """Execution record of the turns one action (or a GM manual turn) triggered (Q4=A)."""

    id: str = Field(default_factory=new_id)
    session_id: str
    action: PlayerAction | None = None  # None = GM manual turn
    cost_turns: int = Field(default=1, ge=1)
    status: TurnRunStatus = TurnRunStatus.RUNNING
    started_turn: int = Field(default=0, ge=0)
    # What the immediate state charged before the turn loop began, so a failed run can
    # be compensated (code review U4-2 #5).
    from_region_id: str | None = None
    turns_charged: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: ActionResult | None = None  # when done
    error: str | None = None  # one fixed line when failed (NFR-6)
    lang: str | None = None  # U6: the display language a declaration is narrated in


class RegionView(LocusModel):
    """Everything the player screen shows for the current region (FR-C5, US-3.2)."""

    session_id: str
    turn: int = Field(default=0, ge=0)
    player: Player
    region_id: str
    region_name: str
    level: str
    description: str = ""
    level_path: list[str] = Field(default_factory=list)
    npcs: list[NPC] = Field(default_factory=list)
    facts: list[KnowledgeView] = Field(default_factory=list)  # direct + inherited + global
    hearsay: list[KnowledgeView] = Field(default_factory=list)
    rumors: list[SessionRumor] = Field(default_factory=list)  # active session rumors
    moves: list[MoveOption] = Field(default_factory=list)
    turn_running: bool = False
    llm_available: bool = True
    declare_max_chars: int = 300  # U6: the server's declaration limit for the input box


# --------------------------------------------------------------------------- #
# U5 — NPC dialogue (FD: construction/U5-npc-dialogue-language/functional-design)
# --------------------------------------------------------------------------- #
class Message(LocusModel):
    """One line of a conversation, stored in the display language it was written in
    (A-1: never embedded, never put through the translation cache)."""

    id: str = Field(default_factory=new_id)
    conversation_id: str
    role: Literal["player", "npc"]
    text: str = Field(min_length=1)
    lang: str = Field(min_length=2)
    turn: int = Field(default=0, ge=0)
    created_at: datetime | None = None


class Conversation(LocusModel):
    """The one conversation a session has with one NPC (BR-U5-1)."""

    id: str = Field(default_factory=new_id)
    session_id: str
    npc_id: str  # canonical NPC id (reference only)
    started_turn: int = Field(default=0, ge=0)
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime | None = None


class ScopeLimits(LocusModel):
    """How much of the region an NPC prompt may carry (FD-U5 Q3=A without hearsay)."""

    facts: int = Field(default=12, ge=0)
    rumors: int = Field(default=8, ge=0)
    recent_messages: int = Field(default=10, ge=0)

    @classmethod
    def from_tuning(cls, tuning: PlayTuning) -> ScopeLimits:
        # Built here, not as a PlayTuning method: shared must not import play (FR-A2).
        return cls(
            facts=tuning.npc_max_facts,
            rumors=tuning.npc_max_rumors,
            recent_messages=tuning.npc_max_recent_messages,
        )


class DeedMemory(LocusModel):
    """A deed as one NPC remembers it (its own retelling, or what it saw)."""

    deed_id: str
    text: str
    slant: str = ""


class NpcContext(LocusModel):
    """What one NPC may draw on for one answer (BR-U5-7). No hearsay (deviation 1)."""

    npc: NPC
    facts: list[KnowledgeView] = Field(default_factory=list)
    rumors: list[SessionRumor] = Field(default_factory=list)
    recent: list[Message] = Field(default_factory=list)
    deeds: list[DeedMemory] = Field(default_factory=list)  # U6: what it knows of the traveler
    allowed_ids: set[str] = Field(default_factory=set)


class NpcReply(LocusModel):
    """The NPC's answer to one ``say`` (exactly one LLM call, BR-U5-16)."""

    message: Message
    lang: str
    llm_calls: int = 1
    context_ids: list[str] = Field(default_factory=list)


class RegenerateResult(LocusModel):
    """Outcome of regenerating a region's rumors (U5 deviation 2).

    The two skip paths U4's review settled (``llm_incomplete``, ``no_sources``) delete
    nothing, so ``deleted_ids`` is empty there and the router purges nothing.
    """

    kept: list[SessionRumor] = Field(default_factory=list)
    fresh: list[SessionRumor] = Field(default_factory=list)
    deleted_ids: list[str] = Field(default_factory=list)
    skipped_reason: Literal["llm_incomplete", "no_sources"] | None = None

    @property
    def rumors(self) -> list[SessionRumor]:
        """What the region holds afterwards — the list the router has always returned."""
        return self.kept + self.fresh


# --- U6 deeds, appraisals and spread (domain-entities §1–§2) ----------------------- #
class DeedKind(str, Enum):
    ARRIVAL = "arrival"  # session start region + every move's arrival (deterministic text)
    STATEMENT = "statement"  # a finished talk's new player lines, summarised in English
    DECLARED_ACTION = "declared_action"  # a declaration's English record (Q3=A)


class Deed(LocusModel):
    """What the player did in a region, as the session remembers it (FR-C8). Session-only:
    it never changes the canonical world."""

    id: str = Field(default_factory=new_id)
    session_id: str
    player_id: str
    region_id: str  # where it happened = where its seeds are born
    turn: int = Field(default=0, ge=0)
    kind: DeedKind
    text: str = Field(min_length=1)  # English, except the no-LLM declaration (BR-U6-24)
    declaration: str | None = None  # DECLARED_ACTION: the player's own words (GM view)
    messages_through: datetime | None = None  # STATEMENT: last player line it summarises
    witnessed_npc_ids: list[str] = Field(default_factory=list)
    voided: bool = False
    voided_turn: int | None = None
    run_id: str | None = None  # the TurnRun that recorded it (failed-run compensation)
    created_at: datetime | None = None  # app-stamped; orders a stay


class DeedAppraisal(LocusModel):
    """One NPC's view of one deed (FR-C10): tell others or not, how eagerly, how."""

    id: str = Field(default_factory=new_id)
    session_id: str
    deed_id: str
    npc_id: str
    noteworthy: bool
    salience: float = Field(ge=0.0, le=1.0)
    slant: str = ""
    retelling: str = ""  # English; "" when not noteworthy
    turn: int = Field(default=0, ge=0)
    seeded_rumor_id: str | None = None  # at most one seed per appraisal (BR-U6-12)
    created_at: datetime | None = None


class DeedView(LocusModel):
    """A deed for the GM: its appraisals, every rumor it produced and where they reached."""

    deed: Deed
    appraisals: list[DeedAppraisal] = Field(default_factory=list)
    rumors: list[SessionRumor] = Field(default_factory=list)  # incl. inactive
    reached_region_ids: list[str] = Field(default_factory=list)


class VoidResult(LocusModel):
    deed_id: str
    deactivated_rumor_ids: list[str] = Field(default_factory=list)


class SceneBrief(LocusModel):
    """What the GM narrator may look at: this region only (BR-U6-26)."""

    player_name: str
    region_name: str
    description: str = ""
    npcs: list[NPC] = Field(default_factory=list)
    facts: list[KnowledgeView] = Field(default_factory=list)
    rumors: list[SessionRumor] = Field(default_factory=list)


class NarrationDraft(LocusModel):
    """Structured LLM output of one narration call (Q3=A)."""

    narration: str = ""
    record: str = ""


class AppraisalDraftItem(LocusModel):
    ref: str  # "d1".."dn" or "statement" — never an id
    noteworthy: bool = False
    salience: float = 0.0
    slant: str = ""
    retelling: str = ""


class AppraisalDraft(LocusModel):
    """Structured LLM output of one appraisal call: the talk's summary + the judgements."""

    summary: str | None = None
    appraisals: list[AppraisalDraftItem] = Field(default_factory=list)


class AppraisalOutcome(LocusModel):
    """What ``NpcDialogueService.appraise`` hands the deed service (no writes of its own)."""

    npc_id: str
    summary: str | None = None  # None: no statement deed (no new lines, or the call failed)
    statement_text: str | None = None  # the statement deed's text when one is recorded
    appraisals: list[DeedAppraisal] = Field(default_factory=list)  # deed ids already bound
    statement_appraisal: DeedAppraisal | None = None  # bound to the new statement deed later
    messages_through: datetime | None = None
    llm_calls: int = Field(default=0, ge=0)
    llm_failed: bool = False


class SpreadTarget(LocusModel):
    """One hop a deed rumor may take this turn (BR-U6-17/18)."""

    region_id: str
    from_region_id: str
    weight: float = Field(ge=0.0, le=1.0)  # best_path_weights(origin)[X] × edge(X,Y)
    degree: float = Field(ge=0.0, le=1.0)  # ≥ max(parent, 1 − weight)
    support: float = Field(ge=0.0, le=1.0)  # parent × (0.5 + 0.5 × edge)
