"""Locus domain models (Pydantic v2)."""

from __future__ import annotations

from .enums import (
    ConnectionKind,
    EntityType,
    PriorType,
    RegionLevel,
    ScopeType,
    SourceKind,
    WikiDomain,
)
from .graph import (
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
    World,
    fallback_title,
    new_id,
)
from .io import (
    ConsensusView,
    IngestionResult,
    KnowledgeGraph,
    KnowledgeView,
    QueryResult,
    RegionDiff,
    RegionTopology,
    SearchDoc,
    SearchHit,
)
from .reports import BuildReport, BuildWarning, GraphSummary, WikiBuildReport

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
    "World",
    "fallback_title",
    "new_id",
    # io
    "ConsensusView",
    "IngestionResult",
    "KnowledgeGraph",
    "KnowledgeView",
    "QueryResult",
    "RegionDiff",
    "RegionTopology",
    "SearchDoc",
    "SearchHit",
    # reports
    "BuildReport",
    "BuildWarning",
    "WikiBuildReport",
    "GraphSummary",
]
