"""V7 consensus properties (PBT-V7-1..3, PBT-03): the result does not follow input order.

The generator lives here (PBT-07). Connection weights are powers of two, so a path's
product is exact whatever order its edges are multiplied in; the code's tie rule
(``_TIE_DIGITS``) covers the last-bit noise of other weights, which a property on exact
equality could not tell from a real order dependence.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from locus.knowledge.consensus import compute_consensus
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
_WEIGHTS = [1.0, 0.5, 0.25, 0.125, 0.0625]  # every consensus band: propagated .. unknown
_conf = st.floats(min_value=0.05, max_value=1.0, allow_nan=False)


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
        st.lists(
            st.tuples(st.sampled_from(rids), st.sampled_from(rids), st.sampled_from(_WEIGHTS)),
            max_size=12,
        )
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
            confidence=draw(_conf),
            is_global=draw(st.booleans()) and draw(st.booleans()),
            provenance=_PROV,
        )
        for kid in kids
    ]
    scopes = [  # one (region, knowledge) may come twice with another confidence (R-07)
        ScopeLink(
            world_id="w",
            knowledge_id=kid,
            region_id=rid,
            scope_type=ScopeType.DIRECT,
            confidence=conf,
        )
        for kid, rid, conf in draw(
            st.lists(st.tuples(st.sampled_from(kids), st.sampled_from(rids), _conf), max_size=14)
        )
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


def _shape(view):
    lists = (view.direct, view.inherited, view.global_knowledge, view.propagated, view.hearsay)
    return (
        [[(v.knowledge_id, v.confidence, v.region_id, v.path_decay) for v in xs] for xs in lists],
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
def test_pbt_v7_3_unknowns_are_at_most_the_knowledge_scoped_anywhere(world) -> None:
    regions, connections, scopes, knowledge = world
    scoped = {s.knowledge_id for s in scopes}
    for region in regions:
        assert _resolve(region.id, *world).unknown_count <= len(scoped)
