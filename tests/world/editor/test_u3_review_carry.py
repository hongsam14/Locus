"""U3 code-review-01 items closed in U8 Step 9a (editor writes).

#13 retry-safe NPC move and prior-ref change · C3/S12 one delete rule · C4 narrow
delete_any · C11 no re-index of an unchanged document · C17 server title · S21 an edit
needs a world · S26 one id, one kind · S29 confidence reaches the DIRECT scope · S30 a
missing parent is not inherited · S32 an existing knowledge id is refused.
"""

from __future__ import annotations

import pytest

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
    SourceKind,
)
from locus.shared.storage.persistence import persist_graph
from locus.world.editor import ConnectionKey
from tests.world.editor.helpers import Stack
from tests.world.editor.test_region_delete import _aldermoor


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


# --------------------------------------------------------------------------- #
# #13: a cut at any write, then the same call again, finishes the job
# --------------------------------------------------------------------------- #
def test_13a_an_npc_move_cut_anywhere_then_retried_lives_in_one_place() -> None:
    def moved(w):
        return w["npcs"][0].model_copy(update={"home_region_id": w["hollow"].id})

    reference, w = _aldermoor()
    reference.editors.npcs.upsert_npc(moved(w))
    writes = len(reference.meter.calls)
    for n in range(writes):
        stack, w = _aldermoor()
        ada = moved(w)
        stack.meter.cut_at = n
        with pytest.raises(RuntimeError, match="cut at write"):
            stack.editors.npcs.upsert_npc(ada)
        stack.editors.npcs.upsert_npc(ada)  # the retry
        lives = [e for e in stack.graph.get_edges("w", ["LIVES_IN"]) if e.source_id == ada.id]
        assert [e.target_id for e in lives] == [w["hollow"].id], f"cut at write {n}"
        assert len(stack.graph.get_edges("w", ["LIVES_IN"])) == 2, f"cut at write {n}"
        home = [x.home_region_id for x in stack.cache.get("w").npcs if x.id == ada.id]
        assert home == [w["hollow"].id], f"cut at write {n}"


def test_13b_a_prior_ref_change_never_loses_the_connection() -> None:
    def setup():
        stack, w = _aldermoor()
        key = ConnectionKey(
            world_id="w",
            a_region_id=w["riverton"].id,
            b_region_id=w["hollow"].id,
            kind=ConnectionKind.ROUTE,
        )
        stack.editors.connections.set_prior_ref(key, "p1")
        stack.meter.calls.clear()
        return stack, w, key

    def pair(stack, w):
        ends = {w["riverton"].id, w["hollow"].id}
        return [
            c
            for c in stack.cache.get("w").topo.connections
            if {c.source_region_id, c.target_region_id} == ends
        ]

    reference, _w, key = setup()
    reference.editors.connections.set_prior_ref(key, None)
    writes = len(reference.meter.calls)
    for n in range(writes):
        stack, w, key = setup()
        stack.meter.cut_at = n
        with pytest.raises(RuntimeError, match="cut at write"):
            stack.editors.connections.set_prior_ref(key, None)
        assert len(pair(stack, w)) == 2, f"cut at write {n}"  # never lost
        stack.editors.connections.set_prior_ref(key, None)  # the retry
        assert {c.wiki_prior_ref for c in pair(stack, w)} == {None}  # cleared for real


# --------------------------------------------------------------------------- #
# C3 / S12 / C4: one delete rule
# --------------------------------------------------------------------------- #
def test_c3_s12_a_delete_by_the_wrong_kind_is_404_and_keeps_the_other_document() -> None:
    stack, w = _aldermoor()
    ada = w["npcs"][0]
    assert ("w", ada.id) in stack.search.docs
    with pytest.raises(LookupError, match="knowledge not found"):
        stack.editors.knowledge.delete_knowledge("w", ada.id)
    assert ("w", ada.id) in stack.search.docs  # the NPC's document stays
    calls = list(stack.meter.calls)
    with pytest.raises(LookupError):
        stack.editors.entities.delete_entity("w", "gone")
    assert stack.meter.calls[len(calls) :] == ["delete"]  # retry cleanup only, no meta write


