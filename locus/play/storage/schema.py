"""play boundary schema: tables + idempotent DDL (owned by play, FR-A4).

``play_metadata`` holds only the play tables; the localization boundary owns
``translations`` in its own ``MetaData``. No foreign keys cross the two.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
    TypeDecorator,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine

# JSONB on PostgreSQL, plain JSON on other dialects (e.g. SQLite for offline tests).
_JSON = JSON().with_variant(JSONB(), "postgresql")


class UtcDateTime(TypeDecorator):
    """``DateTime(timezone=True)`` that always reads back an aware UTC value.

    SQLite (offline tests) drops the zone; stay boundaries and summary cursors compare
    these values, so every play timestamp is read as UTC (U6 review C16; replaces the
    adapter's per-mapper ``_aware``).
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=timezone.utc)


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
    Column("created_at", UtcDateTime(), server_default=text("CURRENT_TIMESTAMP")),
    Column("closed_at", UtcDateTime(), nullable=True),
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
    # U6: rumor origin (domain-entities §2.4); added to older DBs by ensure_play_schema
    Column("origin_kind", String, nullable=False, default="canonical", server_default="canonical"),
    Column("origin_deed_id", String, nullable=True, index=True),
    Column("origin_appraisal_id", String, nullable=True),
    Column("spread_from_region_id", String, nullable=True),
)

region_distortions = Table(
    "region_distortions",
    play_metadata,
    Column("session_id", String, primary_key=True),
    Column("region_id", String, primary_key=True),
    Column("distortion_degree", Float, nullable=False),
    # U7 (Q2=A): the part of the degree that rumor feedback put there
    Column("feedback_share", Float, nullable=False, default=0.0, server_default=text("0")),
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
    Column("created_at", UtcDateTime(), server_default=text("CURRENT_TIMESTAMP")),
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
    Column("created_at", UtcDateTime(), server_default=text("CURRENT_TIMESTAMP")),
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
    Column("started_at", UtcDateTime(), server_default=text("CURRENT_TIMESTAMP")),
    Column("finished_at", UtcDateTime(), nullable=True),
    Column("result", _JSON, nullable=True),
    Column("error", Text, nullable=True),
    # U6: kept so a background run re-read from the store still has them — before U6 the
    # PostgreSQL adapter dropped turns_charged / from_region_id and U4's failed-run
    # compensation silently did nothing (NFR review R-03).
    Column("lang", String, nullable=True),
    Column("turns_charged", Integer, nullable=False, default=0, server_default="0"),
    Column("from_region_id", String, nullable=True),
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
    Column("created_at", UtcDateTime(), server_default=text("CURRENT_TIMESTAMP")),
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
    Column("created_at", UtcDateTime(), nullable=False),
)


# U6 deeds & spread — what the player did, and how each NPC who heard of it judged it.
DEED_APPRAISAL_UNIQUE = "uq_deed_appraisals_deed_npc"

deeds = Table(
    "deeds",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("player_id", String, nullable=False),
    Column("region_id", String, nullable=False),
    Column("turn", Integer, nullable=False, default=0),
    Column("kind", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("declaration", Text, nullable=True),
    Column("messages_through", UtcDateTime(), nullable=True),
    Column("witnessed_npc_ids", _JSON, nullable=False),
    Column("voided", Boolean, nullable=False, default=False),
    Column("voided_turn", Integer, nullable=True),
    Column("run_id", String, nullable=True, index=True),
    # stamped by the application (next_timestamp): a stay is ordered by it
    Column("created_at", UtcDateTime(), nullable=False),
)

deed_appraisals = Table(
    "deed_appraisals",
    play_metadata,
    Column("id", String, primary_key=True),
    Column("session_id", String, nullable=False, index=True),
    Column("deed_id", String, nullable=False, index=True),
    Column("npc_id", String, nullable=False),
    Column("noteworthy", Boolean, nullable=False),
    Column("salience", Float, nullable=False),
    Column("slant", Text, nullable=False, default=""),
    Column("retelling", Text, nullable=False, default=""),
    Column("turn", Integer, nullable=False, default=0),
    Column("seeded_rumor_id", String, nullable=True),
    Column("run_id", String, nullable=True, index=True),
    Column("created_at", UtcDateTime(), nullable=False),
    UniqueConstraint("deed_id", "npc_id", name=DEED_APPRAISAL_UNIQUE),
)

# Columns added to tables that older databases already have (create_all never alters an
# existing table). One list for both dialects (U6 NFR review R-02; BR-U6-34) — the U-H1
# ``active`` column, once a PostgreSQL-only special case, is the first entry.
ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("session_rumors", "active", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("session_rumors", "origin_kind", "VARCHAR NOT NULL DEFAULT 'canonical'"),
    ("session_rumors", "origin_deed_id", "VARCHAR"),
    ("session_rumors", "origin_appraisal_id", "VARCHAR"),
    ("session_rumors", "spread_from_region_id", "VARCHAR"),
    ("turn_runs", "lang", "VARCHAR"),
    ("turn_runs", "turns_charged", "INTEGER NOT NULL DEFAULT 0"),
    ("turn_runs", "from_region_id", "VARCHAR"),
    ("deed_appraisals", "run_id", "VARCHAR"),
    ("region_distortions", "feedback_share", "FLOAT NOT NULL DEFAULT 0"),
)
ADDED_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_session_rumors_origin_deed_id", "session_rumors", "origin_deed_id"),
    ("ix_deed_appraisals_run_id", "deed_appraisals", "run_id"),
)


def ensure_play_schema(engine: Engine) -> None:
    """Idempotent: ``CREATE TABLE IF NOT EXISTS`` for the play tables (BR-S1-17), then the
    columns and indexes older databases lack — found with the inspector on both dialects,
    so existing sessions are kept (U6 N6-3) and offline SQLite tests cover the path."""
    play_metadata.create_all(engine, checkfirst=True)
    if_not_exists = "" if engine.dialect.name == "sqlite" else "IF NOT EXISTS "
    with engine.begin() as conn:
        insp = inspect(conn)
        present: dict[str, set[str]] = {}
        for table, column, ddl in ADDED_COLUMNS:
            if table not in present:
                present[table] = {c["name"] for c in insp.get_columns(table)}
            if column in present[table]:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {if_not_exists}{column} {ddl}"))
            present[table].add(column)
        for name, table, column in ADDED_INDEXES:
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column})"))
