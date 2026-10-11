"""localization boundary models: the translation cache row."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from locus.shared.models import LocusModel, new_id


class Translation(LocusModel):
    """A cached translation of one source field into one language (X1, C2).

    Unified cache for session content (rumors/events, warmed/lazy) and canonical
    Knowledge (lazy, world-scoped). Key = (source_kind, source_id, source_field,
    target_lang); ``world_id``/``session_id`` are metadata only, not part of the key
    (BR-X1-5/8/9). V3 adds world, region, NPC and event-seed text. Their ids are unique
    within a world only (a demo World File keeps its readable ids): two worlds sharing
    an id share the key, the source hash keeps either from showing the other's text,
    and the cost is that they overwrite each other (code plan memo R-05).
    """

    id: str = Field(default_factory=new_id)
    source_kind: str  # rumor|event|deed|deed_appraisal|knowledge|world|region|npc|event_seed
    source_id: str
    source_field: str  # "statement" | "description" | "title"
    target_lang: str = "ko"
    text: str  # translated text
    source_hash: str  # hash of the source text for invalidation (BR-X1-6)
    world_id: str | None = None  # canonical Knowledge cache partition (BR-X1-8)
    session_id: str | None = None  # session-content cache scope (BR-X1-9)
    created_at: datetime | None = None  # set by DB server time


class SeedReport(LocusModel):
    """What :meth:`TranslationService.seed` did (V3, FD domain-entities § 5)."""

    seeded: int = 0  # rows put in the cache
    stale: int = 0  # entries whose source differs from the world's text now (dropped)
    unknown: int = 0  # entries whose (kind, id, field) the world does not hold (dropped)
