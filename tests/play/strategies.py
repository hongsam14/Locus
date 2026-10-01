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
    Knowledge,
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    ScopeLink,
    ScopeType,
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


# --------------------------------------------------------------------------- #
# U5 — worlds whose knowledge is tagged by region (TP-U5-1/4, PBT-07)
# --------------------------------------------------------------------------- #
def marker(region_id: str, i: int) -> str:
    """A statement that can only belong to ``region_id`` — searched for in prompts."""
    return f"only-in-{region_id}-#{i}"


GLOBAL_MARKER = "everyone-knows-this"


@st.composite
def regional_worlds(draw, max_regions: int = 4) -> WorldSnapshot:
    """A chain r0 — r1 — … with each region's own direct knowledge (statements carry a
    region marker), optional global knowledge, and weights drawn across the propagate
    and hearsay bands so neighbours really do reach each other's knowledge."""
    n = draw(st.integers(min_value=2, max_value=max_regions))
    ids = [f"r{i}" for i in range(n)]
    knowledge: list[Knowledge] = []
    scopes: list[ScopeLink] = []
    for rid in ids:
        for j in range(draw(st.integers(min_value=0, max_value=4))):
            k = Knowledge(
                world_id=WORLD,
                statement=marker(rid, j),
                title=f"{rid}-{j}",
                confidence=draw(st.floats(min_value=0.1, max_value=1.0, allow_nan=False)),
                provenance=_prov(),
            )
            k.id = f"k-{rid}-{j}"
            knowledge.append(k)
            scopes.append(
                ScopeLink(
                    world_id=WORLD, knowledge_id=k.id, region_id=rid, scope_type=ScopeType.DIRECT
                )
            )
    if draw(st.booleans()):
        g = Knowledge(
            world_id=WORLD,
            statement=GLOBAL_MARKER,
            title="global",
            is_global=True,
            provenance=_prov(),
        )
        g.id = "k-global"
        knowledge.append(g)
    edges: list[ConnectionEdge] = []
    for a, b in zip(ids, ids[1:], strict=False):
        w = draw(st.sampled_from([0.9, 0.6, 0.4, 0.2, 0.05]))  # propagate / hearsay / nothing
        edges += [edge(a, b, weight=w), edge(b, a, weight=w)]
    kg = KnowledgeGraph(world_id=WORLD, knowledge=knowledge, scopes=scopes)
    return build_snapshot(ids, edges, kg=kg)


@st.composite
def rumors_from(
    draw, session_id: str, region_id: str, knowledge_ids: list[str], max_count: int = 12
) -> list[SessionRumor]:
    """Rumors in ``region_id`` drafted from some of ``knowledge_ids``.

    Like the real generator, a rumor may extend an earlier one (a chain link:
    ``distorted_from_kind="rumor"``), and some rumors are pruned (``active=False``) —
    a pruned middle link must not break the walk to the canonical root (review U5 #1).
    Support ties are common on purpose: the demo's chains share one support value.
    """
    n = draw(st.integers(min_value=0, max_value=max_count))
    out: list[SessionRumor] = []
    for i in range(n):
        if out and draw(st.booleans()):
            parent = draw(st.sampled_from(out))
            source, kind = parent.id, "rumor"
        else:
            source = draw(st.sampled_from(knowledge_ids)) if knowledge_ids else f"k-elsewhere-{i}"
            kind = "knowledge"
        out.append(
            SessionRumor(
                session_id=session_id,
                region_id=region_id,
                distorted_from_id=source,
                distorted_from_kind=kind,
                statement=f"twisted-{source}-{i}",
                distortion_degree=draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
                support=draw(st.sampled_from([0.2, 0.5, 0.8])),
                promoted=draw(st.booleans()),
                active=draw(st.sampled_from([True, True, True, False])),
                provenance=_prov(),
            )
        )
    return out


def chain_roots(picked: list[SessionRumor], every: list[SessionRumor]) -> set[str]:
    """Test oracle, written apart from ``scope.root_source``: the canonical knowledge
    ids at the root of each picked rumor's chain (parents looked up in ``every``)."""
    by_id = {r.id: r for r in every}
    roots: set[str] = set()
    for rumor in picked:
        node: SessionRumor | None = rumor
        visited: set[str] = set()
        while node is not None and node.distorted_from_kind == "rumor" and node.id not in visited:
            visited.add(node.id)
            node = by_id.get(node.distorted_from_id)
        if node is not None and node.distorted_from_kind == "knowledge":
            roots.add(node.distorted_from_id)
    return roots


