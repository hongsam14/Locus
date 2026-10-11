"""V7 — what a region knows is shown and seeded in the consensus order (TP-V7-3, BR-V7-05).

The consensus sorts each list once (Q1 = A); the play screen's facts and the rumor
seeds read that order as it is. The player's first three lines are the most certain
facts; rumor seeds take the region's own knowledge most certain first, then what
travels in — a 0.3 direct fact seeds before a 0.9 propagated one (code review #20).
"""

from __future__ import annotations

from locus.play import InMemoryPlayRepository
from locus.play.region_knowledge import SessionKnowledgeService
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
from tests.play.helpers import compose_play
from tests.play.test_player_mode import CountingGenerator
from tests.shared.snapshots import StaticSnapshots, snapshot_of


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _world():
    here = Region(id="here", world_id="w", name="Here", level=RegionLevel.TOWN, provenance=_prov())
    road = Region(id="road", world_id="w", name="Road", level=RegionLevel.TOWN, provenance=_prov())
    known = {  # knowledge id -> scope confidence; listed least certain first
        "k-low": 0.3,
        "k-high": 0.95,
        "k-mid": 0.6,
        "k-top": 0.99,
    }
    knowledge = [
        Knowledge(id=kid, world_id="w", statement=kid, title=kid, provenance=_prov())
        for kid in [*known, "k-far"]
    ]
    scopes = [
        ScopeLink(
            world_id="w",
            knowledge_id=kid,
            region_id="here",
            scope_type=ScopeType.DIRECT,
            confidence=conf,
        )
        for kid, conf in known.items()
    ] + [
        ScopeLink(world_id="w", knowledge_id="k-far", region_id="road", scope_type=ScopeType.DIRECT)
    ]
    conns = [
        ConnectionEdge(
            world_id="w",
            source_region_id=a,
            target_region_id=b,
            kind=ConnectionKind.ROUTE,
            weight=0.9,
            provenance=_prov(),
        )
        for a, b in (("here", "road"), ("road", "here"))
    ]
    kg = KnowledgeGraph(world_id="w", knowledge=knowledge, scopes=scopes)
    topo = RegionTopology(world_id="w", regions=[here, road], connections=conns)
    return snapshot_of(kg, topo)


def test_tp_v7_3_the_play_screens_facts_come_confident_first() -> None:
    repo = InMemoryPlayRepository()
    s = repo.create_session("w")
    src = SessionKnowledgeService(repo, StaticSnapshots(_world())).region_sources(s.id, "here")
    assert [k.knowledge_id for k in src.facts][:3] == ["k-top", "k-high", "k-mid"]


def test_br_v7_05_rumor_seeds_follow_the_consensus_order() -> None:
    """``_collect_sources`` reads direct + propagated in the consensus order: the direct
    knowledge most certain first, then what travels in from the road (k-far, 0.9 after
    the path, comes after k-low, 0.3 direct)."""
    repo = InMemoryPlayRepository()
    s = repo.create_session("w")
    gen = CountingGenerator()
    play = compose_play(repo, gen, StaticSnapshots(_world()))
    play.rumors.generate_rumors(s.id, "here", degrees=[0.2])
    assert gen.sources == ["k-top", "k-high", "k-mid", "k-low", "k-far"]
