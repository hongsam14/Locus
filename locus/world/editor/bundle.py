"""Editors — the editor classes as one injectable bundle (U3, domain-entities §8 item 8).

The augmentation Q&A writes through the same classes as the editor screen. Its REMOVE
answer names knowledge or an entity, so ``delete_any`` dispatches by the question's
target kind (FD 이탈 1: the generic delete is gone from the API and lives on only here;
V7 code review #4: by kind, not by whatever node the id reads first).
"""

from __future__ import annotations

from dataclasses import dataclass

from locus.knowledge.cache import SnapshotCache
from locus.shared.llm.base import EmbeddingProvider
from locus.shared.storage.base import GraphRepository, SearchRepository
from locus.world.editor.connections import ConnectionEditor
from locus.world.editor.entities import EntityEditor
from locus.world.editor.knowledge import KnowledgeEditor
from locus.world.editor.npcs import NpcEditor
from locus.world.editor.regions import RegionEditor
from locus.world.editor.writes import EditorWrites


@dataclass(frozen=True)
class Editors:
    writes: EditorWrites
    regions: RegionEditor
    connections: ConnectionEditor
    knowledge: KnowledgeEditor
    npcs: NpcEditor
    entities: EntityEditor

    @classmethod
    def assemble(
        cls,
        graph: GraphRepository,
        search: SearchRepository,
        embedding: EmbeddingProvider | None = None,
        *,
        cache: SnapshotCache | None = None,
    ) -> "Editors":
        w = EditorWrites(graph, search, embedding, cache=cache)
        return cls(
            writes=w,
            regions=RegionEditor(w),
            connections=ConnectionEditor(w),
            knowledge=KnowledgeEditor(w),
            npcs=NpcEditor(w),
            entities=EntityEditor(w),
        )

    def delete_any(self, world_id: str, node_id: str, kind: str) -> bool:
        """Delete what an augmentation REMOVE answer names — knowledge or an entity, the
        only kinds a question removes (U3 review C4). ``kind`` is the question's target
        kind: the delete takes that kind's node only, never another kind's node under the
        same id (V7 code review #4). False when it is not there."""
        delete = {
            "knowledge": self.knowledge.delete_knowledge,
            "entity": self.entities.delete_entity,
        }.get(kind)
        if delete is None:
            raise ValueError(f"cannot delete a {kind} here: {node_id}")
        try:
            delete(world_id, node_id)
        except LookupError:
            return False
        return True
