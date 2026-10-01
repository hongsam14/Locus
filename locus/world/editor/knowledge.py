"""KnowledgeEditor — knowledge items and their DIRECT scopes (U3, BLM §1.5, US-2.3).

Editing a statement keeps its scopes (US-2.3 셋째); scopes change only through
``set_scopes``. INHERITED and GLOBAL scopes are computed, never stored.
"""

from __future__ import annotations

from locus.shared.models import Knowledge, ScopeLink, ScopeType
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import EdgeKey
from locus.world.editor.writes import EditorWrites, require_region


class KnowledgeEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    def upsert_knowledge(self, knowledge: Knowledge) -> Knowledge:
        """Replace the item and re-index it; scopes are untouched. ``region_hint`` is a
        build-time value and is not stored."""
        knowledge = knowledge.model_copy(update={"region_hint": None})
        with self._w.writing(knowledge.world_id):
            self._write_item(knowledge)
        return knowledge

    def create_knowledge(self, knowledge: Knowledge, region_id: str) -> Knowledge:
        """ "지식 추가" on a region: the item plus one DIRECT scope (BR-U3-12)."""
        require_region(self._w.snapshot(knowledge.world_id), region_id)
        knowledge = knowledge.model_copy(update={"region_hint": None})
        scope = ScopeLink(
            world_id=knowledge.world_id,
            knowledge_id=knowledge.id,
            region_id=region_id,
            scope_type=ScopeType.DIRECT,
            confidence=knowledge.confidence,
        )
        with self._w.writing(knowledge.world_id):
            self._write_item(knowledge)
            self._w.graph.upsert_edges(gm.scope_edges([scope]))
        return knowledge

    def _write_item(self, knowledge: Knowledge) -> None:
        self._w.replace([gm.knowledge_to_node(knowledge)])
        self._w.index([gm.knowledge_doc(knowledge)])

    def set_scopes(self, world_id: str, knowledge_id: str, region_ids: list[str]) -> list[str]:
        """The item's DIRECT scopes become exactly ``region_ids`` (BR-U3-13); an empty
        list leaves it unscoped."""
        snapshot = self._w.snapshot(world_id)
        item = next((k for k in snapshot.kg.knowledge if k.id == knowledge_id), None)
        if item is None:
            raise LookupError(f"knowledge not found: {knowledge_id}")
        wanted = list(dict.fromkeys(region_ids))
        for rid in wanted:
            require_region(snapshot, rid)
        current = {s.region_id for s in snapshot.kg.scopes if s.knowledge_id == knowledge_id}
        gone = [rid for rid in current if rid not in wanted]
        new = [rid for rid in wanted if rid not in current]
        with self._w.writing(world_id):
            if gone:
                self._w.graph.delete_edges(
                    world_id,
                    [EdgeKey(type="SCOPED_TO", source_id=knowledge_id, target_id=r) for r in gone],
                )
            if new:
                self._w.graph.upsert_edges(
                    gm.scope_edges(
                        [
                            ScopeLink(
                                world_id=world_id,
                                knowledge_id=knowledge_id,
                                region_id=r,
                                scope_type=ScopeType.DIRECT,
                                confidence=item.confidence,
                            )
                            for r in new
                        ]
                    )
                )
        return wanted

    def delete_knowledge(self, world_id: str, knowledge_id: str) -> None:
        """Graph first, then search. An item already gone still has its document removed
        before the ``LookupError``, so a retry after a cut cleans up (NFR R-01). The
        router purges its translations (BR-U3-3)."""
        held = self._w.node(world_id, knowledge_id, "Knowledge") is not None
        with self._w.writing(world_id):
            if held:
                self._w.graph.delete_node(world_id, knowledge_id)
            self._w.unindex(world_id, [knowledge_id])
        if not held:
            raise LookupError(f"knowledge not found: {knowledge_id}")

    def list_unscoped(self, world_id: str) -> list[Knowledge]:
        """Not global and scoped nowhere (BR-U3-14): what the build could not place and
        what a region delete left behind."""
        snapshot = self._w.snapshot(world_id)
        scoped = {s.knowledge_id for s in snapshot.kg.scopes}
        return [k for k in snapshot.kg.knowledge if not k.is_global and k.id not in scoped]
