"""In-memory ``GraphRepository`` / ``SearchRepository`` for offline tests (U2 Step 1.2).

Behaves like the real adapters where tests care: upserts are idempotent, reads are
world-scoped, ``delete_world`` removes everything of a world, and a node ``id`` that
already exists in ANOTHER world raises ``ConstraintViolation`` (the Neo4j unique
``id`` constraint). ``shuffle`` returns reads in a scrambled order so tests can prove
they do not depend on storage order (TP-U2-1).
"""

from __future__ import annotations

import random

from locus.shared.models import SearchDoc, SearchHit
from locus.shared.storage.base import (
    ConstraintViolation,
    Edge,
    EdgeKey,
    Node,
    edge_identity_field,
)


class InMemoryGraphRepository:
    def __init__(self, *, shuffle: random.Random | None = None) -> None:
        self._nodes: dict[tuple[str, str], Node] = {}  # (world_id, id) -> node
        self._edges: dict[tuple, Edge] = {}  # (world, type, src, dst, identity)
        self.shuffle = shuffle
        self.fail_on_upsert: Exception | None = None  # tests inject persist failures

    # -- lifecycle / schema (no-ops) ---------------------------------------- #
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...

    def health_check(self) -> bool:
        return True

    def ensure_schema(self) -> None: ...

    # -- writes ------------------------------------------------------------ #
    def upsert_nodes(self, nodes: list[Node]) -> None:
        if self.fail_on_upsert is not None:
            raise self.fail_on_upsert
        for node in nodes:
            for (wid, nid), _existing in self._nodes.items():
                if nid == node.id and wid != node.world_id:
                    raise ConstraintViolation(
                        f"{node.label} id {node.id!r} already exists in world {wid!r}"
                    )
            key = (node.world_id, node.id)
            if key in self._nodes:
                merged = dict(self._nodes[key].properties)
                merged.update(node.properties)
                self._nodes[key] = node.model_copy(update={"properties": merged})
            else:
                self._nodes[key] = node.model_copy()

    def upsert_edges(self, edges: list[Edge]) -> None:
        if self.fail_on_upsert is not None:
            raise self.fail_on_upsert
        for e in edges:
            key_field = edge_identity_field(e)
            key = e.properties.get(key_field) if key_field else None
            self._edges[(e.world_id, e.type, e.source_id, e.target_id, key)] = e.model_copy()

    def replace_edges(self, edges: list[Edge]) -> None:
        """U8: the fake's upsert already replaces an edge whole."""
        self.upsert_edges(edges)

    def edges_touching(
        self, world_id: str, node_ids: list[str], types: list[str] | None = None
    ) -> list[Edge]:
        ids = set(node_ids)
        out = [  # read the store directly: not a whole-world get_edges (U3 review C10)
            e.model_copy()
            for e in self._edges.values()
            if e.world_id == world_id
            and (types is None or e.type in types)
            and (e.source_id in ids or e.target_id in ids)
        ]
        return self._ordered(out)

    def replace_nodes(self, nodes: list[Node]) -> None:
        """U3: properties replaced whole (a property left out is removed)."""
        if self.fail_on_upsert is not None:
            raise self.fail_on_upsert
        for node in nodes:
            for (wid, nid), _existing in self._nodes.items():
                if nid == node.id and wid != node.world_id:
                    raise ConstraintViolation(
                        f"{node.label} id {node.id!r} already exists in world {wid!r}"
                    )
            self._nodes[(node.world_id, node.id)] = node.model_copy(
                update={"properties": dict(node.properties)}
            )

    def delete_edges(self, world_id: str, edges: list[EdgeKey]) -> int:
        """U3: delete the matching edges; an empty identity matches every parallel edge."""
        deleted = 0
        for key in edges:
            doomed = [
                k
                for k, e in self._edges.items()
                if e.world_id == world_id
                and e.type == key.type
                and e.source_id == key.source_id
                and e.target_id == key.target_id
                and all(e.properties.get(f) == v for f, v in key.identity.items())
            ]
            for k in doomed:
                del self._edges[k]
            deleted += len(doomed)
        return deleted

    def delete_node(self, world_id: str, node_id: str) -> None:
        self._nodes.pop((world_id, node_id), None)
        self._edges = {
            k: e
            for k, e in self._edges.items()
            if not (e.world_id == world_id and node_id in (e.source_id, e.target_id))
        }

    def delete_world(self, world_id: str) -> None:
        self._nodes = {k: n for k, n in self._nodes.items() if k[0] != world_id}
        self._edges = {k: e for k, e in self._edges.items() if e.world_id != world_id}

    # -- reads ------------------------------------------------------------- #
    def _ordered(self, items: list):
        if self.shuffle is not None:
            items = list(items)
            self.shuffle.shuffle(items)
        return items

    def get_node(self, world_id: str, node_id: str) -> Node | None:
        n = self._nodes.get((world_id, node_id))
        return n.model_copy() if n else None

    def find_nodes(self, world_id: str, label: str, filters: dict | None = None) -> list[Node]:
        out = [
            n.model_copy()
            for (wid, _), n in self._nodes.items()
            if wid == world_id
            and n.label == label
            and all(n.properties.get(k) == v for k, v in (filters or {}).items())
        ]
        return self._ordered(out)

    def get_edges(self, world_id: str, types: list[str] | None = None) -> list[Edge]:
        out = [
            e.model_copy()
            for e in self._edges.values()
            if e.world_id == world_id and (types is None or e.type in types)
        ]
        return self._ordered(out)

    def list_world_ids(self) -> list[str]:
        return sorted({wid for wid, _ in self._nodes})


class InMemorySearchRepository:
    def __init__(self) -> None:
        self.docs: dict[tuple[str, str], SearchDoc] = {}
        self.fail_on_index: Exception | None = None
        self.fail_on_delete: Exception | None = None

    def connect(self) -> None: ...
    def disconnect(self) -> None: ...

    def health_check(self) -> bool:
        return True

    def ensure_index(self) -> None: ...

    def index(self, docs: list[SearchDoc]) -> None:
        if self.fail_on_index is not None:
            raise self.fail_on_index
        for d in docs:
            self.docs[(d.world_id, d.id)] = d.model_copy()

    def delete(self, world_id: str, doc_ids: list[str]) -> int:
        """U3: delete a world's documents by id; missing ids are skipped."""
        if self.fail_on_delete is not None:
            raise self.fail_on_delete
        gone = [key for key in ((world_id, d) for d in doc_ids) if key in self.docs]
        for key in gone:
            del self.docs[key]
        return len(gone)

    def hybrid_search(
        self,
        world_id: str | None,
        query_text: str,
        query_embedding: list[float] | None = None,
        k: int = 5,
        filters: dict | None = None,
    ) -> list[SearchHit]:
        needle = query_text.lower()
        hits = [
            SearchHit(
                id=d.id, world_id=d.world_id, label=d.label, text=d.text, score=1.0, meta=d.meta
            )
            for d in self.docs.values()
            if (world_id is None or d.world_id == world_id)
            and all(
                d.meta.get(k2) == v or getattr(d, k2, None) == v
                for k2, v in (filters or {}).items()
            )
            and needle in d.text.lower()
        ]
        return hits[:k]

    def delete_world(self, world_id: str) -> None:
        self.docs = {key: d for key, d in self.docs.items() if key[0] != world_id}
