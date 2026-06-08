"""WorldLoader — reconstruct in-memory KnowledgeGraph + RegionTopology (U8, FD8-Q1=A)."""

from __future__ import annotations

from ..models import KnowledgeGraph, RegionTopology
from ..storage import graph_mapping as gm
from ..storage.base import GraphRepository


class WorldLoader:
    def __init__(self, graph_repo: GraphRepository) -> None:
        self._g = graph_repo

    def load(self, world_id: str) -> tuple[KnowledgeGraph, RegionTopology]:
        regions = [gm.node_to_region(n) for n in self._g.find_nodes(world_id, "Region")]
        entities = [gm.node_to_entity(n) for n in self._g.find_nodes(world_id, "Entity")]
        knowledge = [gm.node_to_knowledge(n) for n in self._g.find_nodes(world_id, "Knowledge")]
        rumors = [gm.node_to_rumor(n) for n in self._g.find_nodes(world_id, "Rumor")]

        edges = self._g.get_edges(world_id)
        connections = [gm.edge_to_connection(e) for e in edges if e.type == "CONNECTED_TO"]
        scopes = [gm.edge_to_scope(e) for e in edges if e.type == "SCOPED_TO"]

        kg = KnowledgeGraph(
            world_id=world_id,
            entities=entities,
            knowledge=knowledge,
            rumors=rumors,
            scopes=scopes,
        )
        topo = RegionTopology(world_id=world_id, regions=regions, connections=connections)
        return kg, topo
