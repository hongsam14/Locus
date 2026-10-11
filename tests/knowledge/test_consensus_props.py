"""V7 consensus properties (PBT-V7-1..3, PBT-03): the result does not follow input order.

The generator lives here (PBT-07). Weights are two-decimal values, as a designer types
them; their products along a path are the same bits whatever order the connections
come in, so the properties compare exactly. Confidences come from a small set so that
ties happen and the id tie-break is exercised (V7 code review #6). One knowledge is
always held by two regions, the case RE-W01 was about (#21).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from locus.knowledge.consensus import DEFAULT_PARAMS, compute_consensus
from locus.knowledge.propagation import best_path_weights
from locus.shared.models import (
    ConnectionEdge,
    ConnectionKind,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    ScopeLink,
    ScopeType,
    SourceKind,
)

_PROV = Provenance(source=SourceKind.INPUT)
_WEIGHTS = st.integers(min_value=1, max_value=100).map(lambda n: n / 100)
_CONF = st.sampled_from([0.2, 0.5, 0.8, 0.9, 1.0])


@st.composite
def worlds(draw):
    n = draw(st.integers(min_value=2, max_value=8))
    rids = [f"r{i}" for i in range(n)]
    regions = []
    for i, rid in enumerate(rids):  # a parent always comes earlier: no cycles
        parent = draw(st.none() | st.sampled_from(rids[:i])) if i else None
        regions.append(
            Region(
                id=rid,
                world_id="w",
                name=rid,
                level=RegionLevel.TOWN,
                parent_id=parent,
                provenance=_PROV,
            )
        )
    pairs = draw(
        st.lists(st.tuples(st.sampled_from(rids), st.sampled_from(rids), _WEIGHTS), max_size=12)
    )
    connections = [
        ConnectionEdge(
            world_id="w",
            source_region_id=a,
            target_region_id=b,
            kind=ConnectionKind.ROUTE,
            weight=w,
            provenance=_PROV,
        )
        for x, y, w in pairs
        if x != y
        for a, b in ((x, y), (y, x))
    ]
    kids = [f"k{i}" for i in range(draw(st.integers(min_value=1, max_value=6)))]
    knowledge = [
        Knowledge(
            id=kid,
            world_id="w",
            statement=kid,
            title=kid,
            confidence=draw(_CONF),
            is_global=draw(st.booleans()) and draw(st.booleans()),
            provenance=_PROV,
        )
        for kid in kids
    ]
    held = draw(
        st.lists(st.tuples(st.sampled_from(kids), st.sampled_from(rids), _CONF), max_size=14)
    )
    a, b = draw(st.lists(st.sampled_from(rids), min_size=2, max_size=2, unique=True))
    held += [(kids[0], a, draw(_CONF)), (kids[0], b, draw(_CONF))]  # two origins (RE-W01)
    scopes = [  # one (region, knowledge) may come twice with another confidence (R-07)
        ScopeLink(
            world_id="w",
            knowledge_id=kid,
            region_id=rid,
            scope_type=ScopeType.DIRECT,
            confidence=conf,
        )
        for kid, rid, conf in held
    ]
    return regions, connections, scopes, knowledge


def _resolve(region_id, regions, connections, scopes, knowledge):
    return compute_consensus(
        region_id,
        regions=regions,
        connections=connections,
        scopes=scopes,
        knowledge_by_id={k.id: k for k in knowledge},
    )


def _lists(view):
    return (view.direct, view.inherited, view.global_knowledge, view.propagated, view.hearsay)


def _shape(view):
    return (
        [
            [(v.knowledge_id, v.confidence, v.region_id, v.path_decay) for v in xs]
            for xs in _lists(view)
        ],
        view.unknown_count,
    )


@settings(max_examples=150, deadline=None)
@given(world=worlds(), data=st.data())
def test_pbt_v7_1_consensus_does_not_follow_input_order(world, data) -> None:
    regions, connections, scopes, knowledge = world
    shuffled = [data.draw(st.permutations(xs)) for xs in (regions, connections, scopes, knowledge)]
    for region in regions:
        assert _shape(_resolve(region.id, *world)) == _shape(_resolve(region.id, *shuffled))


@settings(max_examples=150, deadline=None)
@given(world=worlds())
def test_pbt_v7_1_each_list_is_confident_first_then_by_id(world) -> None:  # BR-V7-04
    regions, connections, scopes, knowledge = world
    for region in regions:
        for xs in _lists(_resolve(region.id, *world)):
            keys = [(-v.confidence, v.knowledge_id) for v in xs]
            assert keys == sorted(keys)


@settings(max_examples=150, deadline=None)
@given(world=worlds())
def test_pbt_v7_2_a_spread_knowledge_comes_from_its_strongest_origin(world) -> None:
    regions, connections, scopes, knowledge = world
    for region in regions:
        view = _resolve(region.id, *world)
        pw = best_path_weights(region.id, connections)
        for v in view.propagated + view.hearsay:
            holders = {
                s.region_id
                for s in scopes
                if s.knowledge_id == v.knowledge_id and s.region_id != region.id
            }
            strongest = max(pw[h] for h in holders if h in pw)
            assert pw[v.region_id] == strongest
            assert v.region_id == min(h for h in holders if pw.get(h) == strongest)


@settings(max_examples=150, deadline=None)
@given(world=worlds())
def test_pbt_v7_3_unknowns_are_counted_once_and_only_when_unsettled(world) -> None:
    """BR-V7-03: a knowledge counts as unknown once, only when no list holds it and its
    strongest origin is below ``hearsay_min``; and no knowledge is in two lists."""
    regions, connections, scopes, knowledge = world
    known = {k.id for k in knowledge}
    for region in regions:
        view = _resolve(region.id, *world)
        ids = [v.knowledge_id for xs in _lists(view) for v in xs]
        assert len(ids) == len(set(ids))  # one list each
        pw = best_path_weights(region.id, connections)
        strongest: dict[str, float] = {}
        for s in scopes:
            if s.knowledge_id in known and s.region_id != region.id and s.region_id in pw:
                w = pw[s.region_id]
                strongest[s.knowledge_id] = max(w, strongest.get(s.knowledge_id, 0.0))
        expected = sum(
            1 for kid, w in strongest.items() if kid not in ids and w < DEFAULT_PARAMS.hearsay_min
        )
        assert view.unknown_count == expected
