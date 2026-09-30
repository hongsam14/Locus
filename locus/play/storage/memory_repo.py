"""In-memory play adapter (all play ports) — offline tests / mock (NFR-R1, C4).

Dict-based; satisfies the full port contract with the same visible behaviour as
the PostgreSQL adapter (ordering, session isolation, idempotent close). A
monotonic counter stands in for DB server time so ordering is deterministic
(BR-S1-8).

U4: thread-safe through one repository-wide ``RLock`` (BR-U4-32). ``uow()``
holds that lock for the whole unit of work and restores a deep-copied snapshot
when the block raises, so a rollback never erases another thread's writes and
no thread observes a half-applied unit (FD R-04). A unit of work never contains
an LLM call (BR-U4-14), so the hold time stays in the milliseconds.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, TypeVar

from locus.play.errors import ConversationExistsError
from locus.play.models import (
    Conversation,
    GameSession,
    Message,
    Player,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TurnRun,
    TurnRunStatus,
)
from locus.play.ports import (
    ConversationStore,
    DistortionStore,
    EventStore,
    PlayerStore,
    PlayUnitOfWork,
    RumorStore,
    SessionStore,
    TimelineStore,
    TurnRunStore,
)

F = TypeVar("F", bound=Callable[..., Any])


def _synchronized(fn: F) -> F:
    """Run a repository method under the repository lock (re-entrant)."""

    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return fn(self, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


class InMemoryPlayRepository:
    """A process-local ``PlayRepository`` for tests and offline use."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, GameSession] = {}
        self._rumors: dict[str, dict[str, SessionRumor]] = {}  # session_id -> {rumor_id: rumor}
        self._distortions: dict[tuple[str, str], float] = {}  # (session_id, region_id) -> degree
        self._timeline: dict[str, list[TimelineEntry]] = {}  # session_id -> entries
        self._events: dict[str, dict[str, SessionEvent]] = {}  # session_id -> {event_id: event}
        self._players: dict[str, Player] = {}  # session_id -> player (U4)
        self._runs: dict[str, dict[str, TurnRun]] = {}  # session_id -> {run_id: run} (U4)
        # U5: session_id -> {npc_id: conversation (no messages)}; conversation_id -> messages
        self._conversations: dict[str, dict[str, Conversation]] = {}
        self._messages: dict[str, list[Message]] = {}
        self._clock = 0

    # --- internal ---
    def _now(self) -> datetime:
        # Strictly increasing fake server time for deterministic ordering.
        self._clock += 1
        return datetime.fromtimestamp(self._clock, tz=timezone.utc)

    # Everything a unit of work must be able to roll back — conversations included (U5).
    _STATE = (
        "_sessions",
        "_rumors",
        "_distortions",
        "_timeline",
        "_events",
        "_players",
        "_runs",
        "_conversations",
        "_messages",
    )

    def _snapshot_state(self) -> dict[str, Any]:
        state = {name: deepcopy(getattr(self, name)) for name in self._STATE}
        state["_clock"] = self._clock
        return state

    def _restore_state(self, state: dict[str, Any]) -> None:
        for name in self._STATE:
            setattr(self, name, state[name])
        self._clock = state["_clock"]

    # --- lifecycle ---
    def connect(self) -> None:  # no-op
        return None

    def disconnect(self) -> None:  # no-op
        return None

    def health_check(self) -> bool:
        return True

    def ensure_schema(self) -> None:  # no-op
        return None

    # --- unit of work (U4) ---
    def uow(self) -> PlayUnitOfWork:
        return _MemoryUnitOfWork(self)

    # --- sessions ---
    @_synchronized
    def create_session(self, world_id: str) -> GameSession:
        session = GameSession(
            world_id=world_id,
            status=SessionStatus.OPEN,
            turn=0,
            created_at=self._now(),
        )
        self._sessions[session.id] = session
        self._rumors[session.id] = {}
        self._timeline[session.id] = []
        self._events[session.id] = {}
        self._runs[session.id] = {}
        return deepcopy(session)

    @_synchronized
    def get_session(self, session_id: str) -> GameSession | None:
        s = self._sessions.get(session_id)
        return deepcopy(s) if s else None

    @_synchronized
    def list_sessions(self, world_id: str) -> list[GameSession]:
        out = [deepcopy(s) for s in self._sessions.values() if s.world_id == world_id]
        out.sort(key=lambda s: s.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return out

    @_synchronized
    def close_session(self, session_id: str) -> GameSession:
        s = self._require_session(session_id)
        if s.status != SessionStatus.CLOSED.value:
            # ``use_enum_values=True`` stores the value; assigning it keeps the twin
            # byte-identical to the SQL adapter (code review U4-2, parity).
            s.status = SessionStatus.CLOSED.value  # type: ignore[assignment]
            s.closed_at = self._now()
        return deepcopy(s)

    @_synchronized
    def bump_turn(self, session_id: str) -> int:
        s = self._require_session(session_id)
        s.turn += 1
        return s.turn

    # --- rumors ---
    @_synchronized
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor:
        self._require_session(rumor.session_id)
        self._rumors[rumor.session_id][rumor.id] = deepcopy(rumor)
        return deepcopy(rumor)

    @_synchronized
    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]:
        """Batch upsert in one logical write (FR-H5). Returns the stored rumors."""
        return [self.upsert_rumor(r) for r in rumors]

    @_synchronized
    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None:
        r = self._rumors.get(session_id, {}).get(rumor_id)
        return deepcopy(r) if r else None

    @_synchronized
    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]:
        rumors = self._rumors.get(session_id, {}).values()
        out = [
            deepcopy(r)
            for r in rumors
            if (region_id is None or r.region_id == region_id) and (include_pruned or r.active)
        ]
        out.sort(key=lambda r: (r.region_id, r.id))  # same order as the SQL adapter
        return out

    @_synchronized
    def delete_rumor(self, session_id: str, rumor_id: str) -> None:
        self._rumors.get(session_id, {}).pop(rumor_id, None)

    # --- region distortion ---
    @_synchronized
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        self._require_session(session_id)
        self._distortions[(session_id, region_id)] = degree

    @_synchronized
    def get_region_distortion(self, session_id: str, region_id: str) -> float | None:
        return self._distortions.get((session_id, region_id))

    @_synchronized
    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]:
        return [
            RegionDistortion(session_id=sid, region_id=rid, distortion_degree=deg)
            for (sid, rid), deg in sorted(self._distortions.items())
            if sid == session_id
        ]

    # --- timeline ---
    @_synchronized
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry:
        self._require_session(entry.session_id)
        stored = deepcopy(entry)
        if stored.created_at is None:
            stored.created_at = self._now()  # strictly increasing, like next_timestamp()
        self._timeline[entry.session_id].append(stored)
        return deepcopy(stored)

    @_synchronized
    def list_timeline(self, session_id: str) -> list[TimelineEntry]:
        entries = self._timeline.get(session_id, [])
        ordered = sorted(
            entries,
            key=lambda e: (e.turn, e.created_at or datetime.min.replace(tzinfo=timezone.utc)),
        )
        return [deepcopy(e) for e in ordered]

    # --- events (Phase 2) ---
    @_synchronized
    def create_event(self, event: SessionEvent) -> SessionEvent:
        self._require_session(event.session_id)
        self._events.setdefault(event.session_id, {})[event.id] = deepcopy(event)
        return deepcopy(event)

    @_synchronized
    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None:
        e = self._events.get(session_id, {}).get(event_id)
        return deepcopy(e) if e else None

    @_synchronized
    def list_events(self, session_id: str, status: str | None = None) -> list[SessionEvent]:
        events = self._events.get(session_id, {}).values()
        out = [deepcopy(e) for e in events if status is None or e.status == status]
        out.sort(key=lambda e: (e.created_turn, e.id))
        return out

    @_synchronized
    def update_event(self, event: SessionEvent) -> SessionEvent:
        self._require_session(event.session_id)
        events = self._events.setdefault(event.session_id, {})
        if event.id not in events:
            # No resurrection: an event discarded during a turn's LLM window must stay
            # gone, and an event may not move between sessions (code review U4-2 #9).
            raise KeyError(f"event not found: {event.id}")
        events[event.id] = deepcopy(event)
        return deepcopy(event)

    @_synchronized
    def delete_event(self, session_id: str, event_id: str) -> None:
        self._events.get(session_id, {}).pop(event_id, None)

    # --- players (U4) ---
    @_synchronized
    def create_player(self, player: Player) -> Player:
        self._require_session(player.session_id)
        if player.session_id in self._players:
            raise ValueError(f"session already has a player: {player.session_id}")
        stored = deepcopy(player)
        if stored.created_at is None:
            stored.created_at = self._now()
        self._players[player.session_id] = stored
        return deepcopy(stored)

    @_synchronized
    def get_player(self, session_id: str) -> Player | None:
        p = self._players.get(session_id)
        return deepcopy(p) if p else None

    @_synchronized
    def update_player(self, player: Player) -> Player:
        current = self._players.get(player.session_id)
        if current is None or current.id != player.id:
            raise KeyError(f"player not found: {player.id}")
        stored = deepcopy(player)
        stored.created_at = current.created_at
        self._players[player.session_id] = stored
        return deepcopy(stored)

    # --- turn runs (U4) ---
    @_synchronized
    def create_run(self, run: TurnRun) -> TurnRun:
        self._require_session(run.session_id)
        stored = deepcopy(run)
        if stored.started_at is None:
            stored.started_at = self._now()
        self._runs.setdefault(run.session_id, {})[run.id] = stored
        return deepcopy(stored)

    @_synchronized
    def get_run(self, session_id: str, run_id: str) -> TurnRun | None:
        r = self._runs.get(session_id, {}).get(run_id)
        return deepcopy(r) if r else None

    @_synchronized
    def update_run(self, run: TurnRun) -> TurnRun:
        runs = self._runs.get(run.session_id, {})
        if run.id not in runs:
            raise KeyError(f"turn run not found: {run.id}")
        stored = deepcopy(run)
        stored.started_at = runs[run.id].started_at
        runs[run.id] = stored
        return deepcopy(stored)

    @_synchronized
    def list_runs(self, session_id: str, status: str | None = None) -> list[TurnRun]:
        runs = self._runs.get(session_id, {}).values()
        out = [deepcopy(r) for r in runs if status is None or r.status == status]
        out.sort(key=lambda r: (r.started_at or datetime.min.replace(tzinfo=timezone.utc), r.id))
        return out

    @_synchronized
    def fail_stale_runs(self, *, reason: str) -> int:
        count = 0
        now = self._now()
        for runs in self._runs.values():
            for r in runs.values():
                if r.status == TurnRunStatus.RUNNING.value:
                    r.status = TurnRunStatus.FAILED.value  # type: ignore[assignment]
                    r.error = reason
                    r.finished_at = now
                    count += 1
        return count

    # --- conversations (U5) ---
    @_synchronized
    def create_conversation(self, conversation: Conversation) -> Conversation:
        self._require_session(conversation.session_id)
        by_npc = self._conversations.setdefault(conversation.session_id, {})
        if conversation.npc_id in by_npc:
            raise ConversationExistsError(
                f"conversation exists: {conversation.session_id}/{conversation.npc_id}"
            )
        stored = conversation.model_copy(deep=True, update={"messages": []})
        if stored.created_at is None:
            stored.created_at = self._now()
        by_npc[conversation.npc_id] = stored
        self._messages.setdefault(stored.id, [])
        return deepcopy(stored)

    @_synchronized
    def get_conversation(self, session_id: str, npc_id: str) -> Conversation | None:
        conv = self._conversations.get(session_id, {}).get(npc_id)
        if conv is None:
            return None
        out = deepcopy(conv)
        out.messages = self._ordered_messages(conv.id)
        return out

    @_synchronized
    def append_message(self, message: Message) -> Message:
        if message.conversation_id not in self._messages:
            raise KeyError(f"conversation not found: {message.conversation_id}")
        stored = deepcopy(message)
        if stored.created_at is None:
            stored.created_at = self._now()
        self._messages[message.conversation_id].append(stored)
        return deepcopy(stored)

    @_synchronized
    def list_conversations(self, session_id: str) -> list[Conversation]:
        out = [deepcopy(c) for c in self._conversations.get(session_id, {}).values()]
        out.sort(key=lambda c: (c.created_at or datetime.min.replace(tzinfo=timezone.utc), c.id))
        return out

    def _ordered_messages(self, conversation_id: str) -> list[Message]:
        msgs = [deepcopy(m) for m in self._messages.get(conversation_id, [])]
        msgs.sort(key=lambda m: (m.created_at or datetime.min.replace(tzinfo=timezone.utc), m.id))
        return msgs

    # --- internal ---
    def _require_session(self, session_id: str) -> GameSession:
        s = self._sessions.get(session_id)
        if s is None:
            raise KeyError(f"session not found: {session_id}")
        return s


