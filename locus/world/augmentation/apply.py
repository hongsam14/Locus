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
from locus.world.editor import Editors
from locus.world.refs import ConnectionKey

_REF_KIND = {  # dangling field -> the label its new reference must have
    "parent_id": "Region",
    "located_in": "Region",
    "wiki_prior_ref": "WikiPrior",
    "derived_from_prior_ids": "WikiPrior",
    "about_entity_ids": "Entity",
}


class _Unchanged:
    """``_write``'s answer for a confirm that left every value as it was (V7, R-09)."""


UNCHANGED = _Unchanged()


def apply_answer(
    issue: Issue,
    question: AugmentationQuestion,
    answer: AugmentationAnswer,
    *,
    world_id: str,
    editors: Editors,
) -> ChangeSet | None:
    """Apply ``answer`` to ``question``'s target; None for ignore, and for a confirm that
    changes no value (nothing written, so nothing to undo — V7, R-09)."""
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
    labels = {target.id: _LABEL_OF.get(issue.target_kind)}  # by kind (V7 code review #4)
    nodes_before = _nodes(editors, world_id, nodes, labels)
    before = _edges(graph, world_id, watch)

    added = _write(issue, target.id, action, answer, world_id=world_id, editors=editors, cs=cs)
    if isinstance(added, _Unchanged):
        return None
    cs.added_ids = added
    labels.update(dict.fromkeys(added, "Knowledge"))  # an answer only adds knowledge
    nodes_after = _nodes(editors, world_id, [*nodes, *added], labels)
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
    if issue.target_kind == "connection" and issue.connection is not None:
        return [], [issue.connection.a_region_id, issue.connection.b_region_id]
    return [target_id], [target_id]


def _write(
    issue, target_id, action, answer, *, world_id, editors: Editors, cs
) -> list[str] | _Unchanged:
    """The writes of BLM §4.2's table; returns the ids of nodes it created, or
    ``UNCHANGED`` for a confirm that left the value as it was."""
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
        if not editors.delete_any(world_id, target_id, issue.target_kind):
            raise LookupError(f"node not found: {target_id}")
        return []
    if _changes_nothing(issue, target_id, action, answer, world_id, editors):
        raise ValueError("the answer changes nothing")  # before any write (review #16)
    if kind in (IssueType.LOW_CONFIDENCE, IssueType.WIKI_CONFLICT):
        if not _confirm_or_edit(issue, target_id, action, answer, world_id, editors):
            return UNCHANGED
    elif kind == IssueType.ORPHAN:  # edit: place it in a region
        entity = _entity(editors, world_id, target_id)
        editors.entities.update_entity(entity.model_copy(update={"located_in": _region(answer)}))
    elif kind == IssueType.UNSCOPED:  # edit: scope it to a region
        editors.knowledge.set_scopes(world_id, target_id, [_region(answer)])
    elif kind == IssueType.DANGLING:
        _repoint(issue, target_id, action, answer, world_id, editors)
    return []


def _confirm_or_edit(issue, target_id, action, answer, world_id, editors: Editors) -> bool:
    """Write the confirm or the edit; False when a confirm leaves the value as it is.

    V7 (BR-V7-22): what would change is worked out first. An edit that changes nothing
    (empty fields, or the values already there) is refused before any write; a confirm
    is "keep it as it is" and never refused (FD review R-03), it just writes nothing."""
    entity = issue.target_kind == "entity"  # B3: entity targets edit the entity
    item = (
        _entity(editors, world_id, target_id)
        if entity
        else _knowledge(editors, world_id, target_id)
    )
    update: dict = {}
    if action == AnswerAction.CONFIRM:
        conf = answer.confidence if answer.confidence is not None else max(item.confidence, 0.9)
        update["confidence"] = conf
    else:
        # compared as they would be stored: trimmed, and a blank field is no field
        # (V7 code review #15; the editor keeps titles trimmed)
        statement = (answer.statement or "").strip()
        title = (answer.title or "").strip()
        if statement:  # an entity's description comes in the statement field
            update["description" if entity else "statement"] = statement
        if title and not entity:  # an entity has no title (U8 #13)
            update["title"] = title
        if answer.confidence is not None:
            update["confidence"] = answer.confidence
    changed = {f: v for f, v in update.items() if getattr(item, f) != v}
    if not changed:
        if action == AnswerAction.CONFIRM:
            return False
        raise ValueError("the answer changes nothing")
    if isinstance(item, Knowledge):
        editors.knowledge.upsert_knowledge(item.model_copy(update=changed))
    else:
        editors.entities.update_entity(item.model_copy(update=changed))
    return True


_LABEL_OF = {"knowledge": "Knowledge", "entity": "Entity", "region": "Region"}


