"""Apply an answer to its question's target, and undo it (U3, BLM §4.2·§4.3, B1/B3/B6).

Writes go through the editor classes, so an answer gets the same checks, search
indexing and cache invalidation as an edit on the screen. A change records the
watched nodes before and right after, and the edges that appeared or went (a diff of
the edges touching the watched nodes), so a revert can put nodes, edges and search
documents back — after checking nobody edited the target since (FD 검토 R-08).
"""

from __future__ import annotations

import json

from locus.shared.models import Knowledge, Provenance, SourceKind, fallback_title
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import Edge, EdgeKey, Node, edge_identity_field
from locus.world.augmentation.types import (
    AnswerAction,
    AugmentationAnswer,
    AugmentationQuestion,
    ChangeSet,
    EdgeSnapshot,
    Issue,
    IssueType,
    NodeSnapshot,
    RevertConflictError,
)
from locus.world.editor import ConnectionKey, Editors

_REF_KIND = {  # dangling field -> the label its new reference must have
    "parent_id": "Region",
    "located_in": "Region",
    "wiki_prior_ref": "WikiPrior",
    "derived_from_prior_ids": "WikiPrior",
    "about_entity_ids": "Entity",
}


def apply_answer(
    issue: Issue,
    question: AugmentationQuestion,
    answer: AugmentationAnswer,
    *,
    world_id: str,
    editors: Editors,
) -> ChangeSet | None:
    """Apply ``answer`` to ``question``'s target; None for ignore (nothing written)."""
    action = AnswerAction(answer.action)
    if action not in [AnswerAction(a) for a in question.actions]:
        raise ValueError(f"{action} is not an answer to this question")
    if action == AnswerAction.IGNORE:
        return None
    target = question.target
    if target is None:
        raise ValueError("this question has no target")
    nodes, watch = _watched(issue, target.id)
    cs = ChangeSet(description=f"{issue.type}:{action}")
    graph = editors.writes.graph
    nodes_before = _nodes(editors, world_id, nodes)
    before = _edges(graph, world_id, watch)

    added = _write(issue, target.id, action, answer, world_id=world_id, editors=editors, cs=cs)
    cs.added_ids = added
    nodes_after = _nodes(editors, world_id, [*nodes, *added])
    # only what changed is recorded: a revert checks those for edits made after it
    changed = {
        i
        for i in nodes_before.keys() | nodes_after.keys()
        if i not in nodes_before
        or i not in nodes_after
        or _props(nodes_before[i].properties) != _props(nodes_after[i].properties)
    }
    cs.nodes_before = [n for i, n in nodes_before.items() if i in changed]
    cs.nodes_after = [n for i, n in nodes_after.items() if i in changed]
    after = _edges(graph, world_id, [*watch, *added])
    cs.edges_added = [after[k] for k in after.keys() - before.keys()]
    cs.edges_removed = [before[k] for k in before.keys() - after.keys()]
    return cs


def _watched(issue: Issue, target_id: str) -> tuple[list[str], list[str]]:
    """(nodes that may change, ids whose edges may change)."""
    if issue.target_kind == "connection":
        a, b = target_id.split("|")[:2]
        return [], [a, b]
    return [target_id], [target_id]


def _write(issue, target_id, action, answer, *, world_id, editors: Editors, cs) -> list[str]:
    """The writes of BLM §4.2's table; returns the ids of nodes it created."""
    kind = IssueType(issue.type)
    if kind == IssueType.GAP:  # add
        statement = (answer.statement or "").strip()
        if not statement:
            raise ValueError("an added fact needs a statement")
        k = Knowledge(
            world_id=world_id,
            statement=statement,
            title=(answer.title or "").strip() or fallback_title(statement),
            confidence=answer.confidence if answer.confidence is not None else 0.8,
            provenance=Provenance(
                source=SourceKind.AUGMENTATION, generated_by="designer", refs=[cs.id]
            ),
        )
        editors.knowledge.create_knowledge(k, target_id)
        return [k.id]
    if action == AnswerAction.REMOVE and kind != IssueType.DANGLING:
        if not editors.delete_any(world_id, target_id):
            raise LookupError(f"node not found: {target_id}")
        return []
    if kind in (IssueType.LOW_CONFIDENCE, IssueType.WIKI_CONFLICT):
        _confirm_or_edit(issue, target_id, action, answer, world_id, editors)
    elif kind == IssueType.ORPHAN:  # edit: place it in a region
        entity = _entity(editors, world_id, target_id)
        editors.entities.update_entity(entity.model_copy(update={"located_in": _region(answer)}))
    elif kind == IssueType.UNSCOPED:  # edit: scope it to a region
        editors.knowledge.set_scopes(world_id, target_id, [_region(answer)])
    elif kind == IssueType.DANGLING:
        _repoint(issue, target_id, action, answer, world_id, editors)
    return []


