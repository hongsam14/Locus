"""EntityEditor — entity edits the augmentation Q&A makes (U3, BLM §1.7, B3).

The editor screen has no entity form (no story asks for one); the Q&A confirms, edits,
locates or removes entities through this class.
"""

from __future__ import annotations

from locus.shared.models import Entity
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import EdgeKey
from locus.world.editor.writes import EditorWrites


class EntityEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    def update_entity(self, entity: Entity) -> Entity:
        if entity.located_in and self._w.node(entity.world_id, entity.located_in, "Region") is None:
            raise LookupError(f"region not found: {entity.located_in}")
        old = self._w.node(entity.world_id, entity.id, "Entity")
        old_loc = old.properties.get("located_in") if old is not None else None
        with self._w.writing(entity.world_id):
            if old_loc and old_loc != entity.located_in:
                self._w.graph.delete_edges(
                    entity.world_id,
                    [EdgeKey(type="LOCATED_IN", source_id=entity.id, target_id=old_loc)],
                )
            self._w.replace([gm.entity_to_node(entity)])
            if entity.located_in and entity.located_in != old_loc:
                self._w.graph.upsert_edges(gm.located_in_edges([entity]))
            self._w.index([gm.entity_doc(entity)])
        return entity

    def delete_entity(self, world_id: str, entity_id: str) -> None:
        """Node, then search document; same retry rule as the other deletes (NFR R-01)."""
        held = self._w.node(world_id, entity_id, "Entity") is not None
        with self._w.writing(world_id):
            if held:
                self._w.graph.delete_node(world_id, entity_id)
            self._w.unindex(world_id, [entity_id])
        if not held:
            raise LookupError(f"entity not found: {entity_id}")
