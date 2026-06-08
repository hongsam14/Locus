"""Core graph domain models (nodes, relationships) for Locus.

Pydantic v2 models mirroring the graph schema in
aidlc-docs/construction/U1-foundation/functional-design/domain-entities.md.

Conventions:
- ``extra="forbid"`` to catch typos / contract drift.
- Confidence / weight in [0.0, 1.0] (BR-4..6).
- Every generated content node carries a ``Provenance`` (BR-7).
"""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import (
    ConnectionKind,
    EntityType,
    PriorType,
    RegionLevel,
    ScopeType,
    SourceKind,
)


def new_id() -> str:
    """Generate a fresh immutable node id (BR-1)."""
    return str(uuid4())


class LocusModel(BaseModel):
    """Base for all Locus models: strict, round-trip-stable (BR-20/21)."""

    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Provenance(LocusModel):
    """Why/where an item came from (BR-7..9)."""

    source: SourceKind
    generated_by: str | None = None  # e.g. "llm:gpt-4o", "user", "rule:terrain"
    refs: list[str] = Field(default_factory=list)  # ids of WikiPrior / ChangeSet / input
    note: str | None = None


class Coord(LocusModel):
    """Normalized map position (0=left/top, 1=right/bottom) for UI overlay (U10)."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


# --------------------------------------------------------------------------- #
# Nodes
# --------------------------------------------------------------------------- #
class World(LocusModel):
    """A game world (or the real-world wiki partition)."""

    world_id: str
    name: str
    kind: str = "game"  # "game" | "realworld"
    description: str | None = None


class Region(LocusModel):
    """A region node, organized in a CONTAINS hierarchy (Q1=B)."""

    id: str = Field(default_factory=new_id)
    world_id: str
    name: str
    level: RegionLevel
    parent_id: str | None = None  # CONTAINS parent (<= 1, BR-16)
    description: str | None = None
    attributes: dict = Field(default_factory=dict)  # e.g. terrain type
    position: Coord | None = None  # normalized map position for UI overlay (U10)
    provenance: Provenance


class Entity(LocusModel):
    """A knowledge entity (place/person/event/object/custom/terrain)."""

    id: str = Field(default_factory=new_id)
    world_id: str
    name: str
    entity_type: EntityType
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    located_in: str | None = None  # LOCATED_IN region id
    embedding_ref: str | None = None
    provenance: Provenance


class Relation(LocusModel):
    """A RELATED_TO edge between two entities."""

    id: str = Field(default_factory=new_id)
    world_id: str
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: Provenance


class Knowledge(LocusModel):
    """A knowledge item / fact held by a region's consensus."""

    id: str = Field(default_factory=new_id)
    world_id: str
    statement: str
    topic: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_global: bool = False  # world-wide fact, known in every region (U4, CL1=A)
    region_hint: str | None = None  # transient: extractor's region name, resolved to scope in U4
    about_entity_ids: list[str] = Field(default_factory=list)  # ABOUT edges
    derived_from_prior_ids: list[str] = Field(default_factory=list)  # DERIVED_FROM
    embedding_ref: str | None = None
    provenance: Provenance


class Rumor(LocusModel):
    """A distorted variant of a Knowledge/Rumor (separate label, FD1-Q4=B).

    Always references exactly one origin via ``distorted_from_id`` (BR-13).
    """

    id: str = Field(default_factory=new_id)
    world_id: str
    statement: str
    distorted_from_id: str  # -> Knowledge or Rumor id (required, BR-13)
    distortion_degree: float = Field(default=0.5, ge=0.0, le=1.0)
    distortion_note: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    embedding_ref: str | None = None
    provenance: Provenance


class WikiPrior(LocusModel):
    """A real-world prior in the Common-sense Wiki (world_id=__realworld__)."""

    id: str = Field(default_factory=new_id)
    prior_type: PriorType
    condition: str  # e.g. "mountain range between two regions"
    effect: str  # e.g. "connection weight x0.3, slower information flow"
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    embedding_ref: str | None = None
    provenance: Provenance


# --------------------------------------------------------------------------- #
# Relationships (carried as standalone records for upsert)
# --------------------------------------------------------------------------- #
class ConnectionEdge(LocusModel):
    """A CONNECTED_TO edge between two regions (topology)."""

    world_id: str
    source_region_id: str
    target_region_id: str
    kind: ConnectionKind
    weight: float = Field(default=0.5, ge=0.0, le=1.0)  # 0=cut off, 1=fully connected
    rationale: str | None = None
    wiki_prior_ref: str | None = None
    provenance: Provenance


class ScopeLink(LocusModel):
    """A SCOPED_TO edge: a Knowledge/Rumor scoped to a region with confidence."""

    world_id: str
    knowledge_id: str
    region_id: str
    is_rumor: bool = False
    scope_type: ScopeType = ScopeType.DIRECT
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
