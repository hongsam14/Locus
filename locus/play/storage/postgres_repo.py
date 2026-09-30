"""PostgreSQL adapter for the play ports (SQLAlchemy 2.0, sync; was PostgresPlayRepository).

Hybrid schema (FD-S1 Q3=A): core fields are regular indexed columns; the
variable/nested parts (``provenance``, timeline ``payload``, turn-run
``action``/``result``) are JSON columns (JSONB on PostgreSQL, generic JSON
elsewhere so the same adapter runs against SQLite in offline tests). Ids are
application-generated (``new_id``); ``created_at`` is set by the DB server
(``func.now()``, FD-S1 Q4=A).

U4 (BR-U4-32): every SQL statement lives in ``_PgStores``, which works over one
``Connection``. The repository's public methods each open ``engine.begin()``
around one call (autocommit per call, as before); ``uow()`` opens one
transaction and hands out the same stores bound to that connection, so a whole
turn commits or rolls back together (BR-U4-14).

``ensure_schema`` is idempotent ``CREATE TABLE IF NOT EXISTS`` (BR-S1-17).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, TypeVar

from sqlalchemy import (
    delete,
    select,
    text,
    update,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

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
    TimelineKind,
    TurnRun,
    TurnRunStatus,
)
from locus.play.ports import PlayUnitOfWork
from locus.play.storage.clock import next_timestamp
from locus.play.storage.schema import (
    CONVERSATION_UNIQUE,
    conversations,
    ensure_play_schema,
    game_sessions,
    messages,
    players,
    region_distortions,
    session_events,
    session_rumors,
    timeline_entries,
    turn_runs,
)
from locus.shared.models import Provenance
from locus.shared.storage.sql import make_engine, upsert_stmt

T = TypeVar("T")


class _PgStores:
    """All play stores over one connection (the unit-of-work view)."""

    def __init__(self, conn: Connection) -> None:
        self._conn = conn
        self._engine = conn.engine

    # every store attribute is this object (one connection, one transaction)
    @property
    def sessions(self) -> _PgStores:
        return self

    @property
    def rumors(self) -> _PgStores:
        return self

    @property
    def distortions(self) -> _PgStores:
        return self

    @property
    def timeline(self) -> _PgStores:
        return self

    @property
    def events(self) -> _PgStores:
        return self

    @property
    def players(self) -> _PgStores:
        return self

    @property
    def runs(self) -> _PgStores:
        return self

    @property
    def conversations(self) -> _PgStores:
        return self

    # -- sessions --------------------------------------------------------- #
    def create_session(self, world_id: str) -> GameSession:
        session = GameSession(world_id=world_id, status=SessionStatus.OPEN, turn=0)
        self._conn.execute(
            game_sessions.insert().values(
                id=session.id,
                world_id=world_id,
                status=SessionStatus.OPEN.value,
                turn=0,
                closed_at=None,
            )
        )
        row = (
            self._conn.execute(select(game_sessions).where(game_sessions.c.id == session.id))
            .mappings()
            .one()
        )
        return _row_to_session(row)

    def get_session(self, session_id: str) -> GameSession | None:
        row = (
            self._conn.execute(select(game_sessions).where(game_sessions.c.id == session_id))
            .mappings()
            .one_or_none()
        )
        return _row_to_session(row) if row else None

    def list_sessions(self, world_id: str) -> list[GameSession]:
        rows = (
            self._conn.execute(
                select(game_sessions)
                .where(game_sessions.c.world_id == world_id)
                .order_by(game_sessions.c.created_at)
            )
            .mappings()
            .all()
        )
        return [_row_to_session(r) for r in rows]

    def close_session(self, session_id: str) -> GameSession:
        current = self._conn.execute(
            select(game_sessions.c.status).where(game_sessions.c.id == session_id)
        ).scalar_one_or_none()
        if current is None:
            raise KeyError(f"session not found: {session_id}")
        if current != SessionStatus.CLOSED.value:
            self._conn.execute(
                update(game_sessions)
                .where(game_sessions.c.id == session_id)
                .values(status=SessionStatus.CLOSED.value, closed_at=text("CURRENT_TIMESTAMP"))
            )
        row = (
            self._conn.execute(select(game_sessions).where(game_sessions.c.id == session_id))
            .mappings()
            .one()
        )
        return _row_to_session(row)

    def bump_turn(self, session_id: str) -> int:
        res = self._conn.execute(
            update(game_sessions)
            .where(game_sessions.c.id == session_id)
            .values(turn=game_sessions.c.turn + 1)
        )
        if res.rowcount == 0:
            raise KeyError(f"session not found: {session_id}")
        return self._conn.execute(
            select(game_sessions.c.turn).where(game_sessions.c.id == session_id)
        ).scalar_one()

    # -- rumors ----------------------------------------------------------- #
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor:
        self._upsert_rumor(rumor)
        return rumor.model_copy(deep=True)

    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]:
        """Batch upsert in a single transaction (FR-H5 / BR-H1-13)."""
        for rumor in rumors:
            self._upsert_rumor(rumor)
        return [r.model_copy(deep=True) for r in rumors]

    def _upsert_rumor(self, rumor: SessionRumor) -> None:
        # INSERT ... ON CONFLICT (id) DO UPDATE: no select-then-write race (P3).
        self._conn.execute(
            upsert_stmt(
                self._engine, session_rumors, _rumor_to_values(rumor), index_elements=["id"]
            )
        )

    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None:
        row = (
            self._conn.execute(
                select(session_rumors).where(
                    session_rumors.c.session_id == session_id,
                    session_rumors.c.id == rumor_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        return _row_to_rumor(row) if row else None

    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]:
        stmt = select(session_rumors).where(session_rumors.c.session_id == session_id)
        if region_id is not None:
            stmt = stmt.where(session_rumors.c.region_id == region_id)
        if not include_pruned:  # active-only by default (BR-H1-6)
            stmt = stmt.where(session_rumors.c.active.is_(True))
        # Explicit order: without it the player screen's rumor order and the
        # notification order were PostgreSQL plan-dependent (code review U4-2).
        stmt = stmt.order_by(session_rumors.c.region_id, session_rumors.c.id)
        rows = self._conn.execute(stmt).mappings().all()
        return [_row_to_rumor(r) for r in rows]

    def delete_rumor(self, session_id: str, rumor_id: str) -> None:
        self._conn.execute(
            delete(session_rumors).where(
                session_rumors.c.session_id == session_id,
                session_rumors.c.id == rumor_id,
            )
        )

    # -- region distortion ------------------------------------------------ #
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        self._conn.execute(
            upsert_stmt(
                self._engine,
                region_distortions,
                {"session_id": session_id, "region_id": region_id, "distortion_degree": degree},
                index_elements=["session_id", "region_id"],
            )
        )

    def get_region_distortion(self, session_id: str, region_id: str) -> float | None:
        return self._conn.execute(
            select(region_distortions.c.distortion_degree).where(
                region_distortions.c.session_id == session_id,
                region_distortions.c.region_id == region_id,
            )
        ).scalar_one_or_none()

    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]:
        rows = (
            self._conn.execute(
                select(region_distortions)
                .where(region_distortions.c.session_id == session_id)
                .order_by(region_distortions.c.region_id)
            )
            .mappings()
            .all()
        )
        return [
            RegionDistortion(
                session_id=r["session_id"],
                region_id=r["region_id"],
                distortion_degree=r["distortion_degree"],
            )
            for r in rows
        ]

    # -- timeline --------------------------------------------------------- #
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry:
        # A whole turn's entries are written inside ONE transaction, and PostgreSQL's
        # CURRENT_TIMESTAMP default is the transaction start time — identical for every
        # row, which left `ORDER BY turn, created_at` tied and the turn's entries in
        # arbitrary order (code review U4 #1). Stamp them in the application with a
        # strictly increasing clock instead (deviation from BR-S1-8 for this table only).
        self._conn.execute(
            timeline_entries.insert().values(
                id=entry.id,
                session_id=entry.session_id,
                turn=entry.turn,
                kind=_kind_value(entry.kind),
                summary=entry.summary,
                payload=entry.payload,
                created_at=entry.created_at or next_timestamp(),
            )
        )
        row = (
            self._conn.execute(select(timeline_entries).where(timeline_entries.c.id == entry.id))
            .mappings()
            .one()
        )
        return _row_to_timeline(row)

    def list_timeline(self, session_id: str) -> list[TimelineEntry]:
        rows = (
            self._conn.execute(
                select(timeline_entries).where(timeline_entries.c.session_id == session_id)
                # `id` breaks a residual tie (e.g. rows written by another process)
                .order_by(
                    timeline_entries.c.turn, timeline_entries.c.created_at, timeline_entries.c.id
                )
            )
            .mappings()
            .all()
        )
        return [_row_to_timeline(r) for r in rows]

    # -- events (Phase 2) ------------------------------------------------- #
    def create_event(self, event: SessionEvent) -> SessionEvent:
        self._conn.execute(session_events.insert().values(**_event_to_values(event)))
        return event.model_copy(deep=True)

    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None:
        row = (
            self._conn.execute(
                select(session_events).where(
                    session_events.c.session_id == session_id,
                    session_events.c.id == event_id,
                )
            )
            .mappings()
            .one_or_none()
        )
        return _row_to_event(row) if row else None

    def list_events(self, session_id: str, status: str | None = None) -> list[SessionEvent]:
        stmt = select(session_events).where(session_events.c.session_id == session_id)
        if status is not None:
            stmt = stmt.where(session_events.c.status == status)
        stmt = stmt.order_by(session_events.c.created_turn, session_events.c.id)
        rows = self._conn.execute(stmt).mappings().all()
        return [_row_to_event(r) for r in rows]

    def update_event(self, event: SessionEvent) -> SessionEvent:
        # Session-scoped, update-only. Matching on `id` alone and inserting when the row
        # was gone resurrected a discarded event and could move one between sessions,
        # losing the original's accumulated contributions (code review U4-2 #9).
        values = {k: v for k, v in _event_to_values(event).items() if k != "id"}
        res = self._conn.execute(
            update(session_events)
            .where(
                session_events.c.id == event.id,
                session_events.c.session_id == event.session_id,
            )
            .values(**values)
        )
        if res.rowcount == 0:
            raise KeyError(f"event not found: {event.id}")
        return event.model_copy(deep=True)

    def delete_event(self, session_id: str, event_id: str) -> None:
        self._conn.execute(
            delete(session_events).where(
                session_events.c.session_id == session_id,
                session_events.c.id == event_id,
            )
        )

    # -- players (U4) ----------------------------------------------------- #
    def create_player(self, player: Player) -> Player:
        exists = self._conn.execute(
            select(players.c.id).where(players.c.session_id == player.session_id)
        ).scalar_one_or_none()
        if exists is not None:
            raise ValueError(f"session already has a player: {player.session_id}")
        self._conn.execute(
            players.insert().values(
                id=player.id,
                session_id=player.session_id,
                name=player.name,
                region_id=player.region_id,
                turns_spent=player.turns_spent,
            )
        )
        row = self._conn.execute(select(players).where(players.c.id == player.id)).mappings().one()
        return _row_to_player(row)

    def get_player(self, session_id: str) -> Player | None:
        row = (
            self._conn.execute(select(players).where(players.c.session_id == session_id))
            .mappings()
            .one_or_none()
        )
        return _row_to_player(row) if row else None

    def update_player(self, player: Player) -> Player:
        res = self._conn.execute(
            update(players)
            .where(players.c.id == player.id, players.c.session_id == player.session_id)
            .values(name=player.name, region_id=player.region_id, turns_spent=player.turns_spent)
        )
        if res.rowcount == 0:
            raise KeyError(f"player not found: {player.id}")
        row = self._conn.execute(select(players).where(players.c.id == player.id)).mappings().one()
        return _row_to_player(row)

    # -- turn runs (U4) --------------------------------------------------- #
    def create_run(self, run: TurnRun) -> TurnRun:
        self._conn.execute(
            turn_runs.insert().values(
                id=run.id,
                session_id=run.session_id,
                status=_enum_value(run.status),
                action=run.action.model_dump(mode="json") if run.action is not None else None,
                cost_turns=run.cost_turns,
                started_turn=run.started_turn,
                finished_at=run.finished_at,
                result=run.result.model_dump(mode="json") if run.result is not None else None,
                error=run.error,
            )
        )
        row = self._conn.execute(select(turn_runs).where(turn_runs.c.id == run.id)).mappings().one()
        return _row_to_run(row)

    def get_run(self, session_id: str, run_id: str) -> TurnRun | None:
        row = (
            self._conn.execute(
                select(turn_runs).where(
                    turn_runs.c.session_id == session_id, turn_runs.c.id == run_id
                )
            )
            .mappings()
            .one_or_none()
        )
        return _row_to_run(row) if row else None

    def update_run(self, run: TurnRun) -> TurnRun:
        res = self._conn.execute(
            update(turn_runs)
            .where(turn_runs.c.id == run.id, turn_runs.c.session_id == run.session_id)
            .values(
                status=_enum_value(run.status),
                finished_at=run.finished_at,
                result=run.result.model_dump(mode="json") if run.result is not None else None,
                error=run.error,
            )
        )
        if res.rowcount == 0:
            raise KeyError(f"turn run not found: {run.id}")
        row = self._conn.execute(select(turn_runs).where(turn_runs.c.id == run.id)).mappings().one()
        return _row_to_run(row)

    def list_runs(self, session_id: str, status: str | None = None) -> list[TurnRun]:
        stmt = select(turn_runs).where(turn_runs.c.session_id == session_id)
        if status is not None:
            stmt = stmt.where(turn_runs.c.status == status)
        stmt = stmt.order_by(turn_runs.c.started_at, turn_runs.c.id)
        rows = self._conn.execute(stmt).mappings().all()
        return [_row_to_run(r) for r in rows]

    def fail_stale_runs(self, *, reason: str) -> int:
        res = self._conn.execute(
            update(turn_runs)
            .where(turn_runs.c.status == TurnRunStatus.RUNNING.value)
            .values(
                status=TurnRunStatus.FAILED.value,
                error=reason,
                finished_at=datetime.now(timezone.utc),
            )
        )
        return int(res.rowcount or 0)

    # -- conversations (U5) ----------------------------------------------- #
    def create_conversation(self, conversation: Conversation) -> Conversation:
        # Pre-read first: the common race loser never reaches the insert. The insert
        # still maps the named unique violation (and only that one) for the narrow
        # window between the read and the write (plan review R-15).
        if self._conversation_row(conversation.session_id, conversation.npc_id) is not None:
            raise ConversationExistsError(
                f"conversation exists: {conversation.session_id}/{conversation.npc_id}"
            )
        try:
            self._conn.execute(
                conversations.insert().values(
                    id=conversation.id,
                    session_id=conversation.session_id,
                    npc_id=conversation.npc_id,
                    started_turn=conversation.started_turn,
                )
            )
        except IntegrityError as exc:
            if _is_conversation_unique_violation(exc):
                raise ConversationExistsError(
                    f"conversation exists: {conversation.session_id}/{conversation.npc_id}"
                ) from exc
            raise
        row = self._conversation_row(conversation.session_id, conversation.npc_id)
        return _row_to_conversation(row, [])

    def get_conversation(self, session_id: str, npc_id: str) -> Conversation | None:
        row = self._conversation_row(session_id, npc_id)
        if row is None:
            return None
        msg_rows = (
            self._conn.execute(
                select(messages)
                .where(messages.c.conversation_id == row["id"])
                .order_by(messages.c.created_at, messages.c.id)
            )
            .mappings()
            .all()
        )
        return _row_to_conversation(row, [_row_to_message(m) for m in msg_rows])

    def append_message(self, message: Message) -> Message:
        exists = self._conn.execute(
            select(conversations.c.id).where(conversations.c.id == message.conversation_id)
        ).scalar_one_or_none()
        if exists is None:
            raise KeyError(f"conversation not found: {message.conversation_id}")
        stored = message.model_copy(update={"created_at": message.created_at or next_timestamp()})
        self._conn.execute(
            messages.insert().values(
                id=stored.id,
                conversation_id=stored.conversation_id,
                role=stored.role,
                text=stored.text,
                lang=stored.lang,
                turn=stored.turn,
                created_at=stored.created_at,
            )
        )
        return stored

    def list_conversations(self, session_id: str) -> list[Conversation]:
        rows = (
            self._conn.execute(
                select(conversations)
                .where(conversations.c.session_id == session_id)
                .order_by(conversations.c.created_at, conversations.c.id)
            )
            .mappings()
            .all()
        )
        return [_row_to_conversation(r, []) for r in rows]

    def _conversation_row(self, session_id: str, npc_id: str):
        return (
            self._conn.execute(
                select(conversations).where(
                    conversations.c.session_id == session_id,
                    conversations.c.npc_id == npc_id,
                )
            )
            .mappings()
            .one_or_none()
        )


class _PgUnitOfWork:
    """One ``engine.begin()`` transaction; every store attribute is the same
    ``_PgStores`` bound to that connection (commit on clean exit, rollback on error)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._ctx: Any = None
        self._stores: _PgStores | None = None

    def __enter__(self) -> PlayUnitOfWork:
        self._ctx = self._engine.begin()
        self._stores = _PgStores(self._ctx.__enter__())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        ctx, self._ctx, self._stores = self._ctx, None, None
        ctx.__exit__(exc_type, exc, tb)

    @property
    def _s(self) -> _PgStores:
        if self._stores is None:
            raise RuntimeError("unit of work is not open")
        return self._stores

    @property
    def sessions(self) -> _PgStores:
        return self._s

    @property
    def rumors(self) -> _PgStores:
        return self._s

    @property
    def distortions(self) -> _PgStores:
        return self._s

    @property
    def timeline(self) -> _PgStores:
        return self._s

    @property
    def events(self) -> _PgStores:
        return self._s

    @property
    def players(self) -> _PgStores:
        return self._s

    @property
    def runs(self) -> _PgStores:
        return self._s

    @property
    def conversations(self) -> _PgStores:
        return self._s


