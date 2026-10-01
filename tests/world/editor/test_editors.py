"""U3 editor classes (BLM §1, BR-U3-1..14, TP-U3-1/3/6, EX-1/4/5, nfr §1 NFR-3 ②③)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    Coord,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage.persistence import persist_graph
from locus.world.editor import ConnectionKey
from locus.world.editor.writes import check_path
from locus.world.worldfile import WorldFile
from tests.world.editor.helpers import Stack
from tests.world.strategies import edit_ops, editable_worlds

_PBT = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
_unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _towns(*names: str) -> tuple[Stack, dict[str, Region]]:
    stack = Stack()
    regions = {
        n: Region(world_id="w", name=n, level=RegionLevel.TOWN, provenance=_prov()) for n in names
    }
    persist_graph(
        stack.graph,
        stack.search,
        None,
        "w",
        regions=list(regions.values()),
        meta=WorldMeta(id="w", name="W"),
    )
    stack.cache.invalidate("w")
    stack.meter.calls.clear()
    return stack, regions


def _conn(a: Region, b: Region, kind=ConnectionKind.ROUTE, weight=0.6, **kw) -> ConnectionEdge:
    return ConnectionEdge(
        world_id="w",
        source_region_id=a.id,
        target_region_id=b.id,
        kind=kind,
        weight=weight,
        provenance=_prov(),
        **kw,
    )


def _pair_edges(stack: Stack, a: Region, b: Region, kind: str) -> list:
    return [
        e
        for e in stack.graph.get_edges("w", ["CONNECTED_TO"])
        if {e.source_id, e.target_id} == {a.id, b.id} and e.properties.get("kind") == kind
    ]


# --------------------------------------------------------------------------- #
# Connections (BR-U3-10·11, TP-U3-1, EX-4)
# --------------------------------------------------------------------------- #
@_PBT
@given(
    kind=st.sampled_from(list(ConnectionKind)),
    weights=st.lists(_unit, min_size=1, max_size=3),
)
def test_tp_u3_1_a_saved_connection_is_exactly_one_pair(kind, weights) -> None:
    stack, r = _towns("A", "B")
    for w in weights:  # saving the same key again still leaves one pair
        stack.editors.connections.upsert_connection(_conn(r["A"], r["B"], kind, w))
    pair = _pair_edges(stack, r["A"], r["B"], str(kind))
    assert len(pair) == 2
    assert {(e.source_id, e.target_id) for e in pair} == {
        (r["A"].id, r["B"].id),
        (r["B"].id, r["A"].id),
    }
    assert {e.properties["weight"] for e in pair} == {weights[-1]}
    key = ConnectionKey(world_id="w", a_region_id=r["B"].id, b_region_id=r["A"].id, kind=kind)
    assert stack.editors.connections.delete_connection(key) == 2
    assert _pair_edges(stack, r["A"], r["B"], str(kind)) == []


def test_ex4_kinds_are_separate_connections() -> None:
    stack, r = _towns("A", "B")
    c = stack.editors.connections
    c.upsert_connection(_conn(r["A"], r["B"], weight=0.6))
    c.upsert_connection(_conn(r["A"], r["B"], weight=0.8))
    route = _pair_edges(stack, r["A"], r["B"], "route")
    assert len(route) == 2 and {e.properties["weight"] for e in route} == {0.8}
    c.upsert_connection(_conn(r["A"], r["B"], ConnectionKind.RIVER, 0.4))
    assert len(stack.graph.get_edges("w", ["CONNECTED_TO"])) == 4
    c.delete_connection(
        ConnectionKey(world_id="w", a_region_id=r["A"].id, b_region_id=r["B"].id, kind="route")
    )
    assert [e.properties["kind"] for e in stack.graph.get_edges("w", ["CONNECTED_TO"])] == [
        "river",
        "river",
    ]


def test_change_kind_keeps_weight_rationale_and_prior() -> None:
    stack, r = _towns("A", "B")
    c = stack.editors.connections
    c.upsert_connection(_conn(r["A"], r["B"], weight=0.3, rationale="pass", wiki_prior_ref="p1"))
    key = ConnectionKey(world_id="w", a_region_id=r["A"].id, b_region_id=r["B"].id, kind="route")
    c.change_connection_kind(key, ConnectionKind.RIVER)
    river = _pair_edges(stack, r["A"], r["B"], "river")
    assert len(river) == 2 and _pair_edges(stack, r["A"], r["B"], "route") == []
    assert {
        (e.properties["weight"], e.properties["rationale"], e.properties["wiki_prior_ref"])
        for e in river
    } == {(0.3, "pass", "p1")}
    c.upsert_connection(_conn(r["A"], r["B"]))  # a route again
    with pytest.raises(ValueError):  # the river already exists
        c.change_connection_kind(key, ConnectionKind.RIVER)


def test_set_prior_ref_writes_both_directions() -> None:
    """FD 검토 R-11: a connection's prior reference changes for the pair."""
    stack, r = _towns("A", "B")
    stack.editors.connections.upsert_connection(_conn(r["A"], r["B"], wiki_prior_ref="old"))
    key = ConnectionKey(world_id="w", a_region_id=r["A"].id, b_region_id=r["B"].id, kind="route")
    stack.editors.connections.set_prior_ref(key, None)
    assert [
        e.properties.get("wiki_prior_ref") for e in _pair_edges(stack, r["A"], r["B"], "route")
    ] == [None, None]


