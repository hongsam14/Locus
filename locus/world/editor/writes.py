"""EditorWrites — the writes and checks every editor class shares (U3, BLM §1.1).

Editor writes replace a node's properties whole (BR-U3-1); build and import keep the
merge write. Every operation ends in ``written``: the world's ``WorldMeta`` is touched
and the snapshot cache invalidated even when a later write failed (BR-U3-4, review #12).
There is no graph transaction (NFR N3-2): each operation orders its writes so a cut
leaves no dangling reference and a retry finishes the job (BR-U3-8).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.models import Region, SearchDoc, WorldSnapshot
from locus.shared.storage.base import GraphRepository, Node, SearchRepository
from locus.shared.storage.persistence import touch_world_meta


class EditorWrites:
    def __init__(
        self,
        graph: GraphRepository,
        search: SearchRepository,
        embedding: EmbeddingProvider | None = None,
        *,
        cache: SnapshotCache | None = None,
    ) -> None:
        self.graph = graph
        self.search = search
        self._embedding = embedding
        self._cache = cache

    # -- reads ------------------------------------------------------------ #
    def snapshot(self, world_id: str) -> WorldSnapshot:
        if self._cache is None:
            raise RuntimeError("the world editor needs the world cache to read a world")
        return self._cache.get(world_id)

    def node(self, world_id: str, node_id: str, label: str) -> Node | None:
        """The stored node if it exists with that label (one read, no snapshot)."""
        node = self.graph.get_node(world_id, node_id)
        return node if node is not None and node.label == label else None

    # -- writes ----------------------------------------------------------- #
    @contextmanager
    def writing(self, world_id: str) -> Iterator[None]:
        try:
            yield
        finally:
            self.written(world_id)

    def written(self, world_id: str) -> None:
        try:
            touch_world_meta(self.graph, world_id, last_writer="edit")
        finally:
            if self._cache is not None:
                self._cache.invalidate(world_id)

    def replace(self, nodes: list[Node]) -> None:
        if nodes:
            self.graph.replace_nodes(nodes)

    def index(self, docs: list[SearchDoc]) -> None:
        docs = [d for d in docs if d.text.strip()]
        if not docs:
            return
        if self._embedding is not None:
            try:
                vectors = self._embedding.embed([d.text for d in docs])
                for d, v in zip(docs, vectors, strict=False):
                    d.embedding = v
            except Exception:  # text-only indexing (no embedding is not an error)
                pass
        self.search.index(docs)

    def unindex(self, world_id: str, ids: list[str]) -> None:
        if ids:
            self.search.delete(world_id, ids)


# -- checks (BR-U3-5/6) -------------------------------------------------------- #
def check_path(path_world: str, path_id: str | None, world_id: str, item_id: str) -> None:
    """The path's world id and item id must match the body (A3-13 -> 400)."""
    if path_world != world_id or (path_id is not None and path_id != item_id):
        raise ValueError("path world_id/id must match the body")


def require_region(snapshot: WorldSnapshot, region_id: str) -> Region:
    region = snapshot.regions_by_id.get(region_id)
    if region is None:
        raise LookupError(f"region not found: {region_id}")
    return region
