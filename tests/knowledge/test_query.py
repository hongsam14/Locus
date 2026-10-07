"""U8 Query tests — reverse mapping, loader, engine, pure split/diff."""

from __future__ import annotations

from locus.knowledge import WorldLoader, diff_sets, split_shared_unique
from locus.knowledge.query import QueryEngine
from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    ConsensusView,
    Knowledge,
    KnowledgeView,
    Provenance,
    Region,
    RegionLevel,
    ScopeLink,
    ScopeType,
    SourceKind,
)
from locus.shared.storage import graph_mapping as gm
from tests.shared.snapshots import snapshot_of


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by="llm")


# --------------------------------------------------------------------------- #
# reverse mapping round-trip
# --------------------------------------------------------------------------- #
def test_region_node_roundtrip() -> None:
    r = Region(
        world_id="w",
        name="Town",
        level=RegionLevel.TOWN,
        attributes={"terrain": "river"},
        provenance=_prov(),
    )
    back = gm.node_to_region(gm.region_to_node(r))
    assert back.id == r.id and back.name == r.name
    assert str(back.level) == str(r.level)
    assert back.attributes == {"terrain": "river"}


def test_knowledge_node_roundtrip_preserves_flags() -> None:
    k = Knowledge(
        world_id="w",
        statement="sun rises east",
        title="Sunrise",
        is_global=True,
        region_hint="Town",
        about_entity_ids=["e1", "e2"],
        provenance=_prov(),
    )
    back = gm.node_to_knowledge(gm.knowledge_to_node(k))
    assert back.is_global is True
    assert back.region_hint == "Town"
    assert back.about_entity_ids == ["e1", "e2"]


# --------------------------------------------------------------------------- #
# WorldLoader (mock repo)
# --------------------------------------------------------------------------- #
class _FakeGraphRepo:
    def __init__(self, nodes_by_label, edges) -> None:
        self._nodes = nodes_by_label
        self._edges = edges

    def find_nodes(self, world_id, label, filters=None):
        return self._nodes.get(label, [])

    def get_edges(self, world_id, types=None):
        return self._edges


def test_world_loader_reconstructs_graph_and_topology() -> None:
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    b = Region(world_id="w", name="B", level=RegionLevel.TOWN, provenance=_prov())
    k = Knowledge(world_id="w", statement="b fact", title="b", provenance=_prov())
    nodes = {
        "Region": [gm.region_to_node(a), gm.region_to_node(b)],
        "Entity": [],
        "Knowledge": [gm.knowledge_to_node(k)],
    }
    edges = gm.connection_edges(
        [
            ConnectionEdge(
                world_id="w",
                source_region_id=a.id,
                target_region_id=b.id,
                kind=ConnectionKind.ROUTE,
                weight=0.7,
                provenance=_prov(),
            )
        ]
    ) + gm.scope_edges(
        [
            ScopeLink(
                world_id="w",
                knowledge_id=k.id,
                region_id=b.id,
                scope_type=ScopeType.DIRECT,
                confidence=0.9,
            )
        ]
    )
    snap = WorldLoader(_FakeGraphRepo(nodes, edges)).load("w")
    kg, topo = snap.kg, snap.topo
    assert len(topo.regions) == 2
    assert len(topo.connections) == 1 and topo.connections[0].weight == 0.7
    assert len(kg.scopes) == 1 and kg.scopes[0].region_id == b.id


# --------------------------------------------------------------------------- #
# pure split / diff
# --------------------------------------------------------------------------- #
def _kv(kid: str) -> KnowledgeView:
    return KnowledgeView(knowledge_id=kid, statement=kid, scope_type="direct", confidence=1.0)


def test_split_shared_unique() -> None:
    view = ConsensusView(
        world_id="w",
        region_id="r",
        direct=[_kv("d1")],
        inherited=[_kv("i1")],
        global_knowledge=[_kv("g1")],
        propagated=[_kv("p1")],
        hearsay=[_kv("ru1")],
    )
    unique, shared = split_shared_unique(view, include_hearsay=True)
    assert unique == ["d1"]
    assert set(shared) == {"i1", "g1", "p1", "ru1"}
    _, shared_no_rumor = split_shared_unique(view, include_hearsay=False)
    assert "ru1" not in shared_no_rumor


def test_diff_sets() -> None:
    shared, only_a, only_b = diff_sets({"x", "y"}, {"y", "z"})
    assert shared == ["y"] and only_a == ["x"] and only_b == ["z"]


def test_region_known_excludes_propagated_and_rumors() -> None:
    from locus.knowledge.query import region_known, view_items

    view = ConsensusView(
        world_id="w",
        region_id="r",
        direct=[_kv("d1")],
        inherited=[_kv("i1")],
        global_knowledge=[_kv("g1")],
        propagated=[_kv("p1")],
        hearsay=[_kv("ru1")],
    )
    known = {v.knowledge_id for v in region_known(view)}
    assert known == {"d1", "i1", "g1"}  # propagated + auto-rumor excluded
    # existing view_items behaviour unchanged (regression guard)
    assert {v.knowledge_id for v in view_items(view)} == {"d1", "i1", "g1", "p1", "ru1"}


