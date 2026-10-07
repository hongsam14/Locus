"""SchemaInitializer — bootstrap Neo4j constraints/indexes + OpenSearch index.

Idempotent: safe to run on every app start or via ``locus init-schema``.
Operates against the repository ports so it is adapter-agnostic.
"""

from __future__ import annotations

from locus.shared.storage.base import GraphRepository, SearchRepository


class SchemaInitializer:
    def __init__(self, graph: GraphRepository, search: SearchRepository) -> None:
        self._graph = graph
        self._search = search

    def initialize(self) -> None:
        """Create all graph constraints/indexes and the search index."""
        self._graph.ensure_schema()
        self._search.ensure_index()


def ensure_world_schema(graph, search) -> None:
    """Idempotent canonical (Neo4j + OpenSearch) schema initialization.

    Function form of ``SchemaInitializer`` so each boundary's ``ensure_*_schema``
    reads alike (world / play / localization) and the CLI can run them one by one.
    """
    SchemaInitializer(graph, search).initialize()
