"""Storage that counts every write and can cut the n-th one (U3 TP-U3-2a, NFR R-02).

``Meter`` is shared by the graph and the search fakes so their writes interleave in one
order. A cut raises once, before the write happens; later writes go through, as a
retry would see them.
"""

from __future__ import annotations

import json

from locus.knowledge.cache import WorldCache
from locus.knowledge.loader import WorldLoader
from locus.world.editor import Editors
from locus.world.worldfile import WorldFile
from locus.world.worldfile.export import WorldFileExporter
from locus.world.worldfile.import_ import WorldFileImporter
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


class Meter:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.cut_at: int | None = None

    def hit(self, name: str) -> None:
        n = len(self.calls)
        self.calls.append(name)
        if self.cut_at is not None and n == self.cut_at:
            self.cut_at = None
            raise RuntimeError(f"cut at write {n} ({name})")


class MeteredGraph(InMemoryGraphRepository):
    def __init__(self, meter: Meter) -> None:
        super().__init__()
        self.meter = meter

    def upsert_nodes(self, nodes):
        self.meter.hit("upsert_nodes")
        super().upsert_nodes(nodes)

    def replace_nodes(self, nodes):
        self.meter.hit("replace_nodes")
        super().replace_nodes(nodes)

    def upsert_edges(self, edges):
        self.meter.hit("upsert_edges")
        super().upsert_edges(edges)

    def delete_edges(self, world_id, edges):
        self.meter.hit("delete_edges")
        return super().delete_edges(world_id, edges)

    def delete_node(self, world_id, node_id):
        self.meter.hit("delete_node")
        super().delete_node(world_id, node_id)


class MeteredSearch(InMemorySearchRepository):
    def __init__(self, meter: Meter) -> None:
        super().__init__()
        self.meter = meter

    def index(self, docs):
        self.meter.hit("index")
        super().index(docs)

    def delete(self, world_id, doc_ids):
        self.meter.hit("delete")
        return super().delete(world_id, doc_ids)


class Stack:
    """A world in metered in-memory storage, behind the real editor classes."""

    def __init__(self, file: WorldFile | None = None, world_id: str = "w") -> None:
        self.meter = Meter()
        self.graph = MeteredGraph(self.meter)
        self.search = MeteredSearch(self.meter)
        self.cache = WorldCache(WorldLoader(self.graph))
        self.exporter = WorldFileExporter(self.cache)
        self.importer = WorldFileImporter(
            self.graph, self.search, None, self.cache, exporter=self.exporter
        )
        if file is not None:
            report = self.importer.import_(world_id, file)
            assert report.ok, report.warnings
        self.meter.calls.clear()
        self.editors = Editors.assemble(self.graph, self.search, cache=self.cache)

    def state(self) -> tuple:
        """Everything stored, WorldMeta aside (its timestamp moves on every write)."""
        nodes = sorted(
            (n.label, n.id, json.dumps(n.properties, sort_keys=True, default=str))
            for n in self.graph._nodes.values()
            if n.label != "WorldMeta"
        )
        edges = sorted(
            (
                e.type,
                e.source_id,
                e.target_id,
                json.dumps(e.properties, sort_keys=True, default=str),
            )
            for e in self.graph._edges.values()
        )
        return nodes, edges, sorted(self.search.docs)

    def dangling(self) -> list[str]:
        """Id properties and edge ends that point at no stored node."""
        ids = {n.id for n in self.graph._nodes.values()}
        bad = [
            f"{n.label}.{key}={n.properties[key]}"
            for n in self.graph._nodes.values()
            for key in ("parent_id", "located_in", "home_region_id", "region_id")  # +seeds (U8)
            if n.properties.get(key) and n.properties[key] not in ids
        ]
        bad += [
            f"{e.type}:{e.source_id}->{e.target_id}"
            for e in self.graph._edges.values()
            if e.source_id not in ids or e.target_id not in ids
        ]
        return bad
