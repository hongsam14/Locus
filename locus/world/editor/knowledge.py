"""KnowledgeEditor — knowledge items and their DIRECT scopes (U3, BLM §1.5, US-2.3).

Editing a statement keeps its scopes (US-2.3 셋째); scopes change only through
``set_scopes``. INHERITED and GLOBAL scopes are computed, never stored.
"""

from __future__ import annotations

from locus.shared.models import Knowledge, ScopeLink, ScopeType, fallback_title
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import Edge, EdgeKey
from locus.world.editor.writes import EditorWrites, require_region


class KnowledgeEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    def upsert_knowledge(self, knowledge: Knowledge) -> Knowledge:
        """Replace the item and re-index it; its scopes stay, but its DIRECT scope edges,
        which the region views read, get its confidence (U3 review S29). Both are judged on
        what is stored — the edge values, the node behind the search document — so the
        same request sent again after a cut finishes the job (U8 review #4, BR-U3-8); an
        edge that was already off is set right on the next save. ``region_hint`` is a
        build-time value and is not stored. An empty title gets the server's fallback
        (C17)."""
        snapshot = self._w.require_world(knowledge.world_id)  # S21
        old = self._w.own_label(knowledge.world_id, knowledge.id, "Knowledge")  # S26
        knowledge = _clean(knowledge)
        before = gm.node_to_knowledge(old) if old is not None else None
        stale = [
            s.model_copy(update={"confidence": knowledge.confidence})
            for s in snapshot.kg.scopes
            if s.knowledge_id == knowledge.id
            and str(s.scope_type) == ScopeType.DIRECT.value
            and s.confidence != knowledge.confidence
        ]
        with self._w.writing(knowledge.world_id):
            self._write_item(knowledge, before)
            if stale:
                self._w.graph.upsert_edges(gm.scope_edges(stale))
        return knowledge

    def create_knowledge(self, knowledge: Knowledge, region_id: str) -> Knowledge:
        """ "지식 추가" on a region: the item plus one DIRECT scope (BR-U3-12). An id that
        already exists is 400, as for regions and NPCs (U3 review S32)."""
        require_region(self._w.require_world(knowledge.world_id), region_id)
        if self._w.own_label(knowledge.world_id, knowledge.id, "Knowledge") is not None:
            raise ValueError(f"knowledge already exists: {knowledge.id}")
        knowledge = _clean(knowledge)
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

    def _write_item(self, knowledge: Knowledge, before: Knowledge | None = None) -> None:
        # the document first, the node last: the node is what C11 compares with, so a
        # cut before it leaves the old text there and the retry indexes again (U8 #4)
        previous = [gm.knowledge_doc(before)] if before is not None else None
        self._w.index([gm.knowledge_doc(knowledge)], previous=previous)
        self._w.replace([gm.knowledge_to_node(knowledge)])

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

    def repoint(
        self, world_id: str, knowledge_id: str, field: str, old_id: str, new_id: str | None
    ) -> Knowledge:
        """Replace one id in ``derived_from_prior_ids`` / ``about_entity_ids`` (or drop it
        when ``new_id`` is None) and its DERIVED_FROM / ABOUT edge (FD 검토 02 R-11)."""
        edge_type = {"derived_from_prior_ids": "DERIVED_FROM", "about_entity_ids": "ABOUT"}.get(
            field
        )
        if edge_type is None:
            raise ValueError(f"not a reference list: {field}")
        snapshot = self._w.snapshot(world_id)
        item = next((k for k in snapshot.kg.knowledge if k.id == knowledge_id), None)
        if item is None:
            raise LookupError(f"knowledge not found: {knowledge_id}")
        ids = [new_id if i == old_id else i for i in getattr(item, field)]
        ids = [i for i in dict.fromkeys(ids) if i]
        changed = item.model_copy(update={field: ids, "region_hint": None})
        before = item
        with self._w.writing(world_id):
            if new_id:
                self._w.graph.upsert_edges(
                    [
                        Edge(
                            type=edge_type,
                            source_id=knowledge_id,
                            target_id=new_id,
                            world_id=world_id,
                        )
                    ]
                )
            self._write_item(changed, before)
            self._w.graph.delete_edges(
                world_id, [EdgeKey(type=edge_type, source_id=knowledge_id, target_id=old_id)]
            )
        return changed

    def delete_knowledge(self, world_id: str, knowledge_id: str) -> None:
        """Graph first, then search. An item already gone still has its document removed
        before the ``LookupError``, so a retry after a cut cleans up (NFR R-01). The
        router purges its translations (BR-U3-3)."""
        if not self._w.delete_held(world_id, knowledge_id, "Knowledge"):
            raise LookupError(f"knowledge not found: {knowledge_id}")

    def list_unscoped(self, world_id: str) -> list[Knowledge]:
        """Not global and scoped nowhere (BR-U3-14): what the build could not place and
        what a region delete left behind."""
        snapshot = self._w.snapshot(world_id)
        unscoped = set(snapshot.unscoped_knowledge_ids)  # one rule (U3 review C5)
        return [k for k in snapshot.kg.knowledge if k.id in unscoped]


def _clean(knowledge: Knowledge) -> Knowledge:
    """No build-time hint; an empty title gets the server's fallback (U3 review C17)."""
    title = (knowledge.title or "").strip() or fallback_title(knowledge.statement)
    return knowledge.model_copy(update={"region_hint": None, "title": title})
