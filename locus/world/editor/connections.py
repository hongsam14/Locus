"""ConnectionEditor — a connection is always a pair, a→b and b→a (U3, BLM §1.4).

The key is two regions + a kind (BR-U3-11); a road and a river between the same two
regions are two connections. A save deletes the key's old pair and writes the new pair
(`SET r += …` would keep a cleared rationale), so the pair always has one kind, weight,
rationale and prior reference.
"""

from __future__ import annotations

from locus.shared.models import ConnectionEdge, ConnectionKind, WorldSnapshot
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import EdgeKey
from locus.world.editor.models import ConnectionKey
from locus.world.editor.writes import EditorWrites, require_region


class ConnectionEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    def upsert_connection(self, conn: ConnectionEdge) -> list[ConnectionEdge]:
        """Save the pair of ``conn`` (BR-U3-10); returns both directions."""
        if conn.source_region_id == conn.target_region_id:
            raise ValueError("a region cannot connect to itself")
        snapshot = self._w.snapshot(conn.world_id)
        require_region(snapshot, conn.source_region_id)
        require_region(snapshot, conn.target_region_id)
        pair = _pair(conn)
        self._write(conn.world_id, delete=[ConnectionKey.of(conn)], create=pair)
        return pair

    def change_connection_kind(
        self, key: ConnectionKey, new_kind: ConnectionKind | str
    ) -> list[ConnectionEdge]:
        """One operation (BR-U3-11): the pair keeps weight, rationale, prior ref and
        provenance under the new kind; the new pair is written before the old goes."""
        new_kind = ConnectionKind(new_kind)
        snapshot = self._w.snapshot(key.world_id)
        old = _existing(snapshot, key)
        if str(new_kind) == str(key.kind):
            return _pair(old)
        moved = key.model_copy(update={"kind": new_kind})
        if _find(snapshot, moved) is not None:
            raise ValueError(f"a {new_kind} connection already joins these regions")
        pair = _pair(old.model_copy(update={"kind": new_kind}))
        with self._w.writing(key.world_id):
            self._w.graph.upsert_edges(gm.connection_edges(pair))
            self._w.graph.delete_edges(key.world_id, edge_keys(key))
        return pair

    def delete_connection(self, key: ConnectionKey) -> int:
        _existing(self._w.snapshot(key.world_id), key)
        with self._w.writing(key.world_id):
            return self._w.graph.delete_edges(key.world_id, edge_keys(key))

    def set_prior_ref(self, key: ConnectionKey, prior_id: str | None) -> list[ConnectionEdge]:
        """Change the cited prior of both directions together (FD 검토 R-11)."""
        old = _existing(self._w.snapshot(key.world_id), key)
        pair = _pair(old.model_copy(update={"wiki_prior_ref": prior_id}))
        self._write(key.world_id, delete=[key], create=pair)
        return pair

    def _write(
        self, world_id: str, *, delete: list[ConnectionKey], create: list[ConnectionEdge]
    ) -> None:
        with self._w.writing(world_id):
            self._w.graph.delete_edges(world_id, [e for k in delete for e in edge_keys(k)])
            self._w.graph.upsert_edges(gm.connection_edges(create))


# --------------------------------------------------------------------------- #
def edge_keys(key: ConnectionKey) -> list[EdgeKey]:
    """Both stored directions of one connection."""
    ident = {"kind": str(key.kind)}
    return [
        EdgeKey(type="CONNECTED_TO", source_id=a, target_id=b, identity=ident)
        for a, b in ((key.a_region_id, key.b_region_id), (key.b_region_id, key.a_region_id))
    ]


def _pair(conn: ConnectionEdge) -> list[ConnectionEdge]:
    back = conn.model_copy(
        update={
            "source_region_id": conn.target_region_id,
            "target_region_id": conn.source_region_id,
        }
    )
    return [conn, back]


def _find(snapshot: WorldSnapshot, key: ConnectionKey) -> ConnectionEdge | None:
    wanted = key.normalized()
    return next((c for c in snapshot.topo.connections if ConnectionKey.of(c) == wanted), None)


def _existing(snapshot: WorldSnapshot, key: ConnectionKey) -> ConnectionEdge:
    found = _find(snapshot, key)
    if found is None:
        raise LookupError(f"connection not found: {key.a_region_id}–{key.b_region_id} ({key.kind})")
    return found
