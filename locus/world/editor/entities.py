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
        """A location is checked only when it changes: confirming an entity whose
        location is broken must not fail on that location (U3 review #12)."""
        old = self._w.own_label(entity.world_id, entity.id, "Entity")  # S26
        old_loc = old.properties.get("located_in") if old is not None else None
        if (
            entity.located_in
            and entity.located_in != old_loc
            and self._w.node(entity.world_id, entity.located_in, "Region") is None
        ):
            raise LookupError(f"region not found: {entity.located_in}")
        with self._w.writing(entity.world_id):
            if old_loc and old_loc != entity.located_in:
                self._w.graph.delete_edges(
                    entity.world_id,
                    [EdgeKey(type="LOCATED_IN", source_id=entity.id, target_id=old_loc)],
                )
            self._w.replace([gm.entity_to_node(entity)])
            if entity.located_in and entity.located_in != old_loc:
                self._w.graph.upsert_edges(gm.located_in_edges([entity]))
            previous = [gm.entity_doc(gm.node_to_entity(old))] if old is not None else None
            self._w.index([gm.entity_doc(entity)], previous=previous)
        return entity

    def delete_entity(self, world_id: str, entity_id: str) -> None:
        """Node, then search document; same retry rule as the other deletes (NFR R-01)."""
        if not self._w.delete_held(world_id, entity_id, "Entity"):
            raise LookupError(f"entity not found: {entity_id}")
