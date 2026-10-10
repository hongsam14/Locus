"""U5 Consensus tests — path weights + consensus classification (pure)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.knowledge import ConsensusEngine, best_path_weights, compute_consensus
from locus.shared.models import (
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
    rumor_ids = [v.knowledge_id for v in view.hearsay]
    assert rumor_ids == [kC.id]  # pw 0.24 in [0.15,0.5)
    # distortion recorded = 1 - 0.24
    assert abs(view.hearsay[0].path_decay - 0.76) < 1e-6
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
    assert not view.propagated and not view.hearsay


def test_consensus_engine_resolve() -> None:
    regions, connections, scopes, kbi, refs = _fixture()
    a = refs[0]
    kg = KnowledgeGraph(world_id="w", knowledge=list(kbi.values()), scopes=scopes)
    topo = RegionTopology(world_id="w", regions=regions, connections=connections)
    view = ConsensusEngine(kg, topo).resolve(a.id)
    assert view.region_id == a.id
    assert view.direct and view.propagated


# --------------------------------------------------------------------------- #
# V7 — the strongest origin, unknowns once, confident first (BR-V7-01..04)
# --------------------------------------------------------------------------- #
def _r(rid: str) -> Region:
    return Region(id=rid, world_id="w", name=rid, level=RegionLevel.TOWN, provenance=_prov())


def _direct(kid: str, rid: str, conf: float = 0.9) -> ScopeLink:
    return ScopeLink(
        world_id="w", knowledge_id=kid, region_id=rid, scope_type=ScopeType.DIRECT, confidence=conf
    )


def _ids(views) -> list[str]:
    return [v.knowledge_id for v in views]


def test_tp_v7_1_a_knowledge_comes_from_its_strongest_origin() -> None:
    """RE-W01: the weak origin is met first (its connection is listed first), yet the
    knowledge both origins hold propagates from the 0.9 one instead of being locked
    into hearsay by the 0.3 one."""
    here, weak, strong = _r("here"), _r("weak"), _r("strong")
    k = _k("both hold it")
    view = compute_consensus(
        "here",
        regions=[here, weak, strong],
        connections=_conn("here", "weak", 0.3) + _conn("here", "strong", 0.9),
        scopes=[_direct(k.id, "weak"), _direct(k.id, "strong")],
        knowledge_by_id={k.id: k},
    )
    assert _ids(view.propagated) == [k.id] and not view.hearsay
    assert view.propagated[0].region_id == "strong"
    assert abs(view.propagated[0].confidence - 0.9 * 0.9) < 1e-9
    assert view.unknown_count == 0


def test_tp_v7_1_a_tie_goes_to_the_smaller_region_id() -> None:
    here, b, a = _r("here"), _r("r-b"), _r("r-a")
    k = _k("both hold it")
    for order in (["r-b", "r-a"], ["r-a", "r-b"]):
        conns = [e for rid in order for e in _conn("here", rid, 0.6)]
        view = compute_consensus(
            "here",
            regions=[here, b, a],
            connections=conns,
            scopes=[_direct(k.id, rid) for rid in order],
            knowledge_by_id={k.id: k},
        )
        assert view.propagated[0].region_id == "r-a"


def test_tp_v7_2_unknown_counts_each_knowledge_once() -> None:
    here, w1, w2, s = _r("here"), _r("w1"), _r("w2"), _r("s")
    far, near = _k("only far away"), _k("far and near")
    view = compute_consensus(
        "here",
        regions=[here, w1, w2, s],
        connections=_conn("here", "w1", 0.1) + _conn("here", "w2", 0.05) + _conn("here", "s", 0.9),
        scopes=[
            _direct(far.id, "w1"),
            _direct(far.id, "w2"),  # two weak origins: one unknown, not two
            _direct(near.id, "w1"),
            _direct(near.id, "s"),  # a strong origin: not unknown at all
        ],
        knowledge_by_id={far.id: far, near.id: near},
    )
    assert view.unknown_count == 1
    assert _ids(view.propagated) == [near.id]


def test_tp_v7_2_a_knowledge_scoped_twice_keeps_its_highest_confidence() -> None:
    here = _r("here")
    k = _k("said twice")
    for scopes in (
        [_direct(k.id, "here", 0.4), _direct(k.id, "here", 0.8)],
        [_direct(k.id, "here", 0.8), _direct(k.id, "here", 0.4)],
    ):
        view = compute_consensus("here", regions=[here], scopes=scopes, knowledge_by_id={k.id: k})
        assert [v.confidence for v in view.direct] == [0.8]


def test_tp_v7_3_each_list_is_confident_first_then_by_id() -> None:
    here = _r("here")
    low, high, mid, tie = _k("low"), _k("high"), _k("mid"), _k("tie")
    scopes = [
        _direct(low.id, "here", 0.2),
        _direct(high.id, "here", 0.9),
        _direct(mid.id, "here", 0.5),
        _direct(tie.id, "here", 0.5),
    ]
    view = compute_consensus(
        "here",
        regions=[here],
        scopes=scopes,
        knowledge_by_id={x.id: x for x in (low, high, mid, tie)},
    )
    assert _ids(view.direct) == [high.id, *sorted([mid.id, tie.id]), low.id]
