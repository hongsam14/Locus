"""WikiAdmin — edit / list a world's Common-sense Wiki priors (US-5.2/5.3).

Each prior carries its own ``world_id`` (no reserved partition); designers may
add/edit priors per world (FR-IM1.3, CL3=C).
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import WikiPrior
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.persistence import touch_world_meta


class WikiAdmin:
    def __init__(
        self,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        embedding: EmbeddingProvider | None = None,
        *,
        cache: SnapshotCache | None = None,
    ) -> None:
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding
        self._cache = cache  # priors are canonical: invalidate after writes (BR-U2-17)

    def upsert_prior(self, prior: WikiPrior) -> WikiPrior:
        """Create or update a prior (idempotent by id), keeping provenance."""
        try:
            self._graph.upsert_nodes([gm.wikiprior_to_node(prior)])
            doc = gm.wikiprior_doc(prior)
            if doc.text.strip():
                if self._embedding is not None:
                    try:
                        doc.embedding = self._embedding.embed([doc.text])[0]
                    except Exception:
                        pass
                self._search.index([doc])
        finally:  # a canonical write: touch meta + invalidate even if indexing failed
            try:
                touch_world_meta(self._graph, prior.world_id, last_writer="edit")
            finally:
                if self._cache is not None:
                    self._cache.invalidate(prior.world_id)
        return prior

    def list_priors(self, world_id: str) -> list:
        """Return WikiPrior nodes stored in ``world_id``."""
        return self._graph.find_nodes(world_id, "WikiPrior")
