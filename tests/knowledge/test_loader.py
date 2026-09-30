"""U2 K3 — WorldLoader reads NPCs, relations, priors and meta into a WorldSnapshot,
skips broken nodes (EX-17, BR-U2-16) and rejects an empty world."""

from __future__ import annotations

import pytest

from locus.knowledge.loader import WorldLoader
from locus.shared.models import (
    NPC,
    Entity,
    EntityType,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    Relation,
    ScopeLink,
    ScopeType,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.base import Node
from locus.shared.storage.persistence import persist_graph
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _seed(graph: InMemoryGraphRepository) -> dict:
    a = Region(world_id="w", name="Riverton", level=RegionLevel.TOWN, provenance=_prov())
    prov_region = Region(
        world_id="w", name="Greenvale", level=RegionLevel.PROVINCE, provenance=_prov()
    )
    a.parent_id = prov_region.id
    k = Knowledge(world_id="w", statement="market", title="Market", provenance=_prov())
    orphan = Knowledge(world_id="w", statement="lost", title="Lost", provenance=_prov())
    npc = NPC(
        world_id="w",
        name="Tomas",
        role="mayor",
        description="d",
        home_region_id=a.id,
        provenance=_prov(),
    )
    e1 = Entity(world_id="w", name="Tomas", entity_type=EntityType.PERSON, provenance=_prov())
    e2 = Entity(world_id="w", name="Market", entity_type=EntityType.EVENT, provenance=_prov())
    rel = Relation(
        world_id="w", source_id=e1.id, target_id=e2.id, relation_type="hosts", provenance=_prov()
    )
    scope = ScopeLink(world_id="w", knowledge_id=k.id, region_id=a.id, scope_type=ScopeType.DIRECT)
    meta = WorldMeta(id="w", name="Aldermoor", last_writer="import")
    persist_graph(
        graph,
        InMemorySearchRepository(),
        None,
        "w",
        regions=[a, prov_region],
        entities=[e1, e2],
        knowledge=[k, orphan],
        scopes=[scope],
        relations=[rel],
        npcs=[npc],
        meta=meta,
    )
    return {"a": a, "k": k, "orphan": orphan, "npc": npc, "rel": rel, "meta": meta}


def test_loader_reads_npcs_relations_meta_and_unscoped() -> None:
    graph = InMemoryGraphRepository()
    ids = _seed(graph)
    snap = WorldLoader(graph).load("w")
    assert snap.meta == ids["meta"]
    assert [n.id for n in snap.npcs] == [ids["npc"].id]
    assert snap.npcs_by_region[ids["a"].id][0].name == "Tomas"
    assert [r.id for r in snap.kg.relations] == [ids["rel"].id]
    assert snap.unscoped_knowledge_ids == [ids["orphan"].id]  # A4: still loaded
    assert snap.regions_by_id[ids["a"].id].parent_id is not None
    assert snap.load_warnings == []


def test_loader_skips_a_broken_node_and_reports_it() -> None:  # EX-17
    graph = InMemoryGraphRepository()
    ids = _seed(graph)
    graph.upsert_nodes(
        [Node(id="bad", label="Knowledge", world_id="w", properties={"id": "bad"})]  # no statement
    )
    snap = WorldLoader(graph).load("w")
    assert {k.id for k in snap.kg.knowledge} == {ids["k"].id, ids["orphan"].id}
    assert len(snap.load_warnings) == 1
    assert snap.load_warnings[0].stage == "load" and snap.load_warnings[0].item_id == "bad"


def test_loader_raises_for_unknown_world() -> None:
    with pytest.raises(LookupError):
        WorldLoader(InMemoryGraphRepository()).load("nope")


def test_lives_in_edge_wins_over_stale_property() -> None:
    graph = InMemoryGraphRepository()
    ids = _seed(graph)
    stale = gm.npc_to_node(ids["npc"].model_copy(update={"home_region_id": "elsewhere"}))
    graph.upsert_nodes([stale])
    snap = WorldLoader(graph).load("w")
    assert snap.npcs[0].home_region_id == ids["a"].id


def test_loader_drops_edges_to_missing_nodes() -> None:  # review U2 #9
    graph = InMemoryGraphRepository()
    ids = _seed(graph)
    graph.upsert_edges(
        gm.scope_edges(
            [
                ScopeLink(
                    world_id="w",
                    knowledge_id="k-ghost",
                    region_id=ids["a"].id,
                    scope_type=ScopeType.DIRECT,
                )
            ]
        )
    )
    snap = WorldLoader(graph).load("w")
    assert all(s.knowledge_id != "k-ghost" for s in snap.kg.scopes)
    assert any("dangling" in w.message for w in snap.load_warnings)
