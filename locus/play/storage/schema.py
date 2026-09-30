"""play boundary schema: tables + idempotent DDL (owned by play, FR-A4).

``play_metadata`` holds only the play tables; the localization boundary owns
``translations`` in its own ``MetaData``. No foreign keys cross the two.
"""

from __future__ import annotations

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

# JSONB on PostgreSQL, plain JSON on other dialects (e.g. SQLite for offline tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")

# Max ids per IN() chunk — keeps large reads under the DB bind-parameter limit
# (SQLite 999 / PostgreSQL cap) (review #7).
_IN_CHUNK = 500

play_metadata = MetaData()

game_sessions = Table(
    "game_sessions",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("world_id", String, nullable=False, index=True),
    Column("status", String, nullable=False),
    Column("turn", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    Column("closed_at", DateTime(timezone=True), nullable=True),
)

session_rumors = Table(
    "session_rumors",
    play_metadata,
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
    play_metadata,
    Column("session_id", String, primary_key=True),
    Column("region_id", String, primary_key=True),
    Column("distortion_degree", Float, nullable=False),
)

timeline_entries = Table(
    "timeline_entries",
    play_metadata,
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
    play_metadata,
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

# U4 player mode — the solo player (one per session) and turn-run execution records.
players = Table(
    "players",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, unique=True, index=True),
    Column("name", String, nullable=False),
    Column("region_id", String, nullable=False),
    Column("turns_spent", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
)

turn_runs = Table(
    "turn_runs",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("status", String, nullable=False, index=True),
    Column("action", _JSON, nullable=True),
    Column("cost_turns", Integer, nullable=False, default=1),
    Column("started_turn", Integer, nullable=False, default=0),
    Column("started_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    Column("finished_at", DateTime(timezone=True), nullable=True),
    Column("result", _JSON, nullable=True),
    Column("error", Text, nullable=True),
)

# U5 NPC dialogue — one conversation per (session, NPC), its messages in order.
# The unique constraint is named so the adapter can tell *this* violation apart from
# any other integrity error (plan review R-15).
CONVERSATION_UNIQUE = "uq_conversations_session_npc"

conversations = Table(
    "conversations",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("npc_id", String, nullable=False),
    Column("started_turn", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint("session_id", "npc_id", name=CONVERSATION_UNIQUE),
)

messages = Table(
    "messages",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("conversation_id", String, nullable=False, index=True),
    Column("role", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("lang", String, nullable=False),
    Column("turn", Integer, nullable=False, default=0),
    # stamped by the application (next_timestamp) so order survives one transaction
    Column("created_at", DateTime(timezone=True), nullable=False),
)


def ensure_play_schema(engine: Engine) -> None:
    """Idempotent ``CREATE TABLE IF NOT EXISTS`` for the play tables (BR-S1-17)."""
    play_metadata.create_all(engine, checkfirst=True)
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
