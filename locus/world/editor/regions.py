"""RegionEditor — add, replace and delete regions (U3, BLM §1.2·§1.3, Q1=A).

Deleting a region tidies what pointed at it: children move to its parent, entities
lose their location, its scopes go (the knowledge stays), its NPCs and connections are
deleted, then the region. Inside each step the write that the retry plan selects by
goes last (BR-U3-8 〔Step 1.3 정정〕), so a cut leaves no dangling id and calling the
delete again finishes it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from locus.shared.models import Region, WorldSnapshot
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import EdgeKey
from locus.world.editor.models import (
    ConnectionKey,
    ConnectionView,
    EditorRegionView,
    NameRef,
    RegionDeletePlan,
    RegionDeleteReport,
    RegionInUseError,
    ScopedKnowledge,
)
from locus.world.editor.writes import EditorWrites, require_region
from locus.world.wiki.admin import prior_ref_view


class RegionEditor:
    def __init__(self, writes: EditorWrites) -> None:
        self._w = writes

    # -- add / replace (BR-U3-7) ------------------------------------------ #
    def create_region(self, region: Region) -> Region:
        if self._w.node(region.world_id, region.id, "Region") is not None:
            raise ValueError(f"region already exists: {region.id}")
        return self.upsert_region(region)

    def upsert_region(self, region: Region) -> Region:
        """Replace the region; a changed parent rewrites ``CONTAINS`` (new edge first,
        then the property, then the old edge)."""
        old = self._w.node(region.world_id, region.id, "Region")
        old_parent = old.properties.get("parent_id") if old is not None else None
        if region.parent_id and region.parent_id != old_parent:
            self._check_parent(region)
        with self._w.writing(region.world_id):
            if old is None:  # a new region: the node first, so CONTAINS can match it
                self._w.replace([gm.region_to_node(region)])
                self._w.graph.upsert_edges(gm.contains_edges([region]))
                return region
            if region.parent_id and region.parent_id != old_parent:
                self._w.graph.upsert_edges(gm.contains_edges([region]))
            self._w.replace([gm.region_to_node(region)])
            if old_parent and old_parent != region.parent_id:
                self._w.graph.delete_edges(
                    region.world_id,
                    [EdgeKey(type="CONTAINS", source_id=old_parent, target_id=region.id)],
                )
        return region

    def _check_parent(self, region: Region) -> None:
        assert region.parent_id is not None
        if region.parent_id == region.id:
            raise ValueError("a region cannot be its own parent")
        snapshot = self._w.snapshot(region.world_id)
        require_region(snapshot, region.parent_id)
        if region.parent_id in _descendants(snapshot, region.id):
            raise ValueError("a region cannot move under its own descendant")

    # -- delete (Q1=A, Q2=A) ---------------------------------------------- #
    def plan_region_delete(self, world_id: str, region_id: str) -> RegionDeletePlan:
        return _plan(self._w.snapshot(world_id), region_id)

    def delete_region(
        self,
        world_id: str,
        region_id: str,
        *,
        protected: Mapping[str, Sequence[str]] | None = None,
    ) -> RegionDeleteReport:
        """``protected`` maps a region where an open session's player stands to those
        session ids (Q2=A, filled by the router under the GM leases)."""
        blocked = list((protected or {}).get(region_id, []))
        if blocked:
            raise RegionInUseError(region_id, blocked)
        snapshot = self._w.snapshot(world_id)
        plan = _plan(snapshot, region_id)  # again: the world may have changed since the dialog
        g = self._w.graph
        with self._w.writing(world_id):
            children = [snapshot.regions_by_id[c.id] for c in plan.children]
            if children:  # ① new CONTAINS -> parent_id -> old CONTAINS
                moved = [c.model_copy(update={"parent_id": plan.new_parent_id}) for c in children]
                if plan.new_parent_id:
                    g.upsert_edges(gm.contains_edges(moved))
                self._w.replace([gm.region_to_node(c) for c in moved])
                g.delete_edges(world_id, [_edge("CONTAINS", region_id, c.id) for c in children])
            entities = [e for e in snapshot.kg.entities if e.located_in == region_id]
            if entities:  # ② LOCATED_IN -> located_in
                g.delete_edges(world_id, [_edge("LOCATED_IN", e.id, region_id) for e in entities])
                self._w.replace(
                    [gm.entity_to_node(e.model_copy(update={"located_in": None})) for e in entities]
                )
            scoped = [s.knowledge_id for s in snapshot.kg.scopes if s.region_id == region_id]
            if scoped:  # ③ scopes go, the knowledge stays
                g.delete_edges(world_id, [_edge("SCOPED_TO", k, region_id) for k in scoped])
            npc_ids = [n.id for n in plan.npcs]
            if npc_ids:  # ④ search documents, then the nodes (DETACH takes LIVES_IN)
                self._w.unindex(world_id, npc_ids)
                for nid in npc_ids:
                    g.delete_node(world_id, nid)
            if plan.connections:  # ⑤ both directions
                g.delete_edges(world_id, _connection_edges(plan.connections))
            g.delete_node(world_id, region_id)  # ⑥
        return RegionDeleteReport(**plan.model_dump(), deleted_ids=[region_id, *npc_ids])

    # -- read -------------------------------------------------------------- #
    def editor_view(self, world_id: str, region_id: str) -> EditorRegionView:
        snapshot = self._w.snapshot(world_id)
        region = require_region(snapshot, region_id)
        names = {r.id: r.name for r in snapshot.topo.regions}
        priors = {p.id: p for p in snapshot.kg.priors}
        connections = [
            ConnectionView(
                key=ConnectionKey.of(c),
                other_region_id=c.target_region_id,
                other_region_name=names.get(c.target_region_id, c.target_region_id),
                weight=c.weight,
                rationale=c.rationale,
                prior=prior_ref_view(c.wiki_prior_ref, priors) if c.wiki_prior_ref else None,
            )
            for c in snapshot.topo.connections
            if c.source_region_id == region_id
        ]
        scopes: dict[str, list[str]] = {}
        for s in snapshot.kg.scopes:
            scopes.setdefault(s.knowledge_id, []).append(s.region_id)
        knowledge = [
            ScopedKnowledge(knowledge=k, scope_region_ids=scopes[k.id])
            for k in snapshot.kg.knowledge
            if region_id in scopes.get(k.id, [])
        ]
        return EditorRegionView(
            region=region,
            children=_children(snapshot, region_id),
            connections=connections,
            knowledge=knowledge,
            npcs=list(snapshot.npcs_by_region.get(region_id, [])),
        )


# --------------------------------------------------------------------------- #
def _edge(kind: str, source: str, target: str) -> EdgeKey:
    return EdgeKey(type=kind, source_id=source, target_id=target)


def _connection_edges(keys: list[ConnectionKey]) -> list[EdgeKey]:
    out: list[EdgeKey] = []
    for k in keys:
        ident = {"kind": str(k.kind)}
        out.append(
            EdgeKey(
                type="CONNECTED_TO",
                source_id=k.a_region_id,
                target_id=k.b_region_id,
                identity=ident,
            )
        )
        out.append(
            EdgeKey(
                type="CONNECTED_TO",
                source_id=k.b_region_id,
                target_id=k.a_region_id,
                identity=ident,
            )
        )
    return out


def _children(snapshot: WorldSnapshot, region_id: str) -> list[NameRef]:
    return [
        NameRef(id=r.id, name=r.name) for r in snapshot.topo.regions if r.parent_id == region_id
    ]


def _descendants(snapshot: WorldSnapshot, region_id: str) -> set[str]:
    by_parent: dict[str, list[str]] = {}
    for r in snapshot.topo.regions:
        if r.parent_id:
            by_parent.setdefault(r.parent_id, []).append(r.id)
    seen: set[str] = set()
    stack = [region_id]
    while stack:
        for child in by_parent.get(stack.pop(), []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def _plan(snapshot: WorldSnapshot, region_id: str) -> RegionDeletePlan:
    region = require_region(snapshot, region_id)
    keys: list[ConnectionKey] = []
    for c in snapshot.topo.connections:
        if region_id in (c.source_region_id, c.target_region_id):
            key = ConnectionKey.of(c)
            if key not in keys:
                keys.append(key)
    scopes: dict[str, set[str]] = {}
    for s in snapshot.kg.scopes:
        scopes.setdefault(s.knowledge_id, set()).add(s.region_id)
    unscope: list[NameRef] = []
    removed: list[NameRef] = []
    for k in snapshot.kg.knowledge:
        regions = scopes.get(k.id, set())
        if region_id not in regions:
            continue
        ref = NameRef(id=k.id, name=k.title or k.id)
        (removed if (regions - {region_id}) or k.is_global else unscope).append(ref)
    return RegionDeletePlan(
        region_id=region_id,
        region_name=region.name,
        new_parent_id=region.parent_id,
        children=_children(snapshot, region_id),
        connections=keys,
        npcs=[NameRef(id=n.id, name=n.name) for n in snapshot.npcs_by_region.get(region_id, [])],
        knowledge_to_unscope=unscope,
        knowledge_scope_removed=removed,
        entities_unlocated=[
            NameRef(id=e.id, name=e.name) for e in snapshot.kg.entities if e.located_in == region_id
        ],
    )