def test_connection_checks() -> None:
    stack, r = _towns("A", "B")
    c = stack.editors.connections
    with pytest.raises(ValueError):  # BR-U3-11 self connection
        c.upsert_connection(_conn(r["A"], r["A"]))
    ghost = Region(world_id="w", name="Ghost", level=RegionLevel.TOWN, provenance=_prov())
    with pytest.raises(LookupError):  # BR-U3-6
        c.upsert_connection(_conn(r["A"], ghost))
    with pytest.raises(LookupError):
        c.delete_connection(
            ConnectionKey(world_id="w", a_region_id=r["A"].id, b_region_id=r["B"].id, kind="river")
        )


def test_connection_save_is_one_delete_and_one_upsert() -> None:
    """nfr §1 NFR-3 ②: FD writes only; ``_written`` adds the meta write."""
    stack, r = _towns("A", "B")
    stack.editors.connections.upsert_connection(_conn(r["A"], r["B"]))
    assert stack.meter.calls == ["delete_edges", "upsert_edges", "upsert_nodes"]


# --------------------------------------------------------------------------- #
# Regions (BR-U3-1·7, TP-U3-3, EX-1)
# --------------------------------------------------------------------------- #
@_PBT
@given(
    description=st.one_of(st.none(), st.text(max_size=12)),
    position=st.one_of(st.none(), st.builds(Coord, x=_unit, y=_unit)),
)
def test_tp_u3_3_region_replace_round_trips(description, position) -> None:
    """TP-U3-3: what the editor writes is what the world reads; a cleared field is gone."""
    stack, r = _towns("A")
    full = r["A"].model_copy(update={"description": "old", "position": Coord(x=0.5, y=0.5)})
    stack.editors.regions.upsert_region(full)
    edited = full.model_copy(update={"description": description, "position": position})
    stack.editors.regions.upsert_region(edited)
    assert stack.cache.get("w").regions_by_id[edited.id] == edited


def test_ex1_parent_cycle_is_refused_and_parent_can_be_cleared() -> None:
    stack, r = _towns("Riverton", "Mill")
    regions = stack.editors.regions
    mill = r["Mill"].model_copy(update={"parent_id": r["Riverton"].id})
    regions.upsert_region(mill)
    with pytest.raises(ValueError):  # Riverton under its own child
        regions.upsert_region(r["Riverton"].model_copy(update={"parent_id": mill.id}))
    with pytest.raises(ValueError):  # its own parent
        regions.upsert_region(r["Riverton"].model_copy(update={"parent_id": r["Riverton"].id}))
    regions.upsert_region(mill.model_copy(update={"parent_id": None}))
    assert stack.cache.get("w").regions_by_id[mill.id].parent_id is None
    assert stack.graph.get_edges("w", ["CONTAINS"]) == []


def test_reparenting_rewrites_contains() -> None:
    stack, r = _towns("A", "B", "C")
    regions = stack.editors.regions
    regions.upsert_region(r["C"].model_copy(update={"parent_id": r["A"].id}))
    regions.upsert_region(r["C"].model_copy(update={"parent_id": r["B"].id}))
    assert [(e.source_id, e.target_id) for e in stack.graph.get_edges("w", ["CONTAINS"])] == [
        (r["B"].id, r["C"].id)
    ]


def test_create_region_refuses_an_existing_id_and_a_missing_parent() -> None:
    stack, r = _towns("A")
    with pytest.raises(ValueError):
        stack.editors.regions.create_region(r["A"])
    orphan = Region(
        world_id="w", name="O", level=RegionLevel.TOWN, parent_id="nope", provenance=_prov()
    )
    with pytest.raises(LookupError):
        stack.editors.regions.create_region(orphan)


def test_path_and_body_must_match() -> None:  # BR-U3-5
    check_path("w", "r1", "w", "r1")
    with pytest.raises(ValueError):
        check_path("w", "r1", "other", "r1")
    with pytest.raises(ValueError):
        check_path("w", "r1", "w", "r2")