# --- U6 deeds & spread (PBT-07; TP-U6-1/2/8) ---------------------------------------- #
@st.composite
def spread_worlds(draw, max_regions: int = 8) -> WorldSnapshot:
    """Regions r0..rn with random connections: some one-way only (spread reads them both
    ways, like movement), some blocked, weights across the whole range."""
    n = draw(st.integers(min_value=2, max_value=max_regions))
    ids = [f"r{i}" for i in range(n)]
    edges: list[ConnectionEdge] = []
    for i in range(n):
        for j in range(i + 1, n):
            if not draw(st.booleans()):
                continue
            kind = draw(
                st.sampled_from(
                    [ConnectionKind.ROUTE, ConnectionKind.ROUTE, ConnectionKind.BLOCKED]
                )
            )
            w = draw(weights)
            edges.append(edge(ids[i], ids[j], weight=w, kind=kind))
            if draw(st.booleans()):
                edges.append(edge(ids[j], ids[i], weight=w, kind=kind))
    return build_snapshot(ids, edges)


def deed_rumor(
    region_id: str,
    *,
    appraisal_id: str = "ap1",
    deed_id: str = "d1",
    support: float = 0.3,
    degree: float = 0.3,
    rumor_id: str | None = None,
) -> SessionRumor:
    r = SessionRumor(
        session_id="s",
        region_id=region_id,
        distorted_from_id=deed_id,
        distorted_from_kind="deed",
        statement=f"the traveler did something ({region_id})",
        distortion_degree=degree,
        support=support,
        origin_kind="deed",
        origin_deed_id=deed_id,
        origin_appraisal_id=appraisal_id,
        provenance=Provenance(source=SourceKind.SIMULATION),
    )
    if rumor_id is not None:
        r.id = rumor_id
    return r


# --- U7 (Step 4.6): feedback states, player timelines, session state --------------- #
_unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)


@st.composite
def feedback_inputs(draw, max_regions: int = 6):
    """Per-region ``(degree, share)`` with share <= cap and a delta map over some of them
    (U7 TP-U7-1..3). Returns ``(states, deltas, cap, restore)``."""
    from locus.play.rumor.dynamics import FeedbackState

    cap = draw(st.floats(min_value=0.0, max_value=0.5, allow_nan=False))
    restore = draw(st.floats(min_value=0.001, max_value=0.2, allow_nan=False))
    ids = [f"r{i}" for i in range(draw(st.integers(min_value=0, max_value=max_regions)))]
    states = {}
    for rid in ids:
        degree = draw(_unit)
        share = draw(st.floats(min_value=0.0, max_value=min(cap, degree), allow_nan=False))
        states[rid] = FeedbackState(degree=degree, share=share)
    extra = [f"new{i}" for i in range(draw(st.integers(min_value=0, max_value=2)))]
    deltas = (
        {
            rid: draw(st.floats(min_value=0.0001, max_value=0.2, allow_nan=False))
            for rid in draw(st.lists(st.sampled_from(ids + extra), unique=True))
        }
        if ids + extra
        else {}
    )
    return states, deltas, cap, restore


@st.composite
def player_timelines(draw, regions: tuple[str, ...] = ("a", "b", "c"), max_len: int = 30):
    """A session timeline mixing the player's moves, region changes, GM work and NPC
    judgements in order (U7 TP-U7-6). Some region lines carry no ``region_id`` (pre-U7)."""
    from locus.play.models import TimelineEntry, TimelineKind

    kinds = [k.value for k in TimelineKind]
    entries = [
        TimelineEntry(
            session_id="s",
            turn=0,
            kind=TimelineKind.SESSION_STARTED,
            summary="start",
            payload={"region_id": draw(st.sampled_from(regions))},
        )
    ]
    for i in range(draw(st.integers(min_value=0, max_value=max_len))):
        kind = draw(st.sampled_from(kinds))
        payload: dict = {}
        if kind == TimelineKind.PLAYER_MOVED.value:
            to = draw(st.sampled_from(regions))
            payload = {"to_region_id": to, "region_id": to}
        elif draw(st.booleans()):
            payload["region_id"] = draw(st.sampled_from(regions))
        if kind == TimelineKind.EVENT_APPLIED.value:
            payload["event_id"] = draw(st.sampled_from(["e1", "e2"]))
        entries.append(
            TimelineEntry(session_id="s", turn=i // 3, kind=kind, summary=kind, payload=payload)
        )
    return entries
