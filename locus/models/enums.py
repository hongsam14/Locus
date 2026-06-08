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


class ConnectionKind(StrEnum):
    """Kind of topology connection between two regions."""

    ADJACENT = "adjacent"
    ROUTE = "route"
    RIVER = "river"
    BLOCKED = "blocked"


class PriorType(StrEnum):
    """Type of a real-world Common-sense Wiki prior."""

    TERRAIN_RULE = "terrain_rule"
    CLIMATE = "climate"
    LOGISTICS = "logistics"
    FACT = "fact"


class SourceKind(StrEnum):
    """Provenance source of a generated/recorded item (BR-7)."""

    INPUT = "input"
    INFERRED_WIKI = "inferred-wiki"
    AUGMENTATION = "augmentation"
