"""NpcEditor — a region's inhabitants (U3, BLM §1.6, US-2.4).

An NPC lives in one region (``home_region_id`` + one ``LIVES_IN``, BR-U3-18). NPC text
is shown as written; there is no ``npc`` translation kind (BR-U3-37).
"""

from __future__ import annotations

from locus.shared.models import NPC
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import EdgeKey
from locus.world.editor.writes import EditorWrites


class NpcEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    def create_npc(self, npc: NPC) -> NPC:
        if self._w.own_label(npc.world_id, npc.id, "NPC") is not None:
            raise ValueError(f"npc already exists: {npc.id}")
        return self.upsert_npc(npc)

    def upsert_npc(self, npc: NPC) -> NPC:
        """Write order (U3 review #13): the new ``LIVES_IN`` first, then the node, then the
        old ``LIVES_IN`` edges. The old homes are read from the edges (what the loader
        follows), so a retry after a cut finds a leftover edge and removes it."""
        self._w.require_world(npc.world_id)  # S21
        if self._w.node(npc.world_id, npc.home_region_id, "Region") is None:
            raise LookupError(f"region not found: {npc.home_region_id}")
        old = self._w.own_label(npc.world_id, npc.id, "NPC")  # S26
        homes = {
            e.target_id
            for e in self._w.graph.edges_touching(npc.world_id, [npc.id], ["LIVES_IN"])
            if e.source_id == npc.id
        }
        gone = sorted(homes - {npc.home_region_id})
        with self._w.writing(npc.world_id):
            # the document before the node it is compared with (U8 review #4, C11)
            previous = [gm.npc_doc(gm.node_to_npc(old))] if old is not None else None
            self._w.index([gm.npc_doc(npc)], previous=previous)
            if npc.home_region_id not in homes:
                self._w.graph.upsert_edges(gm.lives_in_edges([npc]))
            self._w.replace([gm.npc_to_node(npc)])
            if gone:
                self._w.graph.delete_edges(
                    npc.world_id,
                    [EdgeKey(type="LIVES_IN", source_id=npc.id, target_id=h) for h in gone],
                )
        return npc

    def delete_npc(self, world_id: str, npc_id: str) -> None:
        """Node (DETACH takes ``LIVES_IN``), then the search document; an NPC already
        gone still has its document removed before the ``LookupError`` (NFR R-01).
        Conversations with it stay in the sessions (BR-U3-17)."""
        if not self._w.delete_held(world_id, npc_id, "NPC"):
            raise LookupError(f"npc not found: {npc_id}")
