"""Storage layer: ports + Neo4j / OpenSearch adapters (AD-Q5=A)."""

from .base import (
    Edge,
    GraphRepository,
    Node,
    Path,
    SearchRepository,
    TraversalSpec,
)
from .neo4j_repo import Neo4jGraphRepository
from .opensearch_repo import OpenSearchRepository, build_search_body, index_mapping
from .schema import SchemaInitializer

__all__ = [
    "Edge",
    "GraphRepository",
    "Node",
    "Path",
    "SearchRepository",
    "TraversalSpec",
    "Neo4jGraphRepository",
    "OpenSearchRepository",
    "build_search_body",
    "index_mapping",
    "SchemaInitializer",
]