class PostgresPlayRepository:
    """SQLAlchemy-backed ``PlayRepository`` (all play ports). Pass ``engine`` for tests."""

    def __init__(self, url: str | None = None, *, engine: Engine | None = None) -> None:
        self._url = url
        self._engine = engine
        self._owns_engine = engine is None  # an injected (shared) engine is never disposed here

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> None:
        if self._engine is None:
            if not self._url:
                raise RuntimeError("PostgresPlayRepository needs a url or engine")
            self._engine = make_engine(self._url)

    def disconnect(self) -> None:
        """Dispose the engine this adapter created; an injected engine belongs to
        ``SharedContainer`` and stays usable (review U1 #14)."""
        if self._engine is not None and self._owns_engine:
            self._engine.dispose()
            self._engine = None

    def health_check(self) -> bool:
        if self._engine is None:
            return False
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def ensure_schema(self) -> None:
        engine = self._require_engine()
        ensure_play_schema(engine)

    # -- unit of work (U4) ------------------------------------------------- #
    def uow(self) -> PlayUnitOfWork:
        return _PgUnitOfWork(self._require_engine())

    def _tx(self, op: Callable[[_PgStores], T]) -> T:
        """Run one store call in its own transaction (autocommit per call)."""
        with self._require_engine().begin() as conn:
            return op(_PgStores(conn))

    # -- sessions --------------------------------------------------------- #
    def create_session(self, world_id: str) -> GameSession:
        return self._tx(lambda s: s.create_session(world_id))

    def get_session(self, session_id: str) -> GameSession | None:
        return self._tx(lambda s: s.get_session(session_id))

    def list_sessions(self, world_id: str) -> list[GameSession]:
        return self._tx(lambda s: s.list_sessions(world_id))

    def close_session(self, session_id: str) -> GameSession:
        return self._tx(lambda s: s.close_session(session_id))

    def bump_turn(self, session_id: str) -> int:
        return self._tx(lambda s: s.bump_turn(session_id))

    # -- rumors ----------------------------------------------------------- #
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor:
        return self._tx(lambda s: s.upsert_rumor(rumor))

    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]:
        """Batch upsert in a single transaction (FR-H5 / BR-H1-13)."""
        return self._tx(lambda s: s.upsert_rumors(rumors))

    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None:
        return self._tx(lambda s: s.get_rumor(session_id, rumor_id))

    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]:
        return self._tx(
            lambda s: s.list_rumors(session_id, region_id, include_pruned=include_pruned)
        )

    def delete_rumor(self, session_id: str, rumor_id: str) -> None:
        self._tx(lambda s: s.delete_rumor(session_id, rumor_id))

    # -- region distortion ------------------------------------------------ #
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        self._tx(lambda s: s.set_region_distortion(session_id, region_id, degree))

    def get_region_distortion(self, session_id: str, region_id: str) -> float | None:
        return self._tx(lambda s: s.get_region_distortion(session_id, region_id))

    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]:
        return self._tx(lambda s: s.list_region_distortions(session_id))

    # -- timeline --------------------------------------------------------- #
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry:
        return self._tx(lambda s: s.append_timeline(entry))

    def list_timeline(self, session_id: str) -> list[TimelineEntry]:
        return self._tx(lambda s: s.list_timeline(session_id))

    # -- events (Phase 2) ------------------------------------------------- #
    def create_event(self, event: SessionEvent) -> SessionEvent:
        return self._tx(lambda s: s.create_event(event))

    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None:
        return self._tx(lambda s: s.get_event(session_id, event_id))

    def list_events(self, session_id: str, status: str | None = None) -> list[SessionEvent]:
        return self._tx(lambda s: s.list_events(session_id, status))

    def update_event(self, event: SessionEvent) -> SessionEvent:
        return self._tx(lambda s: s.update_event(event))

    def delete_event(self, session_id: str, event_id: str) -> None:
        self._tx(lambda s: s.delete_event(session_id, event_id))

    # -- players (U4) ----------------------------------------------------- #
    def create_player(self, player: Player) -> Player:
        return self._tx(lambda s: s.create_player(player))

    def get_player(self, session_id: str) -> Player | None:
        return self._tx(lambda s: s.get_player(session_id))

    def update_player(self, player: Player) -> Player:
        return self._tx(lambda s: s.update_player(player))

    # -- turn runs (U4) --------------------------------------------------- #
    def create_run(self, run: TurnRun) -> TurnRun:
        return self._tx(lambda s: s.create_run(run))

    def get_run(self, session_id: str, run_id: str) -> TurnRun | None:
        return self._tx(lambda s: s.get_run(session_id, run_id))

    def update_run(self, run: TurnRun) -> TurnRun:
        return self._tx(lambda s: s.update_run(run))

    def list_runs(self, session_id: str, status: str | None = None) -> list[TurnRun]:
        return self._tx(lambda s: s.list_runs(session_id, status))

    def fail_stale_runs(self, *, reason: str) -> int:
        return self._tx(lambda s: s.fail_stale_runs(reason=reason))

    # -- conversations (U5) ----------------------------------------------- #
    def create_conversation(self, conversation: Conversation) -> Conversation:
        return self._tx(lambda s: s.create_conversation(conversation))

    def get_conversation(self, session_id: str, npc_id: str) -> Conversation | None:
        return self._tx(lambda s: s.get_conversation(session_id, npc_id))

    def append_message(self, message: Message) -> Message:
        return self._tx(lambda s: s.append_message(message))

    def list_conversations(self, session_id: str) -> list[Conversation]:
        return self._tx(lambda s: s.list_conversations(session_id))

    # -- helpers ---------------------------------------------------------- #
    def _require_engine(self) -> Engine:
        if self._engine is None:
            self.connect()
        return self._engine  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Row <-> model mapping
