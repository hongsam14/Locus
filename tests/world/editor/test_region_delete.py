"""U3 region delete (BR-U3-8/9/16, TP-U3-2/2a, EX-2/3, nfr §1 NFR-3 ①)."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from locus.shared.models import (
    NPC,
    ConnectionEdge,
    ConnectionKind,
    Entity,
    EntityType,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    ScopeLink,
    ScopeType,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage.persistence import persist_graph
from locus.world.editor import RegionInUseError
from locus.world.worldfile import WorldFile
from tests.world.editor.helpers import Stack
from tests.world.strategies import editable_worlds

_PBT = settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _unscoped(stack: Stack) -> set[str]:
    return {k.id for k in stack.editors.knowledge.list_unscoped("w")}


# --------------------------------------------------------------------------- #
# TP-U3-2: nothing points at the deleted region, nothing else is lost
# --------------------------------------------------------------------------- #
@_PBT
@given(file=editable_worlds(), pick=st.integers(min_value=0, max_value=10))
def test_tp_u3_2_delete_leaves_no_reference_and_loses_no_knowledge(
    file: WorldFile, pick: int
) -> None:
    stack = Stack(file)
    before = stack.cache.get("w")
    region = before.topo.regions[pick % len(before.topo.regions)]
    unscoped_before = _unscoped(stack)
    plan = stack.editors.regions.plan_region_delete("w", region.id)

    report = stack.editors.regions.delete_region("w", region.id)

    after = stack.cache.get("w")
    assert stack.dangling() == []
    assert region.id not in after.regions_by_id
    assert all(
        region.id not in (c.source_region_id, c.target_region_id) for c in after.topo.connections
    )
    assert all(s.region_id != region.id for s in after.kg.scopes)
    assert all(e.located_in != region.id for e in after.kg.entities)
    assert len(after.kg.knowledge) == len(before.kg.knowledge)  # knowledge is never lost
    for child in plan.children:  # children moved up, not lost
        assert after.regions_by_id[child.id].parent_id == region.parent_id
    assert _unscoped(stack) == unscoped_before | {k.id for k in plan.knowledge_to_unscope}
    assert set(report.deleted_ids) == {region.id, *(n.id for n in plan.npcs)}


# --------------------------------------------------------------------------- #
# TP-U3-2a: a cut at any write leaves no dangling id; a retry finishes the job
# --------------------------------------------------------------------------- #
@_PBT
@given(file=editable_worlds(), pick=st.integers(min_value=0, max_value=10))
def test_tp_u3_2a_cut_at_every_write_then_retry(file: WorldFile, pick: int) -> None:
    reference = Stack(file)
    region_id = reference.cache.get("w").topo.regions[pick % len(file.regions)].id
    reference.editors.regions.delete_region("w", region_id)
    writes = len(reference.meter.calls)
    expected = reference.state()

    for n in range(writes):
        stack = Stack(file)
        stack.meter.cut_at = n
        with pytest.raises(RuntimeError, match="cut at write"):
            stack.editors.regions.delete_region("w", region_id)
        assert stack.dangling() == [], f"cut at write {n}"
        try:  # the retry: the same request again
            stack.editors.regions.delete_region("w", region_id)
        except LookupError:  # the cut hit the last write (WorldMeta): already gone
            pass
        assert stack.state() == expected, f"cut at write {n}"


# --------------------------------------------------------------------------- #
# EX-2 / EX-3 and the write count (NFR-3 ①)
# --------------------------------------------------------------------------- #
def _aldermoor() -> tuple[Stack, dict]:
    stack = Stack()
    world = Region(world_id="w", name="Aldermoor", level=RegionLevel.PROVINCE, provenance=_prov())
    riverton = Region(
        world_id="w",
        name="Riverton",
        level=RegionLevel.TOWN,
        parent_id=world.id,
        provenance=_prov(),
    )
    mill = Region(
        world_id="w",
        name="Mill",
        level=RegionLevel.DISTRICT,
        parent_id=riverton.id,
        provenance=_prov(),
    )
    hollow = Region(world_id="w", name="Hollow", level=RegionLevel.TOWN, provenance=_prov())
    ford = Region(world_id="w", name="Ford", level=RegionLevel.TOWN, provenance=_prov())
    conns = [
        ConnectionEdge(
            world_id="w",
            source_region_id=a.id,
            target_region_id=b.id,
            kind=ConnectionKind.ROUTE,
            weight=0.6,
            provenance=_prov(),
        )
        for x, y in ((riverton, hollow), (riverton, ford))
        for a, b in ((x, y), (y, x))
    ]
    k1 = Knowledge(world_id="w", statement="the mill wheel", title="k1", provenance=_prov())
    k2 = Knowledge(world_id="w", statement="river trade", title="k2", provenance=_prov())
    scopes = [
        ScopeLink(
            world_id="w", knowledge_id=k1.id, region_id=riverton.id, scope_type=ScopeType.DIRECT
        ),
        ScopeLink(
            world_id="w", knowledge_id=k2.id, region_id=riverton.id, scope_type=ScopeType.DIRECT
        ),
        ScopeLink(
            world_id="w", knowledge_id=k2.id, region_id=hollow.id, scope_type=ScopeType.DIRECT
        ),
    ]
    tomas = Entity(
        world_id="w",
        name="Tomas",
        entity_type=EntityType.PERSON,
        located_in=riverton.id,
        provenance=_prov(),
    )
    npcs = [
        NPC(
            world_id="w",
            name=n,
            role="r",
            description="d",
            home_region_id=riverton.id,
            provenance=_prov(),
        )
        for n in ("Ada", "Bo")
    ]
    persist_graph(
        stack.graph,
        stack.search,
        None,
        "w",
        regions=[world, riverton, mill, hollow, ford],
        connections=conns,
        knowledge=[k1, k2],
        scopes=scopes,
        entities=[tomas],
        npcs=npcs,
        meta=WorldMeta(id="w", name="W"),
    )
    stack.cache.invalidate("w")
    stack.meter.calls.clear()
    names = {
        "world": world,
        "riverton": riverton,
        "mill": mill,
        "hollow": hollow,
        "k1": k1,
        "k2": k2,
        "tomas": tomas,
        "npcs": npcs,
    }
    return stack, names


def test_ex2_delete_riverton() -> None:
    """EX-2: Mill moves under Aldermoor, two NPCs and four connection edges go, k1 is
    unscoped, k2 keeps Hollow; the report carries every count."""
    stack, w = _aldermoor()
    plan = stack.editors.regions.plan_region_delete("w", w["riverton"].id)
    assert plan.new_parent_id == w["world"].id
    assert [c.name for c in plan.children] == ["Mill"]
    assert sorted(n.name for n in plan.npcs) == ["Ada", "Bo"]
    assert len(plan.connections) == 2
    assert [k.name for k in plan.knowledge_to_unscope] == ["k1"]
    assert [k.name for k in plan.knowledge_scope_removed] == ["k2"]
    assert [e.name for e in plan.entities_unlocated] == ["Tomas"]

    report = stack.editors.regions.delete_region("w", w["riverton"].id)
    snap = stack.cache.get("w")
    assert snap.regions_by_id[w["mill"].id].parent_id == w["world"].id
    assert ("CONTAINS", w["world"].id, w["mill"].id) in {
        (e.type, e.source_id, e.target_id) for e in stack.graph.get_edges("w", ["CONTAINS"])
    }
    assert snap.npcs == [] and snap.topo.connections == []
    assert [k.id for k in stack.editors.knowledge.list_unscoped("w")] == [w["k1"].id]
    assert {s.region_id for s in snap.kg.scopes if s.knowledge_id == w["k2"].id} == {w["hollow"].id}
    assert snap.kg.entities[0].located_in is None
    assert report.model_dump(exclude={"deleted_ids"}) == plan.model_dump()
    assert all(("w", n.id) not in stack.search.docs for n in w["npcs"])


def test_region_delete_write_count_is_nine_plus_npcs() -> None:
    """nfr §1 NFR-3 ① (〔Step 1.3 정정〕 R-02): FD-step writes are 9 + NPC count, one
    batched call per step; ``_written`` adds the meta write on its own line."""
    stack, w = _aldermoor()
    stack.editors.regions.delete_region("w", w["riverton"].id)
    *fd_writes, meta = stack.meter.calls
    assert fd_writes == [
        "upsert_edges",
        "replace_nodes",
        "delete_edges",  # ① children
        "delete_edges",
        "replace_nodes",  # ② entities
        "delete_edges",  # ③ scopes
        "delete",
        "delete_node",
        "delete_node",  # ④ NPC documents, then nodes
        "delete_edges",  # ⑤ connections
        "delete_node",  # ⑥ the region
    ]
    assert len(fd_writes) == 9 + len(w["npcs"]) and meta == "upsert_nodes"


def test_ex3_protected_region_is_refused_and_nothing_written() -> None:
    """EX-3 / BR-U3-16: a player stands in Riverton -> 409 with the session ids."""
    stack, w = _aldermoor()
    before = stack.state()
    with pytest.raises(RegionInUseError) as err:
        stack.editors.regions.delete_region(
            "w", w["riverton"].id, protected={w["riverton"].id: ["s1"]}
        )
    assert err.value.session_ids == ["s1"]
    assert stack.state() == before and stack.meter.calls == []


def test_unknown_region_is_a_lookup_error() -> None:
    stack, _w = _aldermoor()
    with pytest.raises(LookupError):
        stack.editors.regions.plan_region_delete("w", "nope")