class _MemoryUnitOfWork:
    """Lock-holding unit of work over the in-memory repository (rollback = restore)."""

    def __init__(self, repo: InMemoryPlayRepository) -> None:
        self._repo = repo
        self._saved: dict[str, Any] | None = None
        self._open = False

    # Every store is the repository itself (the lock is re-entrant), but only while the
    # block is open: writing through a unit of work that was never entered took no lock,
    # no snapshot and could not be rolled back, while the PostgreSQL adapter raises for
    # the same misuse — the twin was hiding that bug offline (code review U4 #6).
    @property
    def _s(self) -> InMemoryPlayRepository:
        if not self._open:
            raise RuntimeError("unit of work is not open")
        return self._repo

    @property
    def sessions(self) -> SessionStore:
        return self._s

    @property
    def rumors(self) -> RumorStore:
        return self._s

    @property
    def distortions(self) -> DistortionStore:
        return self._s

    @property
    def timeline(self) -> TimelineStore:
        return self._s

    @property
    def events(self) -> EventStore:
        return self._s

    @property
    def players(self) -> PlayerStore:
        return self._s

    @property
    def runs(self) -> TurnRunStore:
        return self._s

    @property
    def conversations(self) -> ConversationStore:
        return self._s

    def __enter__(self) -> PlayUnitOfWork:
        self._repo._lock.acquire()
        self._saved = self._repo._snapshot_state()
        self._open = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if exc_type is not None and self._saved is not None:
                self._repo._restore_state(self._saved)
        finally:
            self._open = False
            self._saved = None
            self._repo._lock.release()
