"""Aggregate and I/O models for Locus pipelines and queries."""

from __future__ import annotations

from pydantic import Field

from .graph import (
    ConnectionEdge,
    Entity,
    Knowledge,
    LocusModel,
    Region,
    Relation,
    Rumor,
    ScopeLink,
)


class IngestionResult(LocusModel):
    """Normalized output of the ingestion pipeline (FR-A)."""

    world_id: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    region_hints: list[Region] = Field(default_factory=list)
    knowledge: list[Knowledge] = Field(default_factory=list)
    low_confidence_item_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RegionTopology(LocusModel):
    """Region nodes + connection edges (FR-B)."""

    world_id: str
    regions: list[Region] = Field(default_factory=list)
    connections: list[ConnectionEdge] = Field(default_factory=list)


class KnowledgeGraph(LocusModel):
    """Entities, relations, knowledge, rumors and their region scoping (FR-C/D)."""

    world_id: str
    entities: list[Entity] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    knowledge: list[Knowledge] = Field(default_factory=list)
    rumors: list[Rumor] = Field(default_factory=list)
    scopes: list[ScopeLink] = Field(default_factory=list)


class SearchDoc(LocusModel):
    """A document indexed in OpenSearch (FD1-Q5=A)."""

    id: str
    world_id: str
    label: str  # "Knowledge" | "Entity" | "WikiPrior" | "Rumor"
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
    scope_type: str  # ScopeType value
    is_rumor: bool = False
    confidence: float
    distortion_degree: float | None = None  # set for rumor views (= 1 - path_weight)
    source: str | None = None  # provenance source
    region_id: str | None = None  # origin region (for shared/unique classification)


class ConsensusView(LocusModel):
    """Computed consensus for a region (FR-D)."""

    world_id: str
    region_id: str
    direct: list[KnowledgeView] = Field(default_factory=list)
    inherited: list[KnowledgeView] = Field(default_factory=list)
    global_knowledge: list[KnowledgeView] = Field(default_factory=list)
    propagated: list[KnowledgeView] = Field(default_factory=list)
    rumors: list[KnowledgeView] = Field(default_factory=list)
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
