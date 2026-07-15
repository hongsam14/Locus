"""P2 advance_turn integration + suggest/approve + resolve restore (FR-P2..P5)."""

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
from locus.session.event_suggester import EventDraft, EventDraftList, EventSuggester
from locus.session.game_master import GameMasterService, SessionClosedError
from locus.session.models import EventCategory, EventLifecycle, EventStatus, TimelineKind
from locus.session.rumor_generator import RumorDraft, RumorGenerator


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _RumorLLM:
    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="distorted")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _SuggestLLM:
    """Returns one valid draft for r1."""

    def structured(self, prompt, schema, *, system=None):
        return EventDraftList(
            drafts=[EventDraft(region_id="r1", category=EventCategory.WAR, magnitude=0.5)]
        )

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _BoomLLM:
    def structured(self, prompt, schema, *, system=None):
        raise RuntimeError("llm down")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _Loader:
    """Two regions r1<->r2 connected (weight 0.8); knowledge in r1."""

    def __init__(self) -> None:
        r1 = Region(world_id="w", name="R1", level=RegionLevel.TOWN, provenance=_prov())
        r1.id = "r1"
        r2 = Region(world_id="w", name="R2", level=RegionLevel.TOWN, provenance=_prov())
        r2.id = "r2"
        k = Knowledge(world_id="w", statement="fact", title="t", provenance=_prov())
        scope = ScopeLink(
            world_id="w", knowledge_id=k.id, region_id="r1", scope_type=ScopeType.DIRECT
        )
        conns = [
            ConnectionEdge(
                world_id="w",
                source_region_id="r1",
                target_region_id="r2",
                kind=ConnectionKind.ROUTE,
                weight=0.8,
                provenance=_prov(),
            ),
            ConnectionEdge(
                world_id="w",
                source_region_id="r2",
                target_region_id="r1",
                kind=ConnectionKind.ROUTE,
                weight=0.8,
                provenance=_prov(),
            ),
        ]
        self._kg = KnowledgeGraph(world_id="w", knowledge=[k], scopes=[scope])
        self._topo = RegionTopology(world_id="w", regions=[r1, r2], connections=conns)

    def load(self, world_id):
        return self._kg, self._topo


def _setup(*, suggester_llm=None):
    repo = InMemorySessionRepository()
    loader = _Loader()
    suggester = EventSuggester(suggester_llm) if suggester_llm is not None else None
    gm = GameMasterService(repo, RumorGenerator(_RumorLLM()), loader, suggester=suggester)
    session = repo.create_session("w")
    repo.set_region_distortion(session.id, "r1", 0.3)
    repo.set_region_distortion(session.id, "r2", 0.3)
    return repo, loader, gm, session


# --- event application + propagation ---------------------------------------- #
def test_advance_turn_applies_event_with_propagation() -> None:
    repo, _loader, gm, session = _setup()
    gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=1.0)  # persistent
    result = gm.advance_turn(session.id)
    assert result.turn == 1 and len(result.applied_event_ids) == 1
    # r1 target: 0.3 + 0.3(=1.0*MAX_EVENT_DELTA) = 0.6
    assert abs(repo.get_region_distortion(session.id, "r1") - 0.6) < 1e-9
    # r2 neighbor: 0.3 + 0.3*0.8 = 0.54
    assert abs(repo.get_region_distortion(session.id, "r2") - 0.54) < 1e-9
    kinds = [e.kind for e in repo.list_timeline(session.id)]
    assert TimelineKind.EVENT_APPLIED.value in kinds


def test_one_shot_auto_resolves_persistent_stays_active() -> None:
    repo, _loader, gm, session = _setup()
    one = gm.create_event(
        session.id, "r1", category=EventCategory.DISASTER, magnitude=0.5
    )  # one_shot
    per = gm.create_event(session.id, "r2", category=EventCategory.WAR, magnitude=0.5)  # persistent
    result = gm.advance_turn(session.id)
    assert one.id in result.resolved_event_ids
    assert repo.get_event(session.id, one.id).status == EventStatus.RESOLVED.value
    assert repo.get_event(session.id, per.id).status == EventStatus.ACTIVE.value


def test_persistent_accumulates_then_resolve_restores() -> None:
    repo, _loader, gm, session = _setup()
    ev = gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=1.0)  # persistent
    gm.advance_turn(session.id)  # r1: 0.6, r2: 0.54
    gm.advance_turn(session.id)  # r1: 0.9, r2: 0.78 (accumulate)
    assert abs(repo.get_region_distortion(session.id, "r1") - 0.9) < 1e-9
    # resolve restores the accumulated contributions symmetrically (target + neighbor)
    gm.resolve_event(session.id, ev.id)
    assert abs(repo.get_region_distortion(session.id, "r1") - 0.3) < 1e-9
    assert abs(repo.get_region_distortion(session.id, "r2") - 0.3) < 1e-9
    assert repo.get_event(session.id, ev.id).status == EventStatus.RESOLVED.value