def test_c4_delete_any_takes_knowledge_and_entities_only() -> None:
    stack, w = _aldermoor()
    with pytest.raises(ValueError, match="cannot delete a NPC"):
        stack.editors.delete_any("w", w["npcs"][0].id)
    assert stack.editors.delete_any("w", w["k1"].id) is True
    assert stack.editors.delete_any("w", "nothing") is False


# --------------------------------------------------------------------------- #
# C11 / C17 / S21 / S26 / S29 / S30 / S32
# --------------------------------------------------------------------------- #
def test_c11_an_unchanged_document_is_not_indexed_again() -> None:
    stack, w = _aldermoor()
    tomas: Entity = w["tomas"]
    stack.editors.entities.update_entity(tomas.model_copy(update={"located_in": w["hollow"].id}))
    assert "index" not in stack.meter.calls  # same name and description: no new embedding
    stack.meter.calls.clear()
    stack.editors.entities.update_entity(tomas.model_copy(update={"description": "a miller"}))
    assert "index" in stack.meter.calls


def test_c17_an_empty_title_gets_the_servers_fallback() -> None:
    stack, w = _aldermoor()
    k = Knowledge(
        world_id="w", statement="The   mill wheel turns at dawn", title="  ", provenance=_prov()
    )
    saved = stack.editors.knowledge.create_knowledge(k, w["riverton"].id)
    assert saved.title and saved.title.startswith("The mill wheel")


def test_s21_an_edit_in_a_world_that_does_not_exist_is_404() -> None:
    stack, _w = _aldermoor()
    town = Region(world_id="nowhere", name="T", level=RegionLevel.TOWN, provenance=_prov())
    with pytest.raises(LookupError):
        stack.editors.regions.create_region(town)
    assert "nowhere" not in stack.graph.list_world_ids()


def test_s26_an_id_held_by_another_kind_is_refused() -> None:
    stack, w = _aldermoor()
    clash = Knowledge(
        id=w["riverton"].id, world_id="w", statement="x", title="x", provenance=_prov()
    )
    with pytest.raises(ValueError, match="already a Region"):
        stack.editors.knowledge.upsert_knowledge(clash)
    npc = NPC(
        id=w["k1"].id,
        world_id="w",
        name="N",
        role="r",
        description="d",
        home_region_id=w["hollow"].id,
        provenance=_prov(),
    )
    with pytest.raises(ValueError, match="already a Knowledge"):
        stack.editors.npcs.create_npc(npc)


def test_s29_a_new_confidence_reaches_the_direct_scopes() -> None:
    stack, w = _aldermoor()
    k1: Knowledge = w["k1"]
    stack.editors.knowledge.upsert_knowledge(k1.model_copy(update={"confidence": 0.3}))
    scopes = [s for s in stack.cache.get("w").kg.scopes if s.knowledge_id == k1.id]
    assert scopes and all(s.confidence == 0.3 for s in scopes)


def test_s30_a_parent_the_world_lacks_is_not_handed_to_the_children() -> None:
    stack, w = _aldermoor()
    lost = w["riverton"].model_copy(update={"parent_id": "gone"})
    persist_graph(stack.graph, stack.search, None, "w", regions=[lost])  # a dangling parent
    stack.cache.invalidate("w")
    plan = stack.editors.regions.plan_region_delete("w", w["riverton"].id)
    assert plan.new_parent_id is None
    stack.editors.regions.delete_region("w", w["riverton"].id)
    assert stack.cache.get("w").regions_by_id[w["mill"].id].parent_id is None


