"""localization schema: the ``translations`` table (owned by localization, FR-A4)."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, MetaData, String, Table, Text, UniqueConstraint, text
from sqlalchemy.engine import Engine

localization_metadata = MetaData()

# Unified cache across play content + canonical Knowledge;
# key = (source_kind, source_id, source_field, target_lang) (BR-X1-5).
translations = Table(
    "translations",
    localization_metadata,
    Column("id", String, primary_key=True),
    Column("source_kind", String, nullable=False),
    Column("source_id", String, nullable=False, index=True),
    Column("source_field", String, nullable=False),
    Column("target_lang", String, nullable=False),
    Column("text", Text, nullable=False),
    Column("source_hash", String, nullable=False),
    Column("world_id", String, nullable=True, index=True),
    Column("session_id", String, nullable=True, index=True),
    Column("created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")),
    UniqueConstraint(
        "source_kind", "source_id", "source_field", "target_lang", name="uq_translation_key"
    ),
)


def ensure_localization_schema(engine: Engine) -> None:
    """Idempotent ``CREATE TABLE IF NOT EXISTS`` for the translation cache."""
    localization_metadata.create_all(engine, checkfirst=True)
