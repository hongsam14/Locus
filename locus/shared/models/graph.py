"""Core graph domain models (nodes, relationships) for Locus.

Pydantic v2 models mirroring the graph schema in
aidlc-docs/construction/U1-foundation/functional-design/domain-entities.md.

Conventions:
- ``extra="forbid"`` to catch typos / contract drift.
- Confidence / weight in [0.0, 1.0] (BR-4..6).
- Every generated content node carries a ``Provenance`` (BR-7).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from locus.shared.models.enums import (
    ConnectionKind,
    EntityType,
    EventCategory,
    EventLifecycle,
    PriorType,
    RegionLevel,
    ScopeType,
    SourceKind,
    WikiDomain,
)


def new_id() -> str:
    """Generate a fresh immutable node id (BR-1)."""
    return str(uuid4())


def fallback_title(statement: str, *, max_len: int = 60) -> str:
    """Derive a one-line title from a statement (BR-A2).

    Used when the LLM omits a title so ``Knowledge.title`` (required, BR-A1) is
    always satisfiable. Truncates on a word boundary near ``max_len``.
    """
    text = " ".join(statement.strip().split())
    if len(text) <= max_len:
        return text or "(untitled)"
    cut = text[:max_len].rsplit(" ", 1)[0]
    return (cut or text[:max_len]).rstrip() + "…"


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
    title: str  # required one-line title / UI label (BR-A1; LLM-generated, BR-A2 fallback)
    topic: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_global: bool = False  # world-wide fact, known in every region (U4, CL1=A)
    region_hint: str | None = None  # transient: extractor's region name, resolved to scope in U4
    about_entity_ids: list[str] = Field(default_factory=list)  # ABOUT edges
    derived_from_prior_ids: list[str] = Field(default_factory=list)  # DERIVED_FROM
    provenance: Provenance


class WikiPrior(LocusModel):
    """A common-sense prior in a world's Wiki (FR-IM1.2).

    Belongs to a world (``world_id``); no reserved partition. ``domains`` place it
    in the shared taxonomy for community/cross-domain linking and the designer's
    cross-world reference (FR-IM2.1).
    """

    id: str = Field(default_factory=new_id)
    world_id: str
    prior_type: PriorType
    condition: str  # e.g. "mountain range between two regions"
    effect: str  # e.g. "connection weight x0.3, slower information flow"
    domains: list[WikiDomain] = Field(default_factory=list)  # shared taxonomy (BR-A5)
    description: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    provenance: Provenance


class WikiPriorLink(LocusModel):
    """A PRIOR_RELATED_TO edge between two WikiPriors in the same world (FR-IM2.3).

    Stored as a graph edge only (no node, FD-A Q5=A). Single-direction storage,
    undirected semantics. Never crosses a world boundary (BR-A6).
    """

    world_id: str
    source_id: str
    target_id: str
    relation: str  # LLM-named relation label, e.g. "reinforces" / "implies"
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    cross_domain: bool = False  # source/target domains disjoint (search/viz flag)
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


# --------------------------------------------------------------------------- #
# World-level metadata and NPCs (U2)
# --------------------------------------------------------------------------- #
WorldWriter = Literal["build", "import", "edit"]


def utcnow() -> datetime:
    return datetime.now(UTC)


class WorldMeta(LocusModel):
    """One node per world: display name, description, last write (U2 Q2=A, BR-U2-23).

    ``id == world_id``; the node also carries ``world_id`` so ``delete_world`` removes it.
    """

    id: str
    name: str
    description: str | None = None
    format_version: int = 1
    updated_at: datetime = Field(default_factory=utcnow)
    last_writer: WorldWriter = "build"


class NPC(LocusModel):
    """A canonical inhabitant of a region (FR-F1). ``:NPC`` node + ``LIVES_IN`` edge."""

    id: str = Field(default_factory=new_id)
    world_id: str
    name: str
    role: str
    description: str
    home_region_id: str  # LIVES_IN target (BR-U2-12)
    traits: list[str] = Field(default_factory=list)  # short English tags (Q7)
    provenance: Provenance


class EventSeed(LocusModel):
    """A world's "event that could happen" (U8, FD domain-entities §2, Q2=A).

    World data: saved with the world (World File ``event_seeds``, an ``EventSeed`` graph
    node), and started by the GM in a session as an ACTIVE event without an LLM. The
    region is referenced by id; a region delete removes its seeds (BR-U8-14).
    """

    id: str = Field(default_factory=new_id)
    world_id: str
    region_id: str
    title: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    category: EventCategory
    magnitude: float = Field(ge=0.0, le=1.0)
    lifecycle: EventLifecycle | None = None  # None: the category default at start
    provenance: Provenance
