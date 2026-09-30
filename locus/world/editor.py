"""WorldEditor — authoring edits to a world graph (U9 Q2=C; U2 BR-U2-17/23).

Every write ends with ``cache.invalidate(world_id)`` so the next read sees it, and
touches the world's ``WorldMeta`` (``last_writer="edit"``) when one exists.
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import Knowledge, Region
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.shared.storage.persistence import touch_world_meta


class WorldEditor:
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
        self._cache = cache

    def upsert_region(self, region: Region) -> Region:
        try:
            self._graph.upsert_nodes([gm.region_to_node(region)])
        finally:
            self._written(region.world_id)
        return region

    def upsert_knowledge(self, knowledge: Knowledge) -> Knowledge:
        try:
            self._graph.upsert_nodes([gm.knowledge_to_node(knowledge)])
            doc = gm.knowledge_doc(knowledge)
            if doc.text.strip():
                if self._embedding is not None:
                    try:
                        doc.embedding = self._embedding.embed([doc.text])[0]
                    except Exception:
                        pass
                self._search.index([doc])
        finally:
            self._written(knowledge.world_id)  # graph may have changed even if indexing failed
        return knowledge

    def delete_node(self, world_id: str, node_id: str) -> list[str]:
        """Delete a node. Deleting a Region also deletes the NPCs living there (their
        ``home_region_id`` must resolve, BR-U2-12). Returns every deleted node id."""
        deleted = [node_id]
        try:
            node = self._graph.get_node(world_id, node_id)
            if node is not None and node.label == "Region":
                for npc in self._graph.find_nodes(world_id, "NPC", {"home_region_id": node_id}):
                    self._graph.delete_node(world_id, npc.id)
                    deleted.append(npc.id)
            self._graph.delete_node(world_id, node_id)
        finally:
            self._written(world_id)
        return deleted

    # ------------------------------------------------------------------ #
    def _written(self, world_id: str) -> None:
        try:
            touch_world_meta(self._graph, world_id, last_writer="edit")
        finally:
            if self._cache is not None:
                self._cache.invalidate(world_id)