def test_resolve_restores_baseline_even_after_saturation() -> None:
    """After distortion clamps to 1.0, resolve must restore to baseline (0.3),
    not below it — contributions track the effective (post-clamp) applied delta."""
    repo, _loader, gm, session = _setup()
    ev = gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=1.0)  # persistent
    gm.advance_turn(session.id)  # r1: 0.6
    gm.advance_turn(session.id)  # r1: 0.9
    gm.advance_turn(session.id)  # r1: clamp(1.2) -> 1.0 (r2 also saturates)
    assert abs(repo.get_region_distortion(session.id, "r1") - 1.0) < 1e-9
    gm.resolve_event(session.id, ev.id)
    # exactly back to baseline, never below (would drop to 0.1 with raw-delta restore)
    assert abs(repo.get_region_distortion(session.id, "r1") - 0.3) < 1e-9
    assert abs(repo.get_region_distortion(session.id, "r2") - 0.3) < 1e-9


def test_empty_turn_does_not_decay_support() -> None:
    """A turn with no active events must leave rumor support untouched (no blanket
    decay that would silently demote promoted rumors)."""
    repo, _loader, gm, session = _setup()
    r = gm.generate_rumors(session.id, "r1")[0]
    gm.adjust_support(session.id, r.id, 0.6)
    gm.advance_turn(session.id)  # no active events
    assert abs(repo.get_rumor(session.id, r.id).support - 0.6) < 1e-9


# --- rumor append + support evolution + promotion --------------------------- #
def test_primary_region_rumors_appended_preserving_existing() -> None:
    repo, _loader, gm, session = _setup()
    first = gm.generate_rumors(session.id, "r1")  # manual chain (3)
    gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=0.3)
    gm.advance_turn(session.id)
    now = repo.list_rumors(session.id, "r1")
    assert len(now) > len(first)  # appended, not wiped
    assert {r.id for r in first} <= {r.id for r in now}  # originals preserved


def test_support_evolution_influenced_vs_not() -> None:
    repo, _loader, gm, session = _setup()
    r1_rumor = gm.generate_rumors(session.id, "r1")[0]
    gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=0.3)
    before = repo.get_rumor(session.id, r1_rumor.id).support
    gm.advance_turn(session.id)
    after = repo.get_rumor(session.id, r1_rumor.id).support
    assert after > before  # r1 influenced -> reinforced


def test_advance_turn_no_events_still_bumps_and_promotes() -> None:
    """Phase 1 regression: advance_turn without events behaves as before."""
    repo, _loader, gm, session = _setup()
    r = gm.generate_rumors(session.id, "r1")[0]
    gm.adjust_support(session.id, r.id, 0.9)
    result = gm.advance_turn(session.id)
    assert result.turn == 1 and r.id in result.promoted_ids
    assert result.applied_event_ids == []


# --- suggest / approve ------------------------------------------------------ #
def test_suggest_then_approve_flow() -> None:
    repo, _loader, gm, session = _setup(suggester_llm=_SuggestLLM())
    suggested = gm.suggest_events(session.id, n=1)
    assert len(suggested) == 1 and suggested[0].status == EventStatus.SUGGESTED.value
    assert suggested[0].provenance.generated_by == "llm:event"
    # not applied while suggested
    gm.advance_turn(session.id)
    assert repo.get_region_distortion(session.id, "r1") == 0.3
    # approve -> active -> next turn applies
    gm.approve_event(session.id, suggested[0].id)
    assert repo.get_event(session.id, suggested[0].id).status == EventStatus.ACTIVE.value
    gm.advance_turn(session.id)
    assert repo.get_region_distortion(session.id, "r1") > 0.3


def test_suggest_graceful_on_llm_failure() -> None:
    _repo, _loader, gm, session = _setup(suggester_llm=_BoomLLM())
    assert gm.suggest_events(session.id, n=2) == []


def test_suggest_without_suggester_returns_empty() -> None:
    _repo, _loader, gm, session = _setup()  # no suggester
    assert gm.suggest_events(session.id) == []


def test_approve_non_suggested_rejected() -> None:
    _repo, _loader, gm, session = _setup()
    ev = gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=0.5)  # ACTIVE
    with pytest.raises(ValueError):
        gm.approve_event(session.id, ev.id)


def test_closed_session_rejects_advance_and_suggest() -> None:
    repo, _loader, gm, session = _setup(suggester_llm=_SuggestLLM())
    repo.close_session(session.id)
    with pytest.raises(SessionClosedError):
        gm.advance_turn(session.id)
    with pytest.raises(SessionClosedError):
        gm.suggest_events(session.id)


def test_lifecycle_value_is_string() -> None:
    """use_enum_values=True: stored lifecycle compares as the string value."""
    _repo, _loader, gm, session = _setup()
    ev = gm.create_event(session.id, "r1", category=EventCategory.WAR, magnitude=0.5)
    assert ev.lifecycle == EventLifecycle.PERSISTENT.value