# --------------------------------------------------------------------------- #
def _row_to_session(row) -> GameSession:
    return GameSession(
        id=row["id"],
        world_id=row["world_id"],
        status=row["status"],
        turn=row["turn"],
        created_at=row["created_at"],
        closed_at=row["closed_at"],
    )


def _rumor_to_values(r: SessionRumor) -> dict:
    return {
        "id": r.id,
        "session_id": r.session_id,
        "region_id": r.region_id,
        "distorted_from_id": r.distorted_from_id,
        "distorted_from_kind": r.distorted_from_kind,
        "statement": r.statement,
        "distortion_degree": r.distortion_degree,
        "support": r.support,
        "confidence": r.confidence,
        "promoted": r.promoted,
        "active": r.active,
        "provenance": r.provenance.model_dump(),
    }


def _row_to_rumor(row) -> SessionRumor:
    return SessionRumor(
        id=row["id"],
        session_id=row["session_id"],
        region_id=row["region_id"],
        distorted_from_id=row["distorted_from_id"],
        distorted_from_kind=row["distorted_from_kind"],
        statement=row["statement"],
        distortion_degree=row["distortion_degree"],
        support=row["support"],
        confidence=row["confidence"],
        promoted=row["promoted"],
        active=row["active"],
        provenance=Provenance.model_validate(row["provenance"]),
    )