# --------------------------------------------------------------------------- #
# QueryEngine (mock loader)
# --------------------------------------------------------------------------- #
class _FakeLoader:
    def __init__(self, kg, topo) -> None:
        self._kg, self._topo = kg, topo

    def get(self, world_id):
        return snapshot_of(self._kg, self._topo)


def test_query_engine_region_knowledge_and_not_found() -> None:
    from locus.shared.models import KnowledgeGraph, RegionTopology

    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    k = Knowledge(world_id="w", statement="a fact", title="a", confidence=0.9, provenance=_prov())
    kg = KnowledgeGraph(
        world_id="w",
        knowledge=[k],
        scopes=[
            ScopeLink(
                world_id="w",
                knowledge_id=k.id,
                region_id=a.id,
                scope_type=ScopeType.DIRECT,
                confidence=0.9,
            )
        ],
    )
    topo = RegionTopology(world_id="w", regions=[a])
    engine = QueryEngine(_FakeLoader(kg, topo))

    result = engine.knowledge_for_region("w", a.id)
    assert result.unique_ids == [k.id]
    assert any(i.knowledge_id == k.id for i in result.items)

    import pytest

    with pytest.raises(LookupError):
        engine.knowledge_for_region("w", "missing")


# --------------------------------------------------------------------------- #
# U2 K5 — title fill (EX-20) and region briefs (EX-21)
# --------------------------------------------------------------------------- #
def _world_for_briefs():
    from locus.shared.models import KnowledgeGraph, RegionTopology

    prov = Region(world_id="w", name="Greenvale", level=RegionLevel.PROVINCE, provenance=_prov())
    town = Region(
        world_id="w",
        name="Riverton",
        level=RegionLevel.TOWN,
        parent_id=prov.id,
        description="A market town.",
        provenance=_prov(),
    )
    empty = Region(world_id="w", name="Highcrag", level=RegionLevel.TOWN, provenance=_prov())
    ks = [
        Knowledge(world_id="w", statement=f"s{i}", title=f"T{i}", confidence=c, provenance=_prov())
        for i, c in enumerate([0.5, 0.9, 0.7, 0.9])
    ]
    scopes = [
        ScopeLink(
            world_id="w",
            knowledge_id=k.id,
            region_id=town.id,
            scope_type=ScopeType.DIRECT,
            confidence=k.confidence,
        )
        for k in ks
    ]
    kg = KnowledgeGraph(world_id="w", knowledge=ks, scopes=scopes)
    topo = RegionTopology(world_id="w", regions=[prov, town, empty])
    return kg, topo, prov, town, empty, ks


def test_query_fills_title_from_knowledge() -> None:  # EX-20 / BR-U2-19
    kg, topo, _prov_r, town, _e, ks = _world_for_briefs()
    engine = QueryEngine(_FakeLoader(kg, topo))
    result = engine.knowledge_for_region("w", town.id)
    assert {v.title for v in result.items} == {k.title for k in ks}


def test_region_briefs_top_k_and_hierarchy_path() -> None:  # EX-21 / BR-U2-20
    kg, topo, prov, town, empty, ks = _world_for_briefs()
    briefs = {
        b.region_id: b for b in QueryEngine(_FakeLoader(kg, topo)).region_briefs("w", top_k=3)
    }
    assert set(briefs) == {prov.id, town.id, empty.id}  # regions without knowledge included
    t = briefs[town.id]
    assert t.level_path == ["Greenvale", "Riverton"] and t.description == "A market town."
    # confidence desc, ties by id: 0.9, 0.9, 0.7
    top = sorted([ks[1], ks[3]], key=lambda k: k.id)
    assert t.top_knowledge == [top[0].title, top[1].title, ks[2].title]
    assert briefs[empty.id].top_knowledge == [] and briefs[prov.id].level_path == ["Greenvale"]


def test_level_path_ids_follow_the_names_and_survive_a_cycle() -> None:  # V3 BR-V3-24
    from locus.knowledge.query import level_path, level_path_ids

    kg, topo, prov, town, _empty, _ks = _world_for_briefs()
    snap = snapshot_of(kg, topo)
    assert level_path(town, snap) == ["Greenvale", "Riverton"]
    assert level_path_ids(town, snap) == [prov.id, town.id]
    a = Region(world_id="w", name="A", level=RegionLevel.TOWN, provenance=_prov())
    b = Region(world_id="w", name="B", level=RegionLevel.TOWN, parent_id=a.id, provenance=_prov())
    a = a.model_copy(update={"parent_id": b.id})  # a cycle
    looped = snapshot_of(kg, topo.model_copy(update={"regions": [a, b]}))
    assert len(level_path_ids(a, looped)) == len(level_path(a, looped)) == 2
