"""Shared composition: connections and providers every boundary may need.

``assemble_shared`` connects only the resources that are switched on, so a
caller that needs just SQL (``init-schema --play``) never touches Neo4j, and a
caller that needs just the graph never creates an LLM provider. It does **not**
initialize any schema — each boundary owns its ``ensure_*_schema``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy.engine import Engine

from locus.shared.config import Settings, get_settings
from locus.shared.llm.base import EmbeddingProvider, LLMProvider, VLMProvider
from locus.shared.llm.factory import ProviderFactory
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.neo4j_repo import Neo4jGraphRepository
from locus.shared.storage.opensearch_repo import OpenSearchRepository
from locus.shared.storage.sql import make_engine

logger = logging.getLogger(__name__)


@dataclass
class SharedContainer:
    """Resources shared by the boundaries. ``None`` = not requested / not connected."""

    settings: Settings
    graph: GraphRepository | None = None
    search: SearchRepository | None = None
    llm: LLMProvider | None = None
    vlm: VLMProvider | None = None
    embedding: EmbeddingProvider | None = None
    sql_engine: Engine | None = None
    factory: ProviderFactory | None = field(default=None, repr=False)

    def close(self) -> None:
        """Release connections and engines (idempotent)."""
        for repo in (self.graph, self.search):
            if repo is not None:
                try:
                    repo.disconnect()
                except Exception:  # pragma: no cover - best effort
                    pass
        if self.sql_engine is not None:
            self.sql_engine.dispose()
        self.graph = self.search = None
        self.sql_engine = None


def assemble_shared(
    settings: Settings | None = None,
    *,
    graph: bool = True,
    search: bool = True,
    llm: bool = True,
    sql: bool = True,
    strict: bool = True,
) -> SharedContainer:
    """Connect the requested resources and return them in a ``SharedContainer``.

    ``strict=True`` (CLI): the first failure closes what was already opened and
    re-raises, so a misconfiguration is loud. ``strict=False`` (API startup): a
    failing resource is logged and left ``None`` so the boundaries that do not
    need it can still assemble (per-boundary degrade, FR-A3; review U1 #4).
    """
    s = settings or get_settings()
    c = SharedContainer(settings=s)

    def _step(name: str, fn) -> None:
        try:
            fn()
        except Exception:
            if strict:
                c.close()
                raise
            logger.warning(
                "shared resource %s unavailable; continuing without it", name, exc_info=True
            )

    def _graph() -> None:
        repo = Neo4jGraphRepository(
            uri=s.neo4j_uri, user=s.neo4j_user, password=s.neo4j_password.get_secret_value()
        )
        repo.connect()
        c.graph = repo

    def _search() -> None:
        srepo = OpenSearchRepository(
            url=s.opensearch_url, index=s.opensearch_index, vector_dimension=s.embedding_dimension
        )
        srepo.connect()
        c.search = srepo

    def _llm() -> None:
        factory = ProviderFactory(s)
        c.factory = factory
        c.llm = factory.llm()
        c.vlm = factory.vlm()
        c.embedding = factory.embedding()

    def _sql() -> None:
        if s.session_db_url:
            c.sql_engine = make_engine(s.session_db_url)

    if graph:
        _step("graph", _graph)
    if search:
        _step("search", _search)
    if llm:
        _step("llm", _llm)
    if sql:
        _step("sql", _sql)
    return c