def _row_to_timeline(row) -> TimelineEntry:
    return TimelineEntry(
        id=row["id"],
        session_id=row["session_id"],
        turn=row["turn"],
        kind=row["kind"],
        summary=row["summary"],
        payload=row["payload"] or {},
        created_at=row["created_at"],
    )


def _kind_value(kind) -> str:
    return kind.value if isinstance(kind, TimelineKind) else str(kind)


def _event_to_values(e: SessionEvent) -> dict:
    return {
        "id": e.id,
        "session_id": e.session_id,
        "region_id": e.region_id,
        "category": _enum_value(e.category),
        "description": e.description,
        "magnitude": e.magnitude,
        "lifecycle": _enum_value(e.lifecycle),
        "status": _enum_value(e.status),
        "created_turn": e.created_turn,
        "resolved_turn": e.resolved_turn,
        "contributions": e.contributions,
        "provenance": e.provenance.model_dump(),
    }


def _row_to_event(row) -> SessionEvent:
    return SessionEvent(
        id=row["id"],
        session_id=row["session_id"],
        region_id=row["region_id"],
        category=row["category"],
        description=row["description"],
        magnitude=row["magnitude"],
        lifecycle=row["lifecycle"],
        status=row["status"],
        created_turn=row["created_turn"],
        resolved_turn=row["resolved_turn"],
        contributions=row["contributions"] or {},
        provenance=Provenance.model_validate(row["provenance"]),
    )


