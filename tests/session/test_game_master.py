"""S2 GameMasterService tests — generate/regenerate/support/turn + timeline."""

from __future__ import annotations

import pytest

from locus.models import (
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
from locus.session.game_master import GameMasterService, SessionClosedError
from locus.session.models import TimelineKind
from locus.session.rumor_generator import RumorDraft, RumorGenerator


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _FakeLLM:
    def __init__(self) -> None:
        self.calls = 0

    def structured(self, prompt, schema, *, system=None):
        self.calls += 1
        return RumorDraft(statement=f"distorted#{self.calls}")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _FakeLoader:
    def __init__(self) -> None:
        self.region = Region(world_id="w", name="Town", level=RegionLevel.TOWN, provenance=_prov())
        self.k = Knowledge(
            world_id="w", statement="The bridge is safe.", title="bridge", provenance=_prov()
        )
        scope = ScopeLink(
            world_id="w",
            knowledge_id=self.k.id,
            region_id=self.region.id,
            scope_type=ScopeType.DIRECT,
        )
        self._kg = KnowledgeGraph(world_id="w", knowledge=[self.k], scopes=[scope])
        self._topo = RegionTopology(world_id="w", regions=[self.region])

    def load(self, world_id):
        return self._kg, self._topo


def _setup():
    repo = InMemorySessionRepository()
    loader = _FakeLoader()
    gm = GameMasterService(repo, RumorGenerator(_FakeLLM()), loader)
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, loader.region.id, 0.3)
    return repo, loader, gm, session


def test_generate_rumors_creates_chain_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    rumors = gm.generate_rumors(session.id, loader.region.id)
    assert len(rumors) == 3  # one source (direct), 3-degree chain
    assert [round(r.distortion_degree, 3) for r in rumors] == [0.1, 0.2, 0.3]
    assert len(repo.list_rumors(session.id, loader.region.id)) == 3
    tl = repo.list_timeline(session.id)
    assert tl[-1].kind == TimelineKind.GENERATE.value
    assert set(tl[-1].payload["rumor_ids"]) == {r.id for r in rumors}


def test_regenerate_deletes_then_recreates() -> None:
    repo, loader, gm, session = _setup()
    first = gm.generate_rumors(session.id, loader.region.id)
    regen = gm.regenerate_region(session.id, loader.region.id)
    ids_first = {r.id for r in first}
    ids_now = {r.id for r in repo.list_rumors(session.id, loader.region.id)}
    assert ids_now.isdisjoint(ids_first)  # old ones gone
    assert ids_now == {r.id for r in regen}
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.REGENERATE.value


def test_adjust_support_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    r = gm.generate_rumors(session.id, loader.region.id)[0]
    updated = gm.adjust_support(session.id, r.id, 1.5)  # clamps to 1.0
    assert updated.support == 1.0
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.ADJUST_SUPPORT.value
    with pytest.raises(LookupError):
        gm.adjust_support(session.id, "missing", 0.5)


def test_advance_turn_promotes_and_bumps() -> None:
    repo, loader, gm, session = _setup()
    r = gm.generate_rumors(session.id, loader.region.id)[0]
    gm.adjust_support(session.id, r.id, 0.9)
    result = gm.advance_turn(session.id)
    assert result.turn == 1 and result.promoted_ids == [r.id]
    assert repo.get_rumor(session.id, r.id).promoted is True
    kinds = [e.kind for e in repo.list_timeline(session.id)]
    assert TimelineKind.PROMOTE.value in kinds and TimelineKind.ADVANCE_TURN.value in kinds
    # demotion on a later turn when support drops
    gm.adjust_support(session.id, r.id, 0.1)
    result2 = gm.advance_turn(session.id)
    assert result2.turn == 2 and result2.demoted_ids == [r.id]
    assert repo.get_rumor(session.id, r.id).promoted is False


def test_set_region_distortion_timeline() -> None:
    repo, loader, gm, session = _setup()
    gm.set_region_distortion(session.id, loader.region.id, 0.8)
    assert repo.get_region_distortion(session.id, loader.region.id) == 0.8
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.SET_DISTORTION.value


def test_closed_session_rejects_writes() -> None:
    repo, loader, gm, session = _setup()
    repo.close_session(session.id)
    with pytest.raises(SessionClosedError):
        gm.generate_rumors(session.id, loader.region.id)
    with pytest.raises(SessionClosedError):
        gm.advance_turn(session.id)


def test_unknown_session_raises_lookup() -> None:
    _repo, loader, gm, _session = _setup()
    with pytest.raises(LookupError):
        gm.generate_rumors("missing", loader.region.id)