def test_s32_adding_knowledge_with_an_existing_id_is_400() -> None:
    stack, w = _aldermoor()
    with pytest.raises(ValueError, match="already exists"):
        stack.editors.knowledge.create_knowledge(w["k1"], w["hollow"].id)


def test_12_confirming_an_entity_with_a_broken_location_succeeds() -> None:
    """U3 review #12 (server half): the location is checked only when it changes."""
    stack, w = _aldermoor()
    ghost = Entity(
        world_id="w",
        name="Ghost",
        entity_type=EntityType.PERSON,
        confidence=0.2,
        located_in="gone",
        provenance=_prov(),
    )
    persist_graph(stack.graph, stack.search, None, "w", entities=[ghost])
    stack.cache.invalidate("w")
    stack.editors.entities.update_entity(ghost.model_copy(update={"confidence": 0.9}))
    with pytest.raises(LookupError, match="region not found"):
        stack.editors.entities.update_entity(ghost.model_copy(update={"located_in": "elsewhere"}))


def test_a_connection_between_regions_of_a_new_world_still_saves() -> None:
    """Guard for S21: a world that exists (has regions) but has no WorldMeta (pre-U2)
    can still be edited — the check reads the world, not its meta node."""
    stack = Stack()
    a = Region(world_id="old", name="A", level=RegionLevel.TOWN, provenance=_prov())
    b = Region(world_id="old", name="B", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(stack.graph, stack.search, None, "old", regions=[a, b])
    edge = ConnectionEdge(
        world_id="old",
        source_region_id=a.id,
        target_region_id=b.id,
        kind=ConnectionKind.ROUTE,
        weight=0.5,
        provenance=_prov(),
    )
    assert len(stack.editors.connections.upsert_connection(edge)) == 2


# --------------------------------------------------------------------------- #
# C5 (U8 Step 10): one "unscoped" rule — the snapshot's — for the editor list, the
# augmentation detector and the export the web counts from
# --------------------------------------------------------------------------- #
def test_c5_the_snapshot_rule_ignores_a_stale_stored_list_and_global_items() -> None:
    from locus.shared.models import (
        KnowledgeGraph,
        RegionTopology,
        ScopeLink,
        ScopeType,
        WorldSnapshot,
    )
    from locus.world.augmentation.detectors import detect_unscoped

    def item(title: str, **kw) -> Knowledge:
        return Knowledge(world_id="w", statement=title, title=title, provenance=_prov(), **kw)

    orphan, common, placed = item("orphan"), item("common", is_global=True), item("placed")
    snap = WorldSnapshot(
        world_id="w",
        kg=KnowledgeGraph(
            world_id="w",
            knowledge=[orphan, common, placed],
            scopes=[
                ScopeLink(
                    world_id="w",
                    knowledge_id=placed.id,
                    region_id="r",
                    scope_type=ScopeType.DIRECT,
                )
            ],
            unscoped_knowledge_ids=[placed.id],  # stale: what the loader saw earlier
        ),
        topo=RegionTopology(world_id="w", regions=[]),
    )
    assert snap.unscoped_knowledge_ids == [orphan.id]
    assert [i.target_ids for i in detect_unscoped(snap)] == [[orphan.id]]


def test_c5_the_editor_list_and_the_export_agree() -> None:
    stack, w = _aldermoor()
    k = stack.editors.knowledge
    well = Knowledge(world_id="w", statement="the well ran dry", title="well", provenance=_prov())
    k.create_knowledge(well, w["hollow"].id)
    k.set_scopes("w", well.id, [])
    listed = [u.id for u in k.list_unscoped("w")]
    assert well.id in listed
    exported = stack.exporter.export_world("w")["unscoped_knowledge_ids"]
    assert exported == listed == stack.cache.get("w").unscoped_knowledge_ids
    k.set_scopes("w", well.id, [w["riverton"].id])
    assert well.id not in stack.exporter.export_world("w")["unscoped_knowledge_ids"]
