"""WorldCatalog — the stored worlds for the ``/`` list (U3, BLM §1.8, US-6.4).

Two small reads per world (its ``WorldMeta`` and its regions), no snapshot load
(nfr §1 NFR-3 ④). The router adds each world's open session count from play.
"""

from __future__ import annotations

from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import GraphRepository
from locus.world.editor.models import WorldSummary


class WorldCatalog:
    def __init__(self, graph: GraphRepository) -> None:
        self._graph = graph

    def list_worlds(self) -> list[WorldSummary]:
        """Every stored world with its meta (BR-U2-24); pre-U2 worlds show ``name=id``."""
        out: list[WorldSummary] = []
        for wid in self._graph.list_world_ids():
            metas = self._graph.find_nodes(wid, "WorldMeta")
            meta = gm.node_to_worldmeta(metas[0]) if metas else None
            out.append(
                WorldSummary(
                    id=wid,
                    name=meta.name if meta else wid,
                    description=meta.description if meta else None,
                    region_count=len(self._graph.find_nodes(wid, "Region")),
                    updated_at=meta.updated_at.isoformat() if meta else None,
                    last_writer=meta.last_writer if meta else None,
                )
            )
        return out
