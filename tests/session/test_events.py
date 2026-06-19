"""P1 Event Foundation tests — SessionEvent model + GameMasterService manual lifecycle."""

from __future__ import annotations

import pytest

from locus.models import (
    KnowledgeGraph,
    Provenance,
    Region,
    RegionLevel,
    RegionTopology,
    SourceKind,
)
from locus.session import InMemorySessionRepository
from locus.session.game_master import GameMasterService, SessionClosedError
from locus.session.models import (
    CATEGORY_DEFAULT_LIFECYCLE,
    EventCategory,
    EventLifecycle,
    EventStatus,
    SessionEvent,
    TimelineKind,
    default_lifecycle,
)
from locus.session.rumor_generator import RumorDraft, RumorGenerator


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _FakeLLM:
    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="x")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


class _FakeLoader:
    def __init__(self) -> None:
        self.region = Region(world_id="w", name="Town", level=RegionLevel.TOWN, provenance=_prov())
        self._kg = KnowledgeGraph(world_id="w")
        self._topo = RegionTopology(world_id="w", regions=[self.region])

    def load(self, world_id):
        return self._kg, self._topo


def _setup():
    repo = InMemorySessionRepository()
    loader = _FakeLoader()
    gm = GameMasterService(repo, RumorGenerator(_FakeLLM()), loader)
    session = repo.create_session("w")
    return repo, loader, gm, session


# --- model / enums ---------------------------------------------------------- #
def test_default_lifecycle_mapping() -> None:
    assert default_lifecycle(EventCategory.WAR) == EventLifecycle.PERSISTENT
    assert default_lifecycle(EventCategory.PLAGUE) == EventLifecycle.PERSISTENT
    assert default_lifecycle(EventCategory.POLITICS) == EventLifecycle.PERSISTENT
    assert default_lifecycle(EventCategory.DISASTER) == EventLifecycle.ONE_SHOT
    assert default_lifecycle(EventCategory.FESTIVAL) == EventLifecycle.ONE_SHOT
    assert default_lifecycle(EventCategory.DISCOVERY) == EventLifecycle.ONE_SHOT
    assert set(CATEGORY_DEFAULT_LIFECYCLE) == set(EventCategory)


def test_event_serialization_roundtrip() -> None:
    e = SessionEvent(
        session_id="s",
        region_id="r",
        category=EventCategory.WAR,
        magnitude=0.5,
        provenance=Provenance(source=SourceKind.SESSION_EVENT),
    )
    assert SessionEvent.model_validate(e.model_dump()) == e
    assert e.contributions == {}  # BR-P1-12


def test_magnitude_out_of_range_rejected() -> None:
    with pytest.raises(ValueError):
        SessionEvent(
            session_id="s",
            region_id="r",
            category=EventCategory.WAR,
            magnitude=1.5,
            provenance=_prov(),
        )


# --- service: create -------------------------------------------------------- #
def test_create_event_active_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    ev = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.6)
    assert ev.status == EventStatus.ACTIVE.value
    assert ev.lifecycle == EventLifecycle.PERSISTENT.value  # category default
    assert ev.created_turn == 0 and ev.contributions == {}
    assert ev.provenance.generated_by == "gm:event"
    tl = repo.list_timeline(session.id)
    assert tl[-1].kind == TimelineKind.EVENT_CREATED.value
    assert tl[-1].payload["event_id"] == ev.id


def test_create_event_lifecycle_override() -> None:
    _repo, loader, gm, session = _setup()
    ev = gm.create_event(
        session.id,
        loader.region.id,
        category=EventCategory.WAR,
        magnitude=0.5,
        lifecycle=EventLifecycle.ONE_SHOT,
    )
    assert ev.lifecycle == EventLifecycle.ONE_SHOT.value


def test_create_event_unknown_region_raises() -> None:
    _repo, _loader, gm, session = _setup()
    with pytest.raises(LookupError):
        gm.create_event(session.id, "missing", category=EventCategory.WAR, magnitude=0.5)


def test_create_event_magnitude_clamped() -> None:
    _repo, loader, gm, session = _setup()
    ev = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=2.0)
    assert ev.magnitude == 1.0


# --- service: list / resolve / discard -------------------------------------- #
def test_list_events_status_filter() -> None:
    _repo, loader, gm, session = _setup()
    a = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.5)
    gm.resolve_event(session.id, a.id)
    gm.create_event(session.id, loader.region.id, category=EventCategory.FESTIVAL, magnitude=0.2)
    assert len(gm.list_events(session.id)) == 2
    assert len(gm.list_events(session.id, status="active")) == 1
    assert len(gm.list_events(session.id, status="resolved")) == 1


def test_resolve_event_idempotent_and_timeline() -> None:
    repo, loader, gm, session = _setup()
    ev = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.5)
    resolved = gm.resolve_event(session.id, ev.id)
    assert resolved.status == EventStatus.RESOLVED.value and resolved.resolved_turn == 0
    n_resolved = sum(
        1 for e in repo.list_timeline(session.id) if e.kind == TimelineKind.EVENT_RESOLVED.value
    )
    gm.resolve_event(session.id, ev.id)  # idempotent — no second timeline entry
    again = sum(
        1 for e in repo.list_timeline(session.id) if e.kind == TimelineKind.EVENT_RESOLVED.value
    )
    assert n_resolved == 1 and again == 1


def test_resolve_missing_event_raises() -> None:
    _repo, _loader, gm, session = _setup()
    with pytest.raises(LookupError):
        gm.resolve_event(session.id, "nope")


def test_discard_only_suggested() -> None:
    repo, loader, gm, session = _setup()
    ev = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.5)
    with pytest.raises(ValueError):  # ACTIVE cannot be discarded
        gm.discard_event(session.id, ev.id)
    # a SUGGESTED event (as P2 would create) can be discarded
    sug = SessionEvent(
        session_id=session.id,
        region_id=loader.region.id,
        category=EventCategory.WAR,
        magnitude=0.5,
        status=EventStatus.SUGGESTED,
        provenance=Provenance(source=SourceKind.SESSION_EVENT),
    )
    repo.create_event(sug)
    gm.discard_event(session.id, sug.id)
    assert repo.get_event(session.id, sug.id) is None


# --- guards ----------------------------------------------------------------- #
def test_closed_session_rejects_event_writes() -> None:
    repo, loader, gm, session = _setup()
    ev = gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.5)
    repo.close_session(session.id)
    with pytest.raises(SessionClosedError):
        gm.create_event(session.id, loader.region.id, category=EventCategory.WAR, magnitude=0.5)
    with pytest.raises(SessionClosedError):
        gm.resolve_event(session.id, ev.id)
    # reads still allowed on closed session
    assert len(gm.list_events(session.id)) == 1


def test_list_events_unknown_session_raises() -> None:
    _repo, _loader, gm, _session = _setup()
    with pytest.raises(LookupError):
        gm.list_events("missing")
