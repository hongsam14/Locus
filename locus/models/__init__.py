"""Locus domain models (Pydantic v2)."""

from __future__ import annotations

from .enums import (
    ConnectionKind,
    EntityType,
    PriorType,
    RegionLevel,
    ScopeType,
    SourceKind,
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
    Rumor,
    ScopeLink,
    WikiPrior,
    World,
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
    # graph
    "ConnectionEdge",
    "Coord",
    "Entity",
    "Knowledge",
    "LocusModel",
    "Provenance",
    "Region",
    "Relation",
    "Rumor",
    "ScopeLink",
    "WikiPrior",
    "World",
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