def _confirm_or_edit(issue, target_id, action, answer, world_id, editors: Editors) -> None:
    if issue.target_kind == "entity":  # B3: entity targets edit the entity
        e = _entity(editors, world_id, target_id)
        if action == AnswerAction.CONFIRM:
            conf = answer.confidence if answer.confidence is not None else max(e.confidence, 0.9)
            e = e.model_copy(update={"confidence": conf})
        else:
            update: dict = {}
            if answer.statement:
                update["description"] = answer.statement
            if answer.confidence is not None:
                update["confidence"] = answer.confidence
            e = e.model_copy(update=update)
        editors.entities.update_entity(e)
        return
    k = _knowledge(editors, world_id, target_id)
    if action == AnswerAction.CONFIRM:
        conf = answer.confidence if answer.confidence is not None else max(k.confidence, 0.9)
        k = k.model_copy(update={"confidence": conf})
    else:
        update = {}
        if answer.statement:
            update["statement"] = answer.statement
        if answer.title:
            update["title"] = answer.title
        if answer.confidence is not None:
            update["confidence"] = answer.confidence
        k = k.model_copy(update=update)
    editors.knowledge.upsert_knowledge(k)


def _repoint(issue: Issue, target_id, action, answer, world_id, editors: Editors) -> None:
    """dangling: edit -> the field points at ``ref_id``; remove -> the field is cleared
    (for a list, only ``broken_id`` goes)."""
    field = issue.field or ""
    ref = None
    if action == AnswerAction.EDIT:
        ref = answer.ref_id
        node = editors.writes.graph.get_node(world_id, ref) if ref else None
        if node is None or node.label != _REF_KIND.get(field):
            raise ValueError(f"{field} must point at an existing {_REF_KIND.get(field)}")
    if field == "parent_id":  # through the region editor: the cycle check applies
        region = editors.writes.snapshot(world_id).regions_by_id.get(target_id)
        if region is None:
            raise LookupError(f"region not found: {target_id}")
        editors.regions.upsert_region(region.model_copy(update={"parent_id": ref}))
    elif field == "located_in":
        entity = _entity(editors, world_id, target_id)
        editors.entities.update_entity(entity.model_copy(update={"located_in": ref}))
    elif field == "wiki_prior_ref":  # both directions of the connection
        a, b, kind = target_id.split("|")
        key = ConnectionKey(world_id=world_id, a_region_id=a, b_region_id=b, kind=kind)
        editors.connections.set_prior_ref(key, ref)
    else:
        editors.knowledge.repoint(world_id, target_id, field, issue.broken_id or "", ref)


# --------------------------------------------------------------------------- #
def revert(change: ChangeSet, *, world_id: str, editors: Editors) -> None:
    """Undo ``change``. Refused, with nothing written, when a node it touched was edited
    after it (or a node it made is gone), or when an edge it wrote or removed has changed
    since — a change outside this run. The edge check covers answers whose target is a
    connection or a scope, which record no node (U3 review #4, BR-U3-27)."""
    graph = editors.writes.graph
    for snap in change.nodes_after:
        now = graph.get_node(world_id, snap.id)
        if now is None or _props(now.properties) != _props(snap.properties):
            raise RevertConflictError(f"{snap.id} was edited after this change")
    edited = _edges_edited_since(graph, world_id, change)
    if edited:
        raise RevertConflictError(f"{edited} was edited after this change")
    change.revert_started = True  # past the checks: a retry may resume (U3 review S03)
    with editors.writes.writing(world_id):
        graph.delete_edges(world_id, [_key(e) for e in change.edges_added])
        for nid in change.added_ids:
            graph.delete_node(world_id, nid)
        editors.writes.unindex(world_id, change.added_ids)
        restored = [
            Node(id=s.id, label=s.label, world_id=world_id, properties=s.properties)
            for s in change.nodes_before
        ]
        editors.writes.replace(restored)
        graph.upsert_edges(
            [
                Edge(
                    type=e.type,
                    source_id=e.source_id,
                    target_id=e.target_id,
                    world_id=world_id,
                    properties=e.properties,
                )
                for e in change.edges_removed
            ]
        )
        editors.writes.index([d for d in (_doc(n) for n in restored) if d is not None])


# --------------------------------------------------------------------------- #
def _region(answer: AugmentationAnswer) -> str:
    if not answer.region_id:
        raise ValueError("this answer needs a region")
    return answer.region_id


def _entity(editors: Editors, world_id: str, entity_id: str):
    node = editors.writes.node(world_id, entity_id, "Entity")
    if node is None:
        raise LookupError(f"entity not found: {entity_id}")
    return gm.node_to_entity(node)


