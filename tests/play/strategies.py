"""Reusable hypothesis generators for the play boundary (PBT-07; TP-U4-8).

Builds small canonical snapshots (regions + connections), sessions with rumors,
and the players that move through them. Shared by the movement / turn / summary
property tests so every U4 invariant draws from the same domain generators.
"""

from __future__ import annotations

from hypothesis import strategies as st

from locus.play.models import Player, SessionRumor
from locus.shared.models import (
    NPC,
    ConnectionEdge,
    ConnectionKind,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    SourceKind,
    WorldSnapshot,
)
from tests.shared.snapshots import snapshot_of

WORLD = "w"


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def region(
    region_id: str, name: str | None = None, level: RegionLevel = RegionLevel.TOWN
) -> Region:
    r = Region(world_id=WORLD, name=name or region_id.upper(), level=level, provenance=_prov())
    r.id = region_id
    return r


def edge(
    src: str, dst: str, *, weight: float = 0.5, kind: ConnectionKind = ConnectionKind.ROUTE
) -> ConnectionEdge:
    return ConnectionEdge(
        world_id=WORLD,
        source_region_id=src,
        target_region_id=dst,
        kind=kind,
        weight=weight,
        provenance=_prov(),
    )


def npc(npc_id: str, home: str, name: str = "Villager") -> NPC:
    n = NPC(
        world_id=WORLD,
        name=name,
        role="villager",
        description="",
        home_region_id=home,
        provenance=_prov(),
    )
    n.id = npc_id
    return n


def build_snapshot(
    region_ids: list[str],
    edges: list[ConnectionEdge],
    *,
    npcs: list[NPC] | None = None,
    kg: KnowledgeGraph | None = None,
) -> WorldSnapshot:
    topo = RegionTopology(
        world_id=WORLD, regions=[region(r) for r in region_ids], connections=edges
    )
    return snapshot_of(kg or KnowledgeGraph(world_id=WORLD), topo, npcs=npcs or [])


weights = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
kinds = st.sampled_from(list(ConnectionKind))


@st.composite
def connections(draw, src: str = "a", dst: str = "b") -> ConnectionEdge:
    """One connection with an arbitrary kind and weight (TP-U4-1/2)."""
    return edge(src, dst, weight=draw(weights), kind=draw(kinds))


@st.composite
def topologies(draw, max_regions: int = 6) -> WorldSnapshot:
    """A small connected-ish topology: ``n`` regions, each edge stored in both
    directions (as the loader does), arbitrary kinds and weights."""
    n = draw(st.integers(min_value=2, max_value=max_regions))
    ids = [f"r{i}" for i in range(n)]
    edges: list[ConnectionEdge] = []
    pairs = draw(
        st.lists(
            st.tuples(st.integers(0, n - 1), st.integers(0, n - 1)).filter(lambda p: p[0] != p[1]),
            min_size=1,
            max_size=n * 2,
        )
    )
    for i, j in pairs:
        w, k = draw(weights), draw(kinds)
        edges.append(edge(ids[i], ids[j], weight=w, kind=k))
        edges.append(edge(ids[j], ids[i], weight=w, kind=k))
    return build_snapshot(ids, edges)


@st.composite
def players_in(draw, snapshot: WorldSnapshot, session_id: str = "s") -> Player:
    rid = draw(st.sampled_from(sorted(snapshot.regions_by_id)))
    return Player(session_id=session_id, name="Ari", region_id=rid)


@st.composite
def rumors_for(draw, session_id: str, region_id: str, max_count: int = 25) -> list[SessionRumor]:
    n = draw(st.integers(min_value=0, max_value=max_count))
    return [
        SessionRumor(
            session_id=session_id,
            region_id=region_id,
            distorted_from_id=f"k{i}",
            distorted_from_kind="knowledge",
            statement=f"rumor {i}",
            support=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
            promoted=draw(st.booleans()),
            provenance=_prov(),
        )
        for i in range(n)
    ]
