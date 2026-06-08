"""WikiAdmin — edit / list Common-sense Wiki priors (U6, US-5.2/5.3)."""

from __future__ import annotations

from .. import REALWORLD_WORLD_ID
from ..llm.base import EmbeddingProvider
from ..models import WikiPrior
from ..storage import graph_mapping as gm
from ..storage.base import GraphRepository, SearchRepository


class WikiAdmin:
    def __init__(
        self,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        embedding: EmbeddingProvider | None = None,
    ) -> None:
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding

    def upsert_prior(self, prior: WikiPrior) -> WikiPrior:
        """Create or update a prior (idempotent by id), keeping provenance (BR-U6-9)."""
        self._graph.upsert_nodes([gm.wikiprior_to_node(prior, REALWORLD_WORLD_ID)])
        doc = gm.wikiprior_doc(prior, REALWORLD_WORLD_ID)
        if doc.text.strip():
            if self._embedding is not None:
                try:
                    doc.embedding = self._embedding.embed([doc.text])[0]
                except Exception:
                    pass
            self._search.index([doc])
        return prior

    def list_priors(self) -> list:
        """Return WikiPrior nodes stored in the real-world partition."""
        return self._graph.find_nodes(REALWORLD_WORLD_ID, "WikiPrior")
