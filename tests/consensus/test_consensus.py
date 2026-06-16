"""U5 Consensus tests — path weights + consensus classification (pure)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.consensus import ConsensusEngine, best_path_weights, compute_consensus
from locus.models import (
    ConnectionEdge,
    ConnectionKind,
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
    SourceKind,
)


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _region(name: str, level: RegionLevel, parent_id: str | None = None) -> Region:
    return Region(world_id="w", name=name, level=level, parent_id=parent_id, provenance=_prov())


def _conn(a: str, b: str, w: float) -> list[ConnectionEdge]:
    # symmetric pair (as U3 emits)
    return [
        ConnectionEdge(
            world_id="w",
            source_region_id=a,
            target_region_id=b,
            kind=ConnectionKind.ROUTE,
            weight=w,
            provenance=_prov(),
        ),
        ConnectionEdge(
            world_id="w",
            source_region_id=b,
            target_region_id=a,
            kind=ConnectionKind.ROUTE,
            weight=w,
            provenance=_prov(),
        ),
    ]


def _k(text: str, conf: float = 0.9, glob: bool = False) -> Knowledge:
    return Knowledge(
        world_id="w",
        statement=text,
        title=text,
        confidence=conf,
        is_global=glob,
        provenance=_prov(),
    )


# --------------------------------------------------------------------------- #
# best_path_weights
# --------------------------------------------------------------------------- #
def test_best_path_weights_max_product() -> None:
    conns = _conn("A", "B", 0.8) + _conn("B", "C", 0.3)
    pw = best_path_weights("A", conns)
    assert pw["A"] == 1.0
    assert abs(pw["B"] - 0.8) < 1e-9
    assert abs(pw["C"] - 0.24) < 1e-9  # 0.8 * 0.3


def test_best_path_weights_prefers_stronger_route() -> None:
    # A-C direct weak (0.2) vs A-B-C strong (0.9*0.9=0.81)
    conns = _conn("A", "C", 0.2) + _conn("A", "B", 0.9) + _conn("B", "C", 0.9)
    pw = best_path_weights("A", conns)
    assert abs(pw["C"] - 0.81) < 1e-9


@given(st.floats(min_value=0.0, max_value=1.0), st.floats(min_value=0.0, max_value=1.0))
def test_path_weights_bounded(w1: float, w2: float) -> None:
    conns = _conn("A", "B", w1) + _conn("B", "C", w2)
    pw = best_path_weights("A", conns)
    assert all(0.0 <= v <= 1.0 for v in pw.values())


# --------------------------------------------------------------------------- #
# compute_consensus
# --------------------------------------------------------------------------- #
def _fixture():
    cont = _region("Continent", RegionLevel.CONTINENT)
    a = _region("A", RegionLevel.TOWN, parent_id=cont.id)
    b = _region("B", RegionLevel.TOWN)
    c = _region("C", RegionLevel.TOWN)
    regions = [cont, a, b, c]
    connections = _conn(a.id, b.id, 0.8) + _conn(b.id, c.id, 0.3)

    kA, kB, kC, kD, kG = (
        _k("A fact"),
        _k("B fact"),
        _k("C fact"),
        _k("continent fact"),
        _k("global fact", glob=True),
    )
    knowledge_by_id = {x.id: x for x in (kA, kB, kC, kD, kG)}
    scopes = [
        ScopeLink(
            world_id="w",
            knowledge_id=kA.id,
            region_id=a.id,
            scope_type=ScopeType.DIRECT,
            confidence=0.9,
        ),
        ScopeLink(
            world_id="w",
            knowledge_id=kB.id,
            region_id=b.id,
            scope_type=ScopeType.DIRECT,
            confidence=0.9,
        ),
        ScopeLink(
            world_id="w",
            knowledge_id=kC.id,
            region_id=c.id,
            scope_type=ScopeType.DIRECT,
            confidence=0.9,
        ),
        ScopeLink(
            world_id="w",
            knowledge_id=kD.id,
            region_id=cont.id,
            scope_type=ScopeType.DIRECT,
            confidence=0.9,
        ),
    ]
    return regions, connections, scopes, knowledge_by_id, (a, b, c, cont, kA, kB, kC, kD, kG)


def test_compute_consensus_classifies() -> None:
    regions, connections, scopes, kbi, refs = _fixture()
    a, b, c, cont, kA, kB, kC, kD, kG = refs
    view = compute_consensus(
        a.id, regions=regions, connections=connections, scopes=scopes, knowledge_by_id=kbi
    )
    assert [v.knowledge_id for v in view.direct] == [kA.id]
    assert [v.knowledge_id for v in view.inherited] == [kD.id]  # continent ancestor
    assert kG.id in [v.knowledge_id for v in view.global_knowledge]
    assert [v.knowledge_id for v in view.propagated] == [kB.id]  # pw 0.8 >= 0.5
    rumor_ids = [v.knowledge_id for v in view.rumors]
    assert rumor_ids == [kC.id]  # pw 0.24 in [0.15,0.5)
    # distortion recorded = 1 - 0.24
    assert abs(view.rumors[0].distortion_degree - 0.76) < 1e-6
    # propagated confidence decayed: 0.9 * 0.8
    assert abs(view.propagated[0].confidence - 0.72) < 1e-9


def test_unknown_below_threshold() -> None:
    a = _region("A", RegionLevel.TOWN)
    b = _region("B", RegionLevel.TOWN)
    regions = [a, b]
    connections = _conn(a.id, b.id, 0.1)  # below rumor_min
    kB = _k("far fact")
    scopes = [
        ScopeLink(
            world_id="w",
            knowledge_id=kB.id,
            region_id=b.id,
            scope_type=ScopeType.DIRECT,
            confidence=0.9,
        )
    ]
    view = compute_consensus(
        a.id, regions=regions, connections=connections, scopes=scopes, knowledge_by_id={kB.id: kB}
    )
    assert view.unknown_count == 1
    assert not view.propagated and not view.rumors


def test_consensus_engine_resolve() -> None:
    regions, connections, scopes, kbi, refs = _fixture()
    a = refs[0]
    kg = KnowledgeGraph(world_id="w", knowledge=list(kbi.values()), scopes=scopes)
    topo = RegionTopology(world_id="w", regions=regions, connections=connections)
    view = ConsensusEngine(kg, topo).resolve(a.id)
    assert view.region_id == a.id
    assert view.direct and view.propagated
