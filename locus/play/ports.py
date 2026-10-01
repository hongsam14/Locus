"""play boundary persistence ports (AD-R3): one Protocol per concern.

The old monolithic ``PlayRepository`` is split by concern so services only
depend on what they use. A single adapter (``PostgresPlayRepository`` or the
in-memory twin) implements all of them and shares one engine / transaction
scope. ``PlayUnitOfWork`` is defined here and implemented in U4 (single
transaction for a whole turn).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from locus.play.models import (
    Conversation,
    Deed,
    DeedAppraisal,
    GameSession,
    Message,
    Player,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    TimelineEntry,
    TurnRun,
)


@runtime_checkable
class PlayStorage(Protocol):
    """Adapter lifecycle (connection + idempotent DDL)."""

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...
    def ensure_schema(self) -> None: ...  # idempotent DDL (BR-S1-17)


@runtime_checkable
class SessionStore(Protocol):
    def create_session(self, world_id: str) -> GameSession: ...  # turn=0, status=OPEN
    def get_session(self, session_id: str) -> GameSession | None: ...
    def list_sessions(self, world_id: str) -> list[GameSession]: ...
    def close_session(self, session_id: str) -> GameSession: ...  # idempotent (BR-S1-4)
    def bump_turn(self, session_id: str) -> int: ...  # turn += 1, returns new turn


@runtime_checkable
class RumorStore(Protocol):
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor: ...
    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]: ...  # one tx
    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None: ...
    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]: ...  # active-only by default (BR-H1-6)
    def delete_rumor(self, session_id: str, rumor_id: str) -> None: ...
    def list_rumors_by_origin(
        self, session_id: str, *, deed_id: str | None = None, include_inactive: bool = False
    ) -> list[SessionRumor]: ...  # U6: origin_kind == "deed" only, narrowed by deed


@runtime_checkable
class DistortionStore(Protocol):
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None: ...
    def get_region_distortion(self, session_id: str, region_id: str) -> float | None: ...
    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]: ...


@runtime_checkable
class TimelineStore(Protocol):
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry: ...
    def list_timeline(self, session_id: str) -> list[TimelineEntry]: ...  # turn, then created_at


@runtime_checkable
class EventStore(Protocol):
    def create_event(self, event: SessionEvent) -> SessionEvent: ...
    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None: ...
    def list_events(
        self, session_id: str, status: str | None = None
    ) -> list[SessionEvent]: ...  # created_turn, then id
    def update_event(self, event: SessionEvent) -> SessionEvent: ...
    def delete_event(self, session_id: str, event_id: str) -> None: ...


@runtime_checkable
class PlayerStore(Protocol):
    """U4 — the solo player of a session (at most one per session, BR-U4-1)."""

    def create_player(self, player: Player) -> Player: ...  # ValueError if one exists
    def get_player(self, session_id: str) -> Player | None: ...
    def update_player(self, player: Player) -> Player: ...


@runtime_checkable
class TurnRunStore(Protocol):
    """U4 — execution records of action-triggered turn runs (Q4=A)."""

    def create_run(self, run: TurnRun) -> TurnRun: ...
    def get_run(self, session_id: str, run_id: str) -> TurnRun | None: ...  # None if other session
    def update_run(self, run: TurnRun) -> TurnRun: ...
    def list_runs(self, session_id: str, status: str | None = None) -> list[TurnRun]: ...
    def fail_stale_runs(self, *, reason: str) -> int: ...  # running -> failed (API startup)


@runtime_checkable
class ConversationStore(Protocol):
    """U5 — NPC conversations: one per (session, NPC), messages in order (BR-U5-1/31)."""

    def create_conversation(
        self, conversation: Conversation
    ) -> Conversation: ...  # ConversationExistsError if the (session, npc) pair exists
    def get_conversation(
        self, session_id: str, npc_id: str
    ) -> Conversation | None: ...  # messages filled, ordered by (created_at, id)
    def append_message(self, message: Message) -> Message: ...  # KeyError: no conversation
    def list_conversations(self, session_id: str) -> list[Conversation]: ...  # no messages


@runtime_checkable
class DeedStore(Protocol):
    """U6 — deeds and the NPC appraisals of them (domain-entities §4.1)."""

    def record_deed(self, deed: Deed) -> Deed: ...  # created_at = next_timestamp()
    def get_deed(self, session_id: str, deed_id: str) -> Deed | None: ...
    def list_deeds(
        self, session_id: str, *, region_id: str | None = None, include_voided: bool = True
    ) -> list[Deed]: ...  # ordered by (created_at, id)
    def update_deed(self, deed: Deed) -> Deed: ...  # KeyError when missing
    def save_appraisals(
        self, appraisals: list[DeedAppraisal]
    ) -> list[DeedAppraisal]: ...  # AppraisalExistsError on a (deed_id, npc_id) repeat
    def list_appraisals(
        self, session_id: str, *, deed_ids: list[str] | None = None, npc_id: str | None = None
    ) -> list[DeedAppraisal]: ...  # ordered by (created_at, id)
    def mark_seeded(self, session_id: str, appraisal_id: str, rumor_id: str) -> None: ...
    def delete_by_run(self, session_id: str, run_id: str) -> int: ...  # deeds + appraisals


@runtime_checkable
class PlayUnitOfWork(Protocol):
    """One transaction spanning every store (U4, BR-U4-14). Enter opens it; a clean
    exit commits, an exception rolls back. Services inside a UoW write only through
    these attributes, never through the repository (PostgreSQL: one connection)."""

    # Read-only members so an adapter may expose them as attributes or as properties
    # (the in-memory twin gates them on "is the block open?", code review U4 #6).
    @property
    def sessions(self) -> SessionStore: ...
    @property
    def rumors(self) -> RumorStore: ...
    @property
    def distortions(self) -> DistortionStore: ...
    @property
    def timeline(self) -> TimelineStore: ...
    @property
    def events(self) -> EventStore: ...
    @property
    def players(self) -> PlayerStore: ...
    @property
    def runs(self) -> TurnRunStore: ...
    @property
    def conversations(self) -> ConversationStore: ...
    @property
    def deeds(self) -> DeedStore: ...

    def __enter__(self) -> PlayUnitOfWork: ...
    def __exit__(self, exc_type, exc, tb) -> None: ...


@runtime_checkable
class PlayRepository(
    PlayStorage,
    SessionStore,
    RumorStore,
    DistortionStore,
    TimelineStore,
    EventStore,
    PlayerStore,
    TurnRunStore,
    ConversationStore,
    DeedStore,
    Protocol,
):
    """Everything a play adapter provides (the union of the concern ports).

    Services should type their dependencies with the narrowest port they use;
    adapters and composition roots use this union.
    """

    def uow(self) -> PlayUnitOfWork: ...  # one transaction over every store (U4)


@runtime_checkable
class SessionRumorStore(SessionStore, RumorStore, Protocol):
    """Sessions + rumors — what the region knowledge view reads."""
