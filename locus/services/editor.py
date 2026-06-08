"""GraphEditor — authoring edits to a world graph (U9, Q2=C)."""

from __future__ import annotations

from ..llm.base import EmbeddingProvider
from ..models import Knowledge, Region
from ..storage import graph_mapping as gm
from ..storage.base import GraphRepository, SearchRepository


class GraphEditor:
    def __init__(
        self,
        graph_repo: GraphRepository,
        search_repo: SearchRepository,
        embedding: EmbeddingProvider | None = None,
    ) -> None:
        self._graph = graph_repo
        self._search = search_repo
        self._embedding = embedding

    def upsert_region(self, region: Region) -> Region:
        self._graph.upsert_nodes([gm.region_to_node(region)])
        return region

    def upsert_knowledge(self, knowledge: Knowledge) -> Knowledge:
        self._graph.upsert_nodes([gm.knowledge_to_node(knowledge)])
        doc = gm.knowledge_doc(knowledge)
        if doc.text.strip():
            if self._embedding is not None:
                try:
                    doc.embedding = self._embedding.embed([doc.text])[0]
                except Exception:
                    pass
            self._search.index([doc])
        return knowledge

    def delete_node(self, world_id: str, node_id: str) -> None:
        self._graph.delete_node(world_id, node_id)
