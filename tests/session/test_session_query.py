"""S2 SessionQueryEngine tests — canonical + session overlay (FR-R5)."""

from __future__ import annotations

import pytest

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
from locus.session import InMemorySessionRepository
from locus.session.models import SessionRumor
from locus.session.query import SessionQueryEngine


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def _world():
    """Two connected regions; far has direct knowledge so near sees it as
    propagated/auto-rumor (which the NPC view must drop)."""
    near = Region(world_id="w", name="Near", level=RegionLevel.TOWN, provenance=_prov())
    far = Region(world_id="w", name="Far", level=RegionLevel.TOWN, provenance=_prov())
    k_near = Knowledge(world_id="w", statement="local fact", title="local", provenance=_prov())
    k_far = Knowledge(world_id="w", statement="far fact", title="far", provenance=_prov())
    scopes = [
        ScopeLink(
            world_id="w", knowledge_id=k_near.id, region_id=near.id, scope_type=ScopeType.DIRECT
        ),
        ScopeLink(
            world_id="w", knowledge_id=k_far.id, region_id=far.id, scope_type=ScopeType.DIRECT
        ),
    ]
    kg = KnowledgeGraph(world_id="w", knowledge=[k_near, k_far], scopes=scopes)
    conns = [
        ConnectionEdge(
            world_id="w",
            source_region_id=near.id,
            target_region_id=far.id,
            kind=ConnectionKind.ROUTE,
            weight=0.3,  # in rumor band -> auto-rumor view at 'near'
            provenance=_prov(),
        )
    ]
    topo = RegionTopology(world_id="w", regions=[near, far], connections=conns)
    return kg, topo, near, far, k_near, k_far


class _Loader:
    def __init__(self, kg, topo) -> None:
        self._kg, self._topo = kg, topo

    def load(self, world_id):
        return self._kg, self._topo


def test_npc_view_drops_propagated_and_autorumor_keeps_direct() -> None:
    kg, topo, near, far, k_near, k_far = _world()
    repo = InMemorySessionRepository()
    s = repo.create_session("w")
    engine = SessionQueryEngine(repo, _Loader(kg, topo))
    res = engine.knowledge_for_region(s.id, near.id)
    ids = {v.knowledge_id for v in res.items}
    assert k_near.id in ids  # direct kept
    assert k_far.id not in ids  # far fact reaches 'near' only as auto-rumor -> dropped


def test_promoted_rumor_appears_direct_like() -> None:
    kg, topo, near, *_ = _world()
    repo = InMemorySessionRepository()
    s = repo.create_session("w")
    promoted = SessionRumor(
        session_id=s.id,
        region_id=near.id,
        distorted_from_id="k",
        promoted=True,
        statement="a promoted rumor",
        confidence=0.5,
        provenance=_prov(),
    )
    plain = SessionRumor(
        session_id=s.id,
        region_id=near.id,
        distorted_from_id="k",
        promoted=False,
        statement="a plain rumor",
        confidence=0.5,
        provenance=_prov(),
    )
    repo.upsert_rumor(promoted)
    repo.upsert_rumor(plain)
    engine = SessionQueryEngine(repo, _Loader(kg, topo))
    res = engine.knowledge_for_region(s.id, near.id)
    item_ids = {v.knowledge_id for v in res.items}
    assert {promoted.id, plain.id} <= item_ids  # both shown
    assert promoted.id in res.unique_ids  # promoted treated direct-like
    assert plain.id not in res.unique_ids and plain.id not in res.shared_ids  # supplementary
    rumor_views = {v.knowledge_id: v for v in res.items if v.is_rumor}
    assert rumor_views[promoted.id].scope_type == ScopeType.DIRECT.value


def test_unknown_session_and_region_raise() -> None:
    kg, topo, near, *_ = _world()
    repo = InMemorySessionRepository()
    engine = SessionQueryEngine(repo, _Loader(kg, topo))
    with pytest.raises(LookupError):
        engine.knowledge_for_region("missing", near.id)
    s = repo.create_session("w")
    with pytest.raises(LookupError):
        engine.knowledge_for_region(s.id, "no-region")
