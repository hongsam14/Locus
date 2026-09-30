"""Enumerations shared across Locus domain models.

String-valued enums for stable serialization (BR-21).
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """str-backed Enum: serializes to its value, compares equal to the string."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return str(self.value)


class RegionLevel(StrEnum):
    """Hierarchy level of a region node (FD1-Q1=A, Q1=B)."""

    CONTINENT = "continent"
    PROVINCE = "province"
    TOWN = "town"
    DISTRICT = "district"
    TERRAIN = "terrain"  # promoted VLM area terrain (FR-IM4.1, FD-B Q2=A)


class EntityType(StrEnum):
    """Type of a knowledge entity."""

    PLACE = "place"
    PERSON = "person"
    EVENT = "event"
    OBJECT = "object"
    CUSTOM = "custom"
    TERRAIN = "terrain"


class ScopeType(StrEnum):
    """How a knowledge item reaches a region (FD1-Q3=A; GLOBAL added in U4)."""

    DIRECT = "direct"
    INHERITED = "inherited"
    PROPAGATED = "propagated"
    GLOBAL = "global"
    HEARSAY = "hearsay"  # reached only over a weak path: heard second-hand (path_decay > 0)


class ConnectionKind(StrEnum):
    """Kind of topology connection between two regions."""

    ADJACENT = "adjacent"
    ROUTE = "route"
    RIVER = "river"
    BLOCKED = "blocked"


class PriorType(StrEnum):
    """Type of a Common-sense Wiki prior."""

    TERRAIN_RULE = "terrain_rule"
    CLIMATE = "climate"
    LOGISTICS = "logistics"
    FACT = "fact"


class WikiDomain(StrEnum):
    """Shared domain taxonomy for WikiPriors and (derived) world domain tags.

    Fixed vocabulary the LLM classifies a prior into (FD-A Q4=A). ``OTHER`` is the
    safety net when classification yields nothing (BR-A5).
    """

    GEOGRAPHY = "geography"
    GEOLOGY = "geology"
    CLIMATE = "climate"
    ECOLOGY = "ecology"
    ECONOMY = "economy"
    LOGISTICS = "logistics"
    CULTURE = "culture"
    HISTORY = "history"
    POLITICS = "politics"
    RELIGION = "religion"
    MILITARY = "military"
    TECHNOLOGY = "technology"
    OTHER = "other"


class SourceKind(StrEnum):
    """Provenance source of a generated/recorded item (BR-7).

    Boundary-neutral values: the shared vocabulary must not know about any one
    boundary's concepts (FR-A2). ``SIMULATION`` covers play-layer generated
    content (rumors, events); ``DIALOGUE`` covers NPC conversation output.
    """

    INPUT = "input"
    INFERRED = "inferred"  # wiki-corroborated / distilled content
    AUGMENTATION = "augmentation"
    SIMULATION = "simulation"  # play layer: rumors, events, deeds
    DIALOGUE = "dialogue"  # play layer: NPC dialogue

    @classmethod
    def _missing_(cls, value: object) -> "SourceKind | None":
        """Map values persisted before the U1 rename (Neo4j ``prov_source``, PostgreSQL
        provenance JSON) so stored worlds and sessions stay readable (review U1 #1/#2)."""
        if isinstance(value, str):
            return _LEGACY_SOURCE_KINDS.get(value)
        return None


_LEGACY_SOURCE_KINDS: dict[str, SourceKind] = {
    "inferred-wiki": SourceKind.INFERRED,
    "session-rumor": SourceKind.SIMULATION,
    "session-event": SourceKind.SIMULATION,
}