# --------------------------------------------------------------------------- #
# Knowledge and scopes (BR-U3-12·13·14, EX-5)
# --------------------------------------------------------------------------- #
def test_ex5_knowledge_scopes_and_the_unscoped_list() -> None:
    stack, r = _towns("Hollow", "Riverton")
    k = stack.editors.knowledge
    item = Knowledge(world_id="w", statement="the well ran dry", title="well", provenance=_prov())
    k.create_knowledge(item, r["Hollow"].id)
    scopes = [s for s in stack.cache.get("w").kg.scopes if s.knowledge_id == item.id]
    assert [(s.region_id, str(s.scope_type)) for s in scopes] == [(r["Hollow"].id, "direct")]

    k.upsert_knowledge(item.model_copy(update={"statement": "the well is dry again"}))
    snap = stack.cache.get("w")
    assert [s.region_id for s in snap.kg.scopes if s.knowledge_id == item.id] == [r["Hollow"].id]
    assert "again" in stack.search.docs[("w", item.id)].text  # re-indexed

    k.set_scopes("w", item.id, [])
    assert [u.id for u in k.list_unscoped("w")] == [item.id]
    k.set_scopes("w", item.id, [r["Riverton"].id])
    assert k.list_unscoped("w") == []
    assert [s.region_id for s in stack.cache.get("w").kg.scopes] == [r["Riverton"].id]


def test_set_scopes_is_at_most_one_delete_and_one_upsert() -> None:
    """nfr §1 NFR-3 ③."""
    stack, r = _towns("A", "B", "C")
    item = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    stack.editors.knowledge.create_knowledge(item, r["A"].id)
    stack.meter.calls.clear()
    stack.editors.knowledge.set_scopes("w", item.id, [r["B"].id, r["C"].id])
    assert stack.meter.calls == ["delete_edges", "upsert_edges", "upsert_nodes"]


def test_scopes_need_existing_regions_and_knowledge() -> None:
    stack, r = _towns("A")
    with pytest.raises(LookupError):
        stack.editors.knowledge.set_scopes("w", "nope", [r["A"].id])
    item = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    with pytest.raises(LookupError):
        stack.editors.knowledge.create_knowledge(item, "nope")


def test_kind_deletes_clean_up_search_on_retry() -> None:
    """NFR R-01: a cut between the graph and the search delete is cleaned up when the
    same delete is sent again (it answers 404, the document is gone)."""
    stack, r = _towns("A")
    item = Knowledge(world_id="w", statement="s", title="t", provenance=_prov())
    stack.editors.knowledge.create_knowledge(item, r["A"].id)
    stack.search.fail_on_delete = RuntimeError("opensearch down")
    with pytest.raises(RuntimeError):
        stack.editors.knowledge.delete_knowledge("w", item.id)
    assert stack.graph.get_node("w", item.id) is None and ("w", item.id) in stack.search.docs
    stack.search.fail_on_delete = None
    with pytest.raises(LookupError):
        stack.editors.knowledge.delete_knowledge("w", item.id)
    assert ("w", item.id) not in stack.search.docs


# --------------------------------------------------------------------------- #
# TP-U3-6: any edit sequence still saves and loads to the same World File
# --------------------------------------------------------------------------- #
def _apply(stack: Stack, op: tuple) -> None:
    name, i, j, k, x = op
    snap = stack.cache.get("w")
    regions, knowledge, conns = snap.topo.regions, snap.kg.knowledge, snap.topo.connections
    if not regions:
        return
    a, b = regions[i % len(regions)], regions[j % len(regions)]
    ed = stack.editors
    if name == "describe_region":
        ed.regions.upsert_region(a.model_copy(update={"description": None if k % 2 else f"d{k}"}))
    elif name == "set_scopes" and knowledge:
        picks = [r.id for r in regions[: k % (len(regions) + 1)]]
        ed.knowledge.set_scopes("w", knowledge[i % len(knowledge)].id, picks)
    elif name == "save_connection" and a.id != b.id:
        kind = list(ConnectionKind)[k % len(ConnectionKind)]
        ed.connections.upsert_connection(_conn(a, b, kind, x))
    elif name == "delete_connection" and conns:
        ed.connections.delete_connection(ConnectionKey.of(conns[i % len(conns)]))
    elif name == "delete_knowledge" and knowledge:
        ed.knowledge.delete_knowledge("w", knowledge[i % len(knowledge)].id)
    elif name == "delete_region" and len(regions) > 1:
        ed.regions.delete_region("w", a.id)
    elif name == "move_npc" and snap.npcs:
        npc = snap.npcs[i % len(snap.npcs)]
        ed.npcs.upsert_npc(npc.model_copy(update={"home_region_id": b.id}))


@_PBT
@given(file=editable_worlds(), ops=edit_ops())
def test_tp_u3_6_edits_keep_the_world_file_round_trip(file: WorldFile, ops: list) -> None:
    stack = Stack(file)
    for op in ops:
        _apply(stack, op)
    out = stack.exporter.export("w")
    again = Stack(out)
    reread = again.exporter.export("w")
    stamp = {"exported_at": None}
    assert reread.model_copy(update=stamp).to_json() == out.model_copy(update=stamp).to_json()
