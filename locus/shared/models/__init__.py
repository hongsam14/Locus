"""Locus domain models (Pydantic v2)."""

from __future__ import annotations

from locus.shared.models.enums import (
    ConnectionKind,
    EntityType,
    PriorType,
    RegionLevel,
    ScopeType,
    SourceKind,
    WikiDomain,
)
from locus.shared.models.graph import (
    NPC,
    ConnectionEdge,
    Coord,
    Entity,
    Knowledge,
    LocusModel,
    Provenance,
    Region,
    Relation,
    ScopeLink,
    WikiPrior,
    WikiPriorLink,
    WorldMeta,
    fallback_title,
    new_id,
)
from locus.shared.models.io import (
    ConsensusView,
    IngestionResult,
    KnowledgeGraph,
    KnowledgeView,
    QueryResult,
    RegionBrief,
    RegionDiff,
    RegionTopology,
    SearchDoc,
    SearchHit,
    WorldSnapshot,
)
from locus.shared.models.reports import BuildReport, BuildWarning, GraphSummary, ImportReport

__all__ = [
    # enums
    "ConnectionKind",
    "EntityType",
    "PriorType",
    "RegionLevel",
    "ScopeType",
    "SourceKind",
    "WikiDomain",
    # graph
    "NPC",
    "ConnectionEdge",
    "Coord",
    "Entity",
    "Knowledge",
    "LocusModel",
    "Provenance",
    "Region",
    "Relation",
    "ScopeLink",
    "WikiPrior",
    "WikiPriorLink",
    "WorldMeta",
    "fallback_title",
    "new_id",
    # io
    "ConsensusView",
    "IngestionResult",
    "KnowledgeGraph",
    "KnowledgeView",
    "QueryResult",
    "RegionBrief",
    "RegionDiff",
    "RegionTopology",
    "SearchDoc",
    "SearchHit",
    "WorldSnapshot",
    # reports
    "BuildReport",
    "BuildWarning",
    "GraphSummary",
    "ImportReport",
]
