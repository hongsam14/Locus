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
        if self._w.node(npc.world_id, npc.id, "NPC") is not None:
            raise ValueError(f"npc already exists: {npc.id}")
        return self.upsert_npc(npc)

    def upsert_npc(self, npc: NPC) -> NPC:
        if self._w.node(npc.world_id, npc.home_region_id, "Region") is None:
            raise LookupError(f"region not found: {npc.home_region_id}")
        old = self._w.node(npc.world_id, npc.id, "NPC")
        old_home = old.properties.get("home_region_id") if old is not None else None
        with self._w.writing(npc.world_id):
            self._w.replace([gm.npc_to_node(npc)])
            if old_home != npc.home_region_id:
                self._w.graph.upsert_edges(gm.lives_in_edges([npc]))
            if old_home and old_home != npc.home_region_id:
                self._w.graph.delete_edges(
                    npc.world_id,
                    [EdgeKey(type="LIVES_IN", source_id=npc.id, target_id=old_home)],
                )
            self._w.index([gm.npc_doc(npc)])
        return npc

    def delete_npc(self, world_id: str, npc_id: str) -> None:
        """Node (DETACH takes ``LIVES_IN``), then the search document; an NPC already
        gone still has its document removed before the ``LookupError`` (NFR R-01).
        Conversations with it stay in the sessions (BR-U3-17)."""
        held = self._w.node(world_id, npc_id, "NPC") is not None
        with self._w.writing(world_id):
            if held:
                self._w.graph.delete_node(world_id, npc_id)
            self._w.unindex(world_id, [npc_id])
        if not held:
            raise LookupError(f"npc not found: {npc_id}")
