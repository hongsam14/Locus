"""WikiAdmin — edit / list a world's Common-sense Wiki priors (US-5.2/5.3).

Each prior carries its own ``world_id`` (no reserved partition); designers may
add/edit priors per world (FR-IM1.3, CL3=C).

U3 (Q4=A, US-2.8): the wiki tab reads each prior with what cites it, and the cited ids
the world does not hold ("저장되지 않은 근거"). The citation maps are pure functions over
the world snapshot so the editor's connection view uses the same answer.
"""

from __future__ import annotations

from collections.abc import Iterable

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import WikiPrior, WorldSnapshot
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.persistence import touch_world_meta
from locus.world.refs import ConnectionKey, NameRef
from locus.world.wiki.schemas import BrokenRef, PriorRefView, PriorUsage


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
        # the editors' delete rule (U3 review C3); imported here: the editor package
        # imports this module for its citation maps
        from locus.world.editor.writes import EditorWrites

        self._writes = EditorWrites(graph_repo, search_repo, embedding, cache=cache)

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

    def list_priors(self, world_id: str) -> list[WikiPrior]:
        """The priors stored in ``world_id`` (U3: models, was raw nodes), by id."""
        nodes = self._graph.find_nodes(world_id, "WikiPrior")
        return sorted((gm.node_to_wikiprior(n) for n in nodes), key=lambda p: p.id)

    def prior_refs(self, world_id: str) -> list[PriorUsage]:
        """Each stored prior with the connections and knowledge that cite it (BR-U3-31)."""
        return usages(self._snapshot(world_id), self.list_priors(world_id))

    def broken_refs(self, world_id: str) -> list[BrokenRef]:
        """Cited prior ids the world does not hold (BR-U3-31, "저장되지 않은 근거")."""
        return broken(self._snapshot(world_id), self.list_priors(world_id))

    def delete_prior(self, world_id: str, prior_id: str) -> None:
        """Delete a prior and its search document; what cites it is left for DANGLING
        (BLM §5.2). Graph first, then search; a prior already gone still has its search
        document removed before the ``LookupError`` so a retry cleans up (NFR R-01), and a
        node of another kind under that id keeps its document (U3 review S12)."""
        if not self._writes.delete_held(world_id, prior_id, "WikiPrior"):
            raise LookupError(f"wiki prior not found: {prior_id}")

    def _snapshot(self, world_id: str) -> WorldSnapshot:
        if self._cache is None:
            raise RuntimeError("WikiAdmin needs the world cache to read references")
        return self._cache.get(world_id)


# --------------------------------------------------------------------------- #
# Pure citation maps (shared with the editor's connection view)
# --------------------------------------------------------------------------- #
def prior_ref_view(prior_id: str, priors_by_id: dict[str, WikiPrior]) -> PriorRefView:
    prior = priors_by_id.get(prior_id)
    if prior is None:
        return PriorRefView(prior_id=prior_id, broken=True)
    return PriorRefView(prior_id=prior_id, condition=prior.condition, effect=prior.effect)


def _citations(
    snapshot: WorldSnapshot,
) -> tuple[dict[str, list[ConnectionKey]], dict[str, list[NameRef]]]:
    """prior id -> connection keys (one per pair) and knowledge that cite it."""
    conns: dict[str, list[ConnectionKey]] = {}
    for edge in snapshot.topo.connections:
        if edge.wiki_prior_ref:
            key = ConnectionKey.of(edge)
            bucket = conns.setdefault(edge.wiki_prior_ref, [])
            if key not in bucket:
                bucket.append(key)
    knowledge: dict[str, list[NameRef]] = {}
    for k in snapshot.kg.knowledge:
        for pid in dict.fromkeys(k.derived_from_prior_ids):
            knowledge.setdefault(pid, []).append(NameRef(id=k.id, name=k.title or k.id))
    return conns, knowledge


def usages(snapshot: WorldSnapshot, priors: Iterable[WikiPrior]) -> list[PriorUsage]:
    conns, knowledge = _citations(snapshot)
    return [
        PriorUsage(prior=p, connections=conns.get(p.id, []), knowledge=knowledge.get(p.id, []))
        for p in priors
    ]


def broken(snapshot: WorldSnapshot, priors: Iterable[WikiPrior]) -> list[BrokenRef]:
    held = {p.id for p in priors}
    conns, knowledge = _citations(snapshot)
    cited = [pid for pid in dict.fromkeys([*conns, *knowledge]) if pid not in held]
    return [
        BrokenRef(ref_id=pid, connections=conns.get(pid, []), knowledge=knowledge.get(pid, []))
        for pid in sorted(cited)
    ]
