"""WikiAdmin — edit / list a world's Common-sense Wiki priors (US-5.2/5.3).

Each prior carries its own ``world_id`` (no reserved partition); designers may
add/edit priors per world (FR-IM1.3, CL3=C).
"""

from __future__ import annotations

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
        """Create or update a prior (idempotent by id), keeping provenance."""
        self._graph.upsert_nodes([gm.wikiprior_to_node(prior)])
        doc = gm.wikiprior_doc(prior)
        if doc.text.strip():
            if self._embedding is not None:
                try:
                    doc.embedding = self._embedding.embed([doc.text])[0]
                except Exception:
                    pass
            self._search.index([doc])
        return prior

    def list_priors(self, world_id: str) -> list:
        """Return WikiPrior nodes stored in ``world_id``."""
        return self._graph.find_nodes(world_id, "WikiPrior")
