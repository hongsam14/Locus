"""Storage layer: ports + Neo4j / OpenSearch adapters (AD-Q5=A)."""

from locus.shared.storage.base import (
    ConstraintViolation,
    Edge,
    GraphRepository,
    Node,
    SearchRepository,
)
from locus.shared.storage.neo4j_repo import Neo4jGraphRepository
from locus.shared.storage.opensearch_repo import (
    OpenSearchRepository,
    build_search_body,
    index_mapping,
)
from locus.shared.storage.schema import SchemaInitializer

__all__ = [
    "ConstraintViolation",
    "Edge",
    "GraphRepository",
    "Node",
    "SearchRepository",
    "Neo4jGraphRepository",
    "OpenSearchRepository",
    "build_search_body",
    "index_mapping",
    "SchemaInitializer",
]
