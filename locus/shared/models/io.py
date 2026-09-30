"""Aggregate and I/O models for Locus pipelines and queries."""

from __future__ import annotations

from pydantic import Field, PrivateAttr, model_validator

from locus.shared.models.graph import (
    NPC,
    ConnectionEdge,
    Entity,
    Knowledge,
    LocusModel,
    Region,
    Relation,
    ScopeLink,
    WikiPrior,
    WikiPriorLink,
    WorldMeta,
)
from locus.shared.models.reports import BuildWarning
from locus.shared.models.util import index_by_name


class IngestionResult(LocusModel):
    """Normalized output of the ingestion pipeline (FR-A)."""

    world_id: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    region_hints: list[Region] = Field(default_factory=list)
    knowledge: list[Knowledge] = Field(default_factory=list)
    low_confidence_item_ids: list[str] = Field(default_factory=list)
    # severity=error: an input could not be read at all; warning: an item was rejected (BR-U2-10/13)
    warnings: list[BuildWarning] = Field(default_factory=list)
    entity_id_map: dict[str, str] = Field(
        default_factory=dict
    )  # merged-away id -> canonical id (A2)


class RegionTopology(LocusModel):
    """Region nodes + connection edges (FR-B)."""

    world_id: str
    regions: list[Region] = Field(default_factory=list)
    connections: list[ConnectionEdge] = Field(default_factory=list)


class KnowledgeGraph(LocusModel):
    """Entities, relations, knowledge and their region scoping (FR-C/D)."""

    world_id: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    knowledge: list[Knowledge] = Field(default_factory=list)
    scopes: list[ScopeLink] = Field(default_factory=list)
    priors: list[WikiPrior] = Field(default_factory=list)  # this world's commonsense priors (U2)
    prior_links: list[WikiPriorLink] = Field(default_factory=list)
    # entities that could not be connected to any region/entity (augmentation candidates, BR-B8)
    unconnected_entity_ids: list[str] = Field(default_factory=list)
    # knowledge that resolved to no region and is not global (RE A4 / BR-U2-14); stored, editor assigns
    unscoped_knowledge_ids: list[str] = Field(default_factory=list)


class WorldSnapshot(LocusModel):
    """Everything the loader reads for one world; the unit the ``WorldCache`` holds (U2 K3/K4).

    Shared, treated as immutable (BR-U2-18). Derived indexes are computed once.
    """

    world_id: str
    meta: WorldMeta | None = None
    kg: KnowledgeGraph
    topo: RegionTopology
    npcs: list[NPC] = Field(default_factory=list)
    load_warnings: list[BuildWarning] = Field(default_factory=list)  # skipped nodes (BR-U2-16)

    _regions_by_id: dict[str, Region] = PrivateAttr(default_factory=dict)
    _regions_by_name: dict[str, list[Region]] = PrivateAttr(default_factory=dict)
    _npcs_by_region: dict[str, list[NPC]] = PrivateAttr(default_factory=dict)

    @model_validator(mode="after")
    def _index(self) -> "WorldSnapshot":
        self._regions_by_id = {r.id: r for r in self.topo.regions}
        self._regions_by_name = index_by_name(self.topo.regions)
        by_region: dict[str, list[NPC]] = {}
        for npc in self.npcs:
            by_region.setdefault(npc.home_region_id, []).append(npc)
        self._npcs_by_region = by_region
        return self

    @property
    def regions_by_id(self) -> dict[str, Region]:
        return self._regions_by_id

    @property
    def regions_by_name(self) -> dict[str, list[Region]]:
        return self._regions_by_name

    @property
    def npcs_by_region(self) -> dict[str, list[NPC]]:
        return self._npcs_by_region

    @property
    def unscoped_knowledge_ids(self) -> list[str]:
        return self.kg.unscoped_knowledge_ids


class SearchDoc(LocusModel):
    """A document indexed in OpenSearch (FD1-Q5=A)."""

    id: str
    world_id: str
    label: str  # "Knowledge" | "Entity" | "WikiPrior" | "NPC"
    text: str
    embedding: list[float] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)


class SearchHit(LocusModel):
    """A hybrid-search result."""

    id: str
    world_id: str
    label: str
    text: str
    score: float
    meta: dict = Field(default_factory=dict)


class KnowledgeView(LocusModel):
    """A single knowledge item as seen from a querying region."""

    knowledge_id: str
    statement: str
    title: str | None = None  # one-line label for UI/export (FR-IM3.1)
    scope_type: str  # ScopeType value
    is_hearsay: bool = False  # canonical knowledge reached only over a weak path
    confidence: float
    path_decay: float | None = None  # hearsay only: 1 - best path weight
    distortion: float | None = None  # play-layer rumor views only: the rumor's distortion degree
    source: str | None = None  # provenance source, or "rumor" / "rumor:promoted" for play views
    region_id: str | None = None  # origin region (for shared/unique classification)


class ConsensusView(LocusModel):
    """Computed consensus for a region (FR-D)."""

    world_id: str
    region_id: str
    direct: list[KnowledgeView] = Field(default_factory=list)
    inherited: list[KnowledgeView] = Field(default_factory=list)
    global_knowledge: list[KnowledgeView] = Field(default_factory=list)
    propagated: list[KnowledgeView] = Field(default_factory=list)
    hearsay: list[KnowledgeView] = Field(default_factory=list)  # weak-path knowledge
    unknown_count: int = 0


class QueryResult(LocusModel):
    """API response for 'knowledge known by NPCs in region X' (FR-H)."""

    world_id: str
    region_id: str
    items: list[KnowledgeView] = Field(default_factory=list)
    shared_ids: list[str] = Field(default_factory=list)
    unique_ids: list[str] = Field(default_factory=list)


class RegionDiff(LocusModel):
    """Comparison of two regions' knowledge (shared vs unique, FR-H2/SC-2)."""

    world_id: str
    region_a: str
    region_b: str
    shared_ids: list[str] = Field(default_factory=list)
    only_a_ids: list[str] = Field(default_factory=list)
    only_b_ids: list[str] = Field(default_factory=list)


class RegionBrief(LocusModel):
    """Prompt-ready summary of one region (U2 K5, FR-D2): name, place in the hierarchy,
    description and the best-known DIRECT knowledge titles."""

    region_id: str
    name: str
    level: str
    level_path: list[str] = Field(default_factory=list)  # top ancestor ... own name
    description: str | None = None
    top_knowledge: list[str] = Field(default_factory=list)
