"""Apply augmentation answers as graph mutations + revert (U7, US-6.3)."""

from __future__ import annotations

from ..models import Knowledge, Provenance, ScopeLink, ScopeType, SourceKind
from ..storage import graph_mapping as gm
from ..storage.base import Node
from .types import AnswerAction, AugmentationAnswer, ChangeSet, NodeSnapshot


def _snapshot(node: Node) -> NodeSnapshot:
    return NodeSnapshot(id=node.id, label=node.label, properties=dict(node.properties))


def apply_answer(answer: AugmentationAnswer, *, world_id: str, graph_repo, editor) -> ChangeSet:
    cs = ChangeSet(description=f"answer:{answer.action}")
    action = AnswerAction(answer.action)

    if action == AnswerAction.IGNORE:
        return cs

    if action == AnswerAction.ADD:
        k = Knowledge(
            world_id=world_id,
            statement=answer.statement or "",
            confidence=answer.confidence if answer.confidence is not None else 0.8,
            region_hint=answer.region_id,
            provenance=Provenance(
                source=SourceKind.AUGMENTATION, generated_by="designer", refs=[cs.id]
            ),
        )
        editor.upsert_knowledge(k)
        cs.added_ids.append(k.id)
        if answer.region_id:
            scope = ScopeLink(
                world_id=world_id,
                knowledge_id=k.id,
                region_id=answer.region_id,
                scope_type=ScopeType.DIRECT,
                confidence=k.confidence,
            )
            graph_repo.upsert_edges(gm.scope_edges([scope]))
        return cs

    # confirm / edit / remove target an existing node
    target = answer.target_id
    node = graph_repo.get_node(world_id, target) if target else None
    if node is None:
        return cs  # nothing to do

    if action == AnswerAction.REMOVE:
        cs.removed.append(_snapshot(node))
        editor.delete_node(world_id, target)
        return cs

    # confirm / edit -> mutate a Knowledge node
    cs.updated.append(_snapshot(node))
    knowledge = gm.node_to_knowledge(node)
    if action == AnswerAction.CONFIRM:
        knowledge.confidence = (
            answer.confidence if answer.confidence is not None else max(knowledge.confidence, 0.9)
        )
    elif action == AnswerAction.EDIT:
        if answer.statement:
            knowledge.statement = answer.statement
        if answer.confidence is not None:
            knowledge.confidence = answer.confidence
    editor.upsert_knowledge(knowledge)
    return cs


def revert(change_set: ChangeSet, *, world_id: str, graph_repo, editor) -> None:
    for nid in change_set.added_ids:
        editor.delete_node(world_id, nid)
    for snap in change_set.removed + change_set.updated:
        graph_repo.upsert_nodes(
            [Node(id=snap.id, label=snap.label, world_id=world_id, properties=snap.properties)]
        )
