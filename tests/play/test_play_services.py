"""S2 GameMasterService tests — generate/regenerate/support/turn + timeline."""

from __future__ import annotations

import pytest

from locus.play import InMemoryPlayRepository
from locus.play.base import SessionClosedError
from locus.play.models import TimelineKind
from locus.play.rumor.generator import RumorDraft, RumorGenerator
from locus.shared.models import (
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
from tests.shared.snapshots import snapshot_of


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

    def get(self, world_id):
        return snapshot_of(self._kg, self._topo)


def _setup():
    repo = InMemoryPlayRepository()
    loader = _FakeLoader()
    gm = compose_play(repo, RumorGenerator(_FakeLLM()), loader)
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, loader.region.id, 0.3)
    return repo, loader, gm, session


def test_generate_rumors_creates_chain_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    rumors = gm.rumors.generate_rumors(session.id, loader.region.id)
    assert len(rumors) == 3  # one source (direct), 3-degree chain
    assert [round(r.distortion_degree, 3) for r in rumors] == [0.1, 0.2, 0.3]
    assert len(repo.list_rumors(session.id, loader.region.id)) == 3
    tl = repo.list_timeline(session.id)
    assert tl[-1].kind == TimelineKind.GENERATE.value
    assert set(tl[-1].payload["rumor_ids"]) == {r.id for r in rumors}


def test_regenerate_deletes_then_recreates() -> None:
    repo, loader, gm, session = _setup()
    first = gm.rumors.generate_rumors(session.id, loader.region.id)
    regen = gm.rumors.regenerate_region(session.id, loader.region.id).rumors
    ids_first = {r.id for r in first}
    ids_now = {r.id for r in repo.list_rumors(session.id, loader.region.id)}
    assert ids_now.isdisjoint(ids_first)  # old ones gone
    assert ids_now == {r.id for r in regen}
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.REGENERATE.value


def test_regenerate_preserves_promoted_rumors() -> None:
    # X3 / BR-X3-9: regen keeps promoted rumors, replaces only the rest.
    repo, loader, gm, session = _setup()
    first = gm.rumors.generate_rumors(session.id, loader.region.id)
    promoted = first[0]
    promoted.promoted = True
    repo.upsert_rumor(promoted)

    regen = gm.rumors.regenerate_region(session.id, loader.region.id).rumors
    now = repo.list_rumors(session.id, loader.region.id)
    ids_now = {r.id for r in now}
    assert promoted.id in ids_now  # promoted survived
    assert {r.id for r in first if not r.promoted}.isdisjoint(ids_now)  # non-promoted replaced
    assert promoted.id in {r.id for r in regen}  # returned set includes the kept one
    # review #1: regen must reseed from canonical only — the preserved promoted
    # rumor must NOT spawn an extra chain. 1 canonical source -> 3-degree chain +
    # the 1 kept promoted = 4; a re-seed from the promoted would inflate to 7.
    assert len(now) == 1 + 3
    tl_payload = repo.list_timeline(session.id)[-1].payload
    assert tl_payload["kept"] == [promoted.id]


def test_adjust_support_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    r = gm.rumors.generate_rumors(session.id, loader.region.id)[0]
    updated = gm.rumors.adjust_support(session.id, r.id, 1.5)  # clamps to 1.0
    assert updated.support == 1.0
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.ADJUST_SUPPORT.value
    with pytest.raises(LookupError):
        gm.rumors.adjust_support(session.id, "missing", 0.5)


def test_advance_turn_promotes_and_bumps() -> None:
    repo, loader, gm, session = _setup()
    r = gm.rumors.generate_rumors(session.id, loader.region.id)[0]
    gm.rumors.adjust_support(session.id, r.id, 0.9)
    result = gm.turns.advance(session.id).turns[-1]
    assert result.turn == 1 and result.promoted_ids == [r.id]
    assert repo.get_rumor(session.id, r.id).promoted is True
    kinds = [e.kind for e in repo.list_timeline(session.id)]
    assert TimelineKind.PROMOTE.value in kinds and TimelineKind.ADVANCE_TURN.value in kinds
    # demotion on a later turn when support drops
    gm.rumors.adjust_support(session.id, r.id, 0.1)
    result2 = gm.turns.advance(session.id).turns[-1]
    assert result2.turn == 2 and result2.demoted_ids == [r.id]
    assert repo.get_rumor(session.id, r.id).promoted is False


def test_set_region_distortion_timeline() -> None:
    repo, loader, gm, session = _setup()
    gm.distortions.set_region_distortion(session.id, loader.region.id, 0.8)
    assert repo.get_region_distortion(session.id, loader.region.id) == 0.8
    assert repo.list_timeline(session.id)[-1].kind == TimelineKind.SET_DISTORTION.value


def test_closed_session_rejects_writes() -> None:
    repo, loader, gm, session = _setup()
    repo.close_session(session.id)
    with pytest.raises(SessionClosedError):
        gm.rumors.generate_rumors(session.id, loader.region.id)
    with pytest.raises(SessionClosedError):
        gm.turns.advance(session.id).turns[-1]


def test_unknown_session_raises_lookup() -> None:
    _repo, loader, gm, _session = _setup()
    with pytest.raises(LookupError):
        gm.rumors.generate_rumors("missing", loader.region.id)


# --------------------------------------------------------------------------- #
# Code review U4 #3 — regenerate must not destroy rumors when the LLM is down
# --------------------------------------------------------------------------- #
class _DeadLLM:
    """Every call fails, so ``generate_chain`` swallows it and returns an empty chain."""

    def structured(self, prompt, schema, *, system=None):
        raise RuntimeError("provider unavailable")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        raise RuntimeError("provider unavailable")


def test_regenerate_keeps_everything_when_generation_produces_nothing() -> None:
    repo, loader, gm, session = _setup()
    first = gm.rumors.generate_rumors(session.id, loader.region.id)
    assert first  # something to lose
    gm.rumors._gen = RumorGenerator(_DeadLLM())  # the provider goes down

    regen = gm.rumors.regenerate_region(session.id, loader.region.id).rumors

    still_there = repo.list_rumors(session.id, loader.region.id)
    assert {r.id for r in still_there} == {r.id for r in first}  # nothing destroyed
    assert {r.id for r in regen} == {r.id for r in first}
    last = repo.list_timeline(session.id)[-1]
    assert last.kind == TimelineKind.REGENERATE.value
    assert last.payload["skipped"] is True and last.payload["deactivated"] == []


def test_regenerate_swaps_in_one_transaction() -> None:
    """A failure while swapping leaves the old rumors in place (BR-U4-14)."""
    repo, loader, gm, session = _setup()
    first = gm.rumors.generate_rumors(session.id, loader.region.id)

    original_upsert = repo.upsert_rumors

    def boom(rumors):
        raise RuntimeError("db hiccup")

    repo.upsert_rumors = boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        gm.rumors.regenerate_region(session.id, loader.region.id)
    repo.upsert_rumors = original_upsert  # type: ignore[method-assign]

    assert {r.id for r in repo.list_rumors(session.id, loader.region.id)} == {r.id for r in first}
    assert repo.list_timeline(session.id)[-1].kind != TimelineKind.REGENERATE.value
