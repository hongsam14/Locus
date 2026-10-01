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


# --------------------------------------------------------------------------- #
# Event vocabulary (U8, FD domain-entities §2). Moved here from ``play/models.py``:
# an event seed is world data that the World File (world boundary) validates, and the
# world boundary may not import play. This is an intended exception to FR-A2's "shared
# vocabulary knows no boundary's concepts"; ``locus.play.models`` re-exports the names.
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
