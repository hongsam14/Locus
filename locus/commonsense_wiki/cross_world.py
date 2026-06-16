"""CrossWorldWikiExplorer — designer-only cross-world prior reference (FR-IM1.4).

Scoped strictly to the designer/authoring path: it is NEVER used by the build
pipeline or NPC runtime query, which stay single-world (BR-A9). Read-through
only — it returns other worlds' priors for reference; nothing is copied into the
current world (BR-A10).
"""

from __future__ import annotations

from ..llm.base import EmbeddingProvider
from ..models import PriorType, Provenance, SourceKind, WikiDomain, WikiPrior
from ..storage import graph_mapping as gm
from ..storage.base import GraphRepository, SearchRepository


class CrossWorldWikiExplorer:
    def __init__(
        self,
        graph: GraphRepository,
        search: SearchRepository,
        embedding: EmbeddingProvider | None = None,
    ) -> None:
        self._graph = graph
        self._search = search
        self._embedding = embedding

    def world_domains(self, world_id: str) -> set[WikiDomain]:
        """A world's domain tags = union of its WikiPriors' domains (BR-A11)."""
        domains: set[WikiDomain] = set()
        for node in self._graph.find_nodes(world_id, "WikiPrior"):
            for d in gm.node_to_wikiprior(node).domains:
                domains.add(WikiDomain(d))
        return domains

    def search_related_priors(
        self, world_id: str, query: str | None = None, k: int = 10
    ) -> list[WikiPrior]:
        """Find priors in OTHER worlds whose domains overlap this world's (FR-IM1.4).

        Global (world_id=None) domain-filtered search; the current world is
        excluded. Read-through only (BR-A10).
        """
        domains = self.world_domains(world_id)
        if not domains:
            return []
        embedding = None
        if query and self._embedding is not None:
            embedding = self._embedding.embed([query])[0]
        hits = self._search.hybrid_search(
            world_id=None,
            query_text=query or "",
            query_embedding=embedding,
            k=k,
            filters={"label": "WikiPrior", "domains": [str(d) for d in domains]},
        )
        out: list[WikiPrior] = []
        for hit in hits:
            if hit.world_id == world_id:
                continue  # exclude own world
            out.append(self._hit_to_prior(hit))
        return out

    @staticmethod
    def _hit_to_prior(hit) -> WikiPrior:
        meta = hit.meta or {}
        return WikiPrior(
            id=hit.id,
            world_id=hit.world_id,
            prior_type=meta.get("prior_type", PriorType.FACT),
            condition=meta.get("condition", hit.text),
            effect=meta.get("effect", ""),
            domains=meta.get("domains", []),
            description=meta.get("description"),
            confidence=meta.get("confidence", 1.0),
            provenance=Provenance(
                source=SourceKind.INPUT, generated_by="wiki", note="cross-world reference"
            ),
        )
