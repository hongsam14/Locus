"""PostgreSQL implementation of SessionRepository (SQLAlchemy 2.0, sync).

Hybrid schema (FD-S1 Q3=A): core fields are regular indexed columns; the
variable/nested parts (``provenance``, timeline ``payload``) are JSON columns
(JSONB on PostgreSQL, generic JSON elsewhere so the same adapter runs against
SQLite in offline tests). Ids are application-generated (``new_id``);
``created_at`` is set by the DB server (``func.now()``, FD-S1 Q4=A).

``ensure_schema`` is idempotent ``CREATE TABLE IF NOT EXISTS`` (BR-S1-17).
"""

from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

from ..models import Provenance
from ..session.models import (
    GameSession,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)

# JSONB on PostgreSQL, plain JSON on other dialects (e.g. SQLite for offline tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")

_metadata = MetaData()

game_sessions = Table(
    "game_sessions",
    _metadata,
    Column("id", String, primary_key=True),
    Column("world_id", String, nullable=False, index=True),
    Column("status", String, nullable=False),
    Column("turn", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    Column("closed_at", DateTime(timezone=True), nullable=True),
)

session_rumors = Table(
    "session_rumors",
    _metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("region_id", String, nullable=False, index=True),
    Column("distorted_from_id", String, nullable=False),
    Column("distorted_from_kind", String, nullable=False, default="knowledge"),
    Column("statement", Text, nullable=False, default=""),
    Column("distortion_degree", Float, nullable=False),
    Column("support", Float, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("promoted", Boolean, nullable=False, default=False),
    Column("active", Boolean, nullable=False, default=True),  # soft-flag prune (BR-H1-5)
    Column("provenance", _JSON, nullable=False),
)

region_distortions = Table(
    "region_distortions",
    _metadata,
    Column("session_id", String, primary_key=True),
    Column("region_id", String, primary_key=True),
    Column("distortion_degree", Float, nullable=False),
)

timeline_entries = Table(
    "timeline_entries",
    _metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("turn", Integer, nullable=False, default=0),
    Column("kind", String, nullable=False),
    Column("summary", Text, nullable=False, default=""),
    Column("payload", _JSON, nullable=False, default=dict),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
)

# Phase 2 — hybrid: core fields = indexed columns, contributions/provenance = JSON(B).
session_events = Table(
    "session_events",
    _metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("region_id", String, nullable=False, index=True),
    Column("category", String, nullable=False),
    Column("description", Text, nullable=False, default=""),
    Column("magnitude", Float, nullable=False),
    Column("lifecycle", String, nullable=False),
    Column("status", String, nullable=False, index=True),
    Column("created_turn", Integer, nullable=False, default=0),
    Column("resolved_turn", Integer, nullable=True),
    Column("contributions", _JSON, nullable=False, default=dict),
    Column("provenance", _JSON, nullable=False),
)


class PostgresSessionRepository:
    """SQLAlchemy-backed SessionRepository. Pass ``engine`` for tests."""

    def __init__(self, url: str | None = None, *, engine: Engine | None = None) -> None:
        self._url = url
        self._engine = engine

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> None:
        if self._engine is None:
            if not self._url:
                raise RuntimeError("PostgresSessionRepository needs a url or engine")
            self._engine = create_engine(self._url, future=True)

    def disconnect(self) -> None:
        if self._engine is not None:
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
        _metadata.create_all(engine, checkfirst=True)
        # Additive column for existing DBs (idempotent). Skipped on SQLite offline
        # tests, where create_all already includes the column (NFR-H4 / BR-H1-16).
        if engine.dialect.name != "sqlite":
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE session_rumors "
                        "ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE"
                    )
                )

    # -- sessions --------------------------------------------------------- #
    def create_session(self, world_id: str) -> GameSession:
        session = GameSession(world_id=world_id, status=SessionStatus.OPEN, turn=0)
        with self._require_engine().begin() as conn:
            conn.execute(
                game_sessions.insert().values(
                    id=session.id,
                    world_id=world_id,
                    status=SessionStatus.OPEN.value,
                    turn=0,
                    closed_at=None,
                )
            )
            row = (
                conn.execute(select(game_sessions).where(game_sessions.c.id == session.id))
                .mappings()
                .one()
            )
        return _row_to_session(row)

    def get_session(self, session_id: str) -> GameSession | None:
        with self._require_engine().connect() as conn:
            row = (
                conn.execute(select(game_sessions).where(game_sessions.c.id == session_id))
                .mappings()
                .one_or_none()
            )
        return _row_to_session(row) if row else None

    def list_sessions(self, world_id: str) -> list[GameSession]:
        with self._require_engine().connect() as conn:
            rows = (
                conn.execute(
                    select(game_sessions)
                    .where(game_sessions.c.world_id == world_id)
                    .order_by(game_sessions.c.created_at)
                )
                .mappings()
                .all()
            )
        return [_row_to_session(r) for r in rows]

    def close_session(self, session_id: str) -> GameSession:
        with self._require_engine().begin() as conn:
            current = conn.execute(
                select(game_sessions.c.status).where(game_sessions.c.id == session_id)
            ).scalar_one_or_none()
            if current is None:
                raise KeyError(f"session not found: {session_id}")
            if current != SessionStatus.CLOSED.value:
                conn.execute(
                    update(game_sessions)
                    .where(game_sessions.c.id == session_id)
                    .values(status=SessionStatus.CLOSED.value, closed_at=text("CURRENT_TIMESTAMP"))
                )
            row = (
                conn.execute(select(game_sessions).where(game_sessions.c.id == session_id))
                .mappings()
                .one()
            )
        return _row_to_session(row)

    def bump_turn(self, session_id: str) -> int:
        with self._require_engine().begin() as conn:
            res = conn.execute(
                update(game_sessions)
                .where(game_sessions.c.id == session_id)
                .values(turn=game_sessions.c.turn + 1)
            )
            if res.rowcount == 0:
                raise KeyError(f"session not found: {session_id}")
            return conn.execute(
                select(game_sessions.c.turn).where(game_sessions.c.id == session_id)
            ).scalar_one()

    # -- rumors ----------------------------------------------------------- #
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor:
        with self._require_engine().begin() as conn:
            self._upsert_rumor_conn(conn, rumor)
        return rumor.model_copy(deep=True)

    def upsert_rumors(self, rumors: list[SessionRumor]) -> list[SessionRumor]:
        """Batch upsert in a single transaction (FR-H5 / BR-H1-13)."""
        with self._require_engine().begin() as conn:
            for rumor in rumors:
                self._upsert_rumor_conn(conn, rumor)
        return [r.model_copy(deep=True) for r in rumors]

    @staticmethod
    def _upsert_rumor_conn(conn, rumor: SessionRumor) -> None:
        values = _rumor_to_values(rumor)
        exists = conn.execute(
            select(session_rumors.c.id).where(session_rumors.c.id == rumor.id)
        ).scalar_one_or_none()
        if exists:
            conn.execute(
                update(session_rumors).where(session_rumors.c.id == rumor.id).values(**values)
            )
        else:
            conn.execute(session_rumors.insert().values(**values))

    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None:
        with self._require_engine().connect() as conn:
            row = (
                conn.execute(
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
        with self._require_engine().connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [_row_to_rumor(r) for r in rows]

    def delete_rumor(self, session_id: str, rumor_id: str) -> None:
        with self._require_engine().begin() as conn:
            conn.execute(
                delete(session_rumors).where(
                    session_rumors.c.session_id == session_id,
                    session_rumors.c.id == rumor_id,
                )
            )

    # -- region distortion ------------------------------------------------ #
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        with self._require_engine().begin() as conn:
            exists = conn.execute(
                select(region_distortions.c.session_id).where(
                    region_distortions.c.session_id == session_id,
                    region_distortions.c.region_id == region_id,
                )
            ).first()
            if exists:
                conn.execute(
                    update(region_distortions)
                    .where(
                        region_distortions.c.session_id == session_id,
                        region_distortions.c.region_id == region_id,
                    )
                    .values(distortion_degree=degree)
                )
            else:
                conn.execute(
                    region_distortions.insert().values(
                        session_id=session_id, region_id=region_id, distortion_degree=degree
                    )
                )

    def get_region_distortion(self, session_id: str, region_id: str) -> float | None:
        with self._require_engine().connect() as conn:
            return conn.execute(
                select(region_distortions.c.distortion_degree).where(
                    region_distortions.c.session_id == session_id,
                    region_distortions.c.region_id == region_id,
                )
            ).scalar_one_or_none()

    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]:
        with self._require_engine().connect() as conn:
            rows = (
                conn.execute(
                    select(region_distortions).where(region_distortions.c.session_id == session_id)
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
        with self._require_engine().begin() as conn:
            conn.execute(
                timeline_entries.insert().values(
                    id=entry.id,
                    session_id=entry.session_id,
                    turn=entry.turn,
                    kind=_kind_value(entry.kind),
                    summary=entry.summary,
                    payload=entry.payload,
                )
            )
            row = (
                conn.execute(select(timeline_entries).where(timeline_entries.c.id == entry.id))
                .mappings()
                .one()
            )
        return _row_to_timeline(row)

    def list_timeline(self, session_id: str) -> list[TimelineEntry]:
        with self._require_engine().connect() as conn:
            rows = (
                conn.execute(
                    select(timeline_entries)
                    .where(timeline_entries.c.session_id == session_id)
                    .order_by(timeline_entries.c.turn, timeline_entries.c.created_at)
                )
                .mappings()
                .all()
            )
        return [_row_to_timeline(r) for r in rows]

    # -- events (Phase 2) ------------------------------------------------- #
    def create_event(self, event: SessionEvent) -> SessionEvent:
        with self._require_engine().begin() as conn:
            conn.execute(session_events.insert().values(**_event_to_values(event)))
        return event.model_copy(deep=True)

    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None:
        with self._require_engine().connect() as conn:
            row = (
                conn.execute(
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
        with self._require_engine().connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [_row_to_event(r) for r in rows]

    def update_event(self, event: SessionEvent) -> SessionEvent:
        values = _event_to_values(event)
        with self._require_engine().begin() as conn:
            exists = conn.execute(
                select(session_events.c.id).where(session_events.c.id == event.id)
            ).scalar_one_or_none()
            if exists:
                conn.execute(
                    update(session_events).where(session_events.c.id == event.id).values(**values)
                )
            else:
                conn.execute(session_events.insert().values(**values))
        return event.model_copy(deep=True)

    def delete_event(self, session_id: str, event_id: str) -> None:
        with self._require_engine().begin() as conn:
            conn.execute(
                delete(session_events).where(
                    session_events.c.session_id == session_id,
                    session_events.c.id == event_id,
                )
            )

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


def _enum_value(v) -> str:
    """Enum field values are already strings (use_enum_values=True), but accept enums too."""
    return v.value if isinstance(v, Enum) else str(v)