def _changes_nothing(issue: Issue, target_id, action, answer, world_id, editors) -> bool:
    """A place, scope or re-point answer that would leave the value as it already is —
    a question gone stale after an edit in the inspector (V7 code review #16)."""
    kind = IssueType(issue.type)
    if kind in (IssueType.ORPHAN, IssueType.UNSCOPED) and not answer.region_id:
        return False  # the missing region is refused on its own ("needs a region")
    if kind == IssueType.ORPHAN:
        return _entity(editors, world_id, target_id).located_in == answer.region_id
    if kind not in (IssueType.UNSCOPED, IssueType.DANGLING):
        return False
    snapshot = editors.writes.snapshot(world_id)
    if kind == IssueType.UNSCOPED:
        held = {s.region_id for s in snapshot.kg.scopes if s.knowledge_id == target_id}
        return held == {answer.region_id}
    field = issue.field or ""
    ref = answer.ref_id if action == AnswerAction.EDIT else None
    if field == "parent_id":
        region = snapshot.regions_by_id.get(target_id)
        return region is not None and region.parent_id == ref
    if field == "located_in":
        entity = next((e for e in snapshot.kg.entities if e.id == target_id), None)
        return entity is not None and entity.located_in == ref
    if field == "wiki_prior_ref":
        if issue.connection is None:
            return False
        key = issue.connection.normalized()
        edge = next(
            (
                c
                for c in snapshot.topo.connections
                if (k := ConnectionKey.of(c)).a_region_id == key.a_region_id
                and k.b_region_id == key.b_region_id
                and k.kind == key.kind
            ),
            None,
        )
        return edge is not None and edge.wiki_prior_ref == ref
    item = next((k for k in snapshot.kg.knowledge if k.id == target_id), None)
    ids = list(getattr(item, field, None) or []) if item is not None else []
    return issue.broken_id not in ids and (ref is None or ref in ids)


def _repoint(issue: Issue, target_id, action, answer, world_id, editors: Editors) -> None:
    """dangling: edit -> the field points at ``ref_id``; remove -> the field is cleared
    (for a list, only ``broken_id`` goes)."""
    field = issue.field or ""
    ref = None
    if action == AnswerAction.EDIT:
        ref = answer.ref_id
        kind = _REF_KIND.get(field)
        node = editors.writes.graph.get_node(world_id, ref, label=kind) if ref else None
        if node is None or node.label != kind:
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
        if issue.connection is None:
            raise ValueError("a connection answer needs its connection key")
        key = issue.connection.model_copy(update={"world_id": world_id})
        editors.connections.set_prior_ref(key, ref)
    else:
        editors.knowledge.repoint(world_id, target_id, field, issue.broken_id or "", ref)


# --------------------------------------------------------------------------- #
def revert(change: ChangeSet, *, world_id: str, editors: Editors) -> None:
    """Undo ``change``. Refused, with nothing written, when a node it touched was edited
    after it (or a node it made is gone), or when an edge it wrote or removed has changed
    since — a change outside this run. The edge check covers answers whose target is a
    connection or a scope, which record no node (U3 review #4, BR-U3-27).

    A revert that passed these checks once (``revert_started``) and was cut part-way
    finds each item either as the change left it or as it was before; anything else is
    still an outside edit. Every write below is idempotent, so the same revert sent again
    redoes them all and ends where an uncut one would (U8 review #6, U3 review S03)."""
    graph = editors.writes.graph
    resuming = change.revert_started
    before = {s.id: _props(s.properties) for s in change.nodes_before}
    for snap in change.nodes_after:
        now = graph.get_node(world_id, snap.id, label=snap.label)
        if now is not None and _props(now.properties) == _props(snap.properties):
            continue
        if resuming and now is None and snap.id in change.added_ids:
            continue  # a node it made, already deleted by the cut revert
        if resuming and now is not None and before.get(snap.id) == _props(now.properties):
            continue  # already restored by the cut revert
        raise RevertConflictError(f"{snap.id} was edited after this change")
    edited = _edges_edited_since(graph, world_id, change, resuming=resuming)
    if edited:
        raise RevertConflictError(f"{edited} was edited after this change")
    change.revert_started = True  # past the checks: a retry may resume (U3 review S03)
    with editors.writes.writing(world_id):
        graph.delete_edges(world_id, [_key(e) for e in change.edges_added])
        labels = {s.id: s.label for s in change.nodes_after}
        for nid in change.added_ids:  # by its kind; an id with no snapshot, any kind
            graph.delete_node(world_id, nid, label=labels.get(nid))
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


def _nodes(
    editors: Editors, world_id: str, ids: list[str], labels: dict[str, str | None]
) -> dict[str, NodeSnapshot]:
    out: dict[str, NodeSnapshot] = {}
    for nid in dict.fromkeys(ids):
        node = editors.writes.graph.get_node(world_id, nid, label=labels.get(nid))
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


def _edges_edited_since(
    graph, world_id: str, change: ChangeSet, *, resuming: bool = False
) -> str | None:
    """The first edge identity whose edges no longer equal what ``change`` left, or None.

    Among the identities the change wrote or removed (type, endpoints, kind/id), the
    edges stored now must be exactly the ones it added: a changed weight or rationale, a
    deleted pair, a kind change or a re-added removed edge all differ. Resuming a cut
    revert, each stored edge may be one the change added or one it removed (half undone);
    only an edge that is neither is an outside edit (U8 review #6)."""
    idents = {_ident(e) for e in [*change.edges_added, *change.edges_removed]}
    if not idents:
        return None
    expected = {_full(e) for e in change.edges_added}
    now = _current(graph, world_id, idents)
    if resuming:
        diff = sorted(now - expected - {_full(e) for e in change.edges_removed})
    else:
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