def _knowledge(editors: Editors, world_id: str, knowledge_id: str) -> Knowledge:
    node = editors.writes.node(world_id, knowledge_id, "Knowledge")
    if node is None:
        raise LookupError(f"knowledge not found: {knowledge_id}")
    return gm.node_to_knowledge(node)


def _nodes(editors: Editors, world_id: str, ids: list[str]) -> dict[str, NodeSnapshot]:
    out: dict[str, NodeSnapshot] = {}
    for nid in dict.fromkeys(ids):
        node = editors.writes.graph.get_node(world_id, nid)
        if node is not None:
            out[nid] = NodeSnapshot(id=node.id, label=node.label, properties=dict(node.properties))
    return out


def _edges(graph, world_id: str, ids: list[str]) -> dict[tuple, EdgeSnapshot]:
    """The edges touching ``ids``, read with one filtered query (U3 review C10)."""
    return {
        (
            e.type,
            e.source_id,
            e.target_id,
            json.dumps(e.properties, sort_keys=True, default=str),
        ): EdgeSnapshot(
            type=e.type, source_id=e.source_id, target_id=e.target_id, properties=dict(e.properties)
        )
        for e in graph.edges_touching(world_id, list(dict.fromkeys(ids)))
    }


def is_undone(change: ChangeSet, *, world_id: str, editors: Editors) -> bool:
    """The graph is back where ``change`` found it: its nodes as before, the nodes it made
    gone, and the edges it touched as before (U3 review S03)."""
    graph = editors.writes.graph
    for snap in change.nodes_before:
        now = graph.get_node(world_id, snap.id)
        if now is None or _props(now.properties) != _props(snap.properties):
            return False
    if any(graph.get_node(world_id, nid) is not None for nid in change.added_ids):
        return False
    idents = {_ident(e) for e in [*change.edges_added, *change.edges_removed]}
    expected = {_full(e) for e in change.edges_removed}
    return _current(graph, world_id, idents) == expected


def finish_revert(change: ChangeSet, *, world_id: str, editors: Editors) -> None:
    """The search side of a revert whose graph writes already happened (idempotent)."""
    with editors.writes.writing(world_id):
        editors.writes.unindex(world_id, change.added_ids)
        restored = [
            Node(id=s.id, label=s.label, world_id=world_id, properties=s.properties)
            for s in change.nodes_before
        ]
        editors.writes.index([d for d in (_doc(n) for n in restored) if d is not None])


def _current(graph, world_id: str, idents: set[tuple]) -> set[tuple]:
    """The stored edges with one of ``idents``, read around their ends (U3 review C10)."""
    ends = sorted({i[1] for i in idents} | {i[2] for i in idents})
    now: set[tuple] = set()
    for edge in graph.edges_touching(world_id, ends):
        snap = EdgeSnapshot(
            type=edge.type,
            source_id=edge.source_id,
            target_id=edge.target_id,
            properties=dict(edge.properties),
        )
        if _ident(snap) in idents:
            now.add(_full(snap))
    return now


def _edges_edited_since(graph, world_id: str, change: ChangeSet) -> str | None:
    """The first edge identity whose edges no longer equal what ``change`` left, or None.

    Among the identities the change wrote or removed (type, endpoints, kind/id), the
    edges stored now must be exactly the ones it added: a changed weight or rationale, a
    deleted pair, a kind change or a re-added removed edge all differ."""
    idents = {_ident(e) for e in [*change.edges_added, *change.edges_removed]}
    if not idents:
        return None
    expected = {_full(e) for e in change.edges_added}
    now = _current(graph, world_id, idents)
    diff = sorted(now ^ expected)
    return f"{diff[0][0]} {diff[0][1]}->{diff[0][2]}" if diff else None


def _ident(e: EdgeSnapshot) -> tuple:
    k = _key(e)
    return (k.type, k.source_id, k.target_id, json.dumps(k.identity, sort_keys=True, default=str))


def _full(e: EdgeSnapshot) -> tuple:
    return (e.type, e.source_id, e.target_id, json.dumps(e.properties, sort_keys=True, default=str))


def _key(e: EdgeSnapshot) -> EdgeKey:
    edge = Edge(
        type=e.type,
        source_id=e.source_id,
        target_id=e.target_id,
        world_id="",
        properties=e.properties,
    )
    field = edge_identity_field(edge)
    return EdgeKey(
        type=e.type,
        source_id=e.source_id,
        target_id=e.target_id,
        identity={field: e.properties[field]} if field else {},
    )


def _props(props: dict) -> dict:
    return {k: v for k, v in props.items() if k not in ("id", "world_id")}


def _doc(node: Node):
    if node.label == "Knowledge":
        return gm.knowledge_doc(gm.node_to_knowledge(node))
    if node.label == "Entity":
        return gm.entity_doc(gm.node_to_entity(node))
    if node.label == "NPC":
        return gm.npc_doc(gm.node_to_npc(node))
    return None