def _row_to_player(row) -> Player:
    return Player(
        id=row["id"],
        session_id=row["session_id"],
        name=row["name"],
        region_id=row["region_id"],
        turns_spent=row["turns_spent"],
        created_at=row["created_at"],
    )


def _row_to_run(row) -> TurnRun:
    return TurnRun(
        id=row["id"],
        session_id=row["session_id"],
        action=row["action"],
        cost_turns=row["cost_turns"],
        status=row["status"],
        started_turn=row["started_turn"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        result=row["result"],
        error=row["error"],
    )


def _enum_value(v) -> str:
    """Enum field values are already strings (use_enum_values=True), but accept enums too."""
    return v.value if isinstance(v, Enum) else str(v)


def _row_to_conversation(row, msgs: list[Message]) -> Conversation:
    return Conversation(
        id=row["id"],
        session_id=row["session_id"],
        npc_id=row["npc_id"],
        started_turn=row["started_turn"],
        created_at=row["created_at"],
        messages=msgs,
    )


def _row_to_message(row) -> Message:
    return Message(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        text=row["text"],
        lang=row["lang"],
        turn=row["turn"],
        created_at=row["created_at"],
    )


def _is_conversation_unique_violation(exc: IntegrityError) -> bool:
    """Only the (session_id, npc_id) uniqueness — never an unrelated integrity error.

    PostgreSQL names the constraint (``diag.constraint_name``); SQLite (offline tests)
    only names the columns in the message.
    """
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    name = getattr(diag, "constraint_name", None)
    if name is not None:
        return name == CONVERSATION_UNIQUE
    text_ = str(getattr(exc, "orig", exc))
    return "conversations.session_id" in text_ and "conversations.npc_id" in text_
