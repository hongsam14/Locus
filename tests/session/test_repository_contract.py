"""S1 SessionRepository port contract tests (in-memory adapter, NFR-R1).

These exercise the behaviour the PostgreSQL adapter must also satisfy: CRUD,
timeline ordering (turn then created_at), distortion upsert/uniqueness and
session isolation (BR-S1-12/13/15).
"""

from __future__ import annotations

from locus.models import Provenance, SourceKind
from locus.session import InMemorySessionRepository, SessionRepository
from locus.session.models import (
    EventCategory,
    EventStatus,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)


def _repo() -> InMemorySessionRepository:
    return InMemorySessionRepository()


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_in_memory_satisfies_protocol() -> None:
    assert isinstance(_repo(), SessionRepository)


def test_session_crud_and_history() -> None:
    repo = _repo()
    a = repo.create_session("w1")
    b = repo.create_session("w1")
    repo.create_session("w2")
    assert a.status == SessionStatus.OPEN.value and a.turn == 0 and a.created_at is not None
    assert {s.id for s in repo.list_sessions("w1")} == {a.id, b.id}
    assert [s.id for s in repo.list_sessions("w2")] != [a.id]
    assert repo.get_session(a.id).world_id == "w1"
    assert repo.get_session("nope") is None


def test_close_is_idempotent() -> None:
    repo = _repo()
    s = repo.create_session("w")
    closed = repo.close_session(s.id)
    assert closed.status == SessionStatus.CLOSED.value and closed.closed_at is not None
    first_closed_at = closed.closed_at
    again = repo.close_session(s.id)
    assert again.closed_at == first_closed_at  # unchanged on repeat


def test_bump_turn() -> None:
    repo = _repo()
    s = repo.create_session("w")
    assert repo.bump_turn(s.id) == 1
    assert repo.bump_turn(s.id) == 2
    assert repo.get_session(s.id).turn == 2


def test_rumor_crud_and_region_filter() -> None:
    repo = _repo()
    s = repo.create_session("w")
    r1 = repo.upsert_rumor(
        SessionRumor(session_id=s.id, region_id="rA", distorted_from_id="k", provenance=_prov())
    )
    repo.upsert_rumor(
        SessionRumor(session_id=s.id, region_id="rB", distorted_from_id="k", provenance=_prov())
    )
    assert len(repo.list_rumors(s.id)) == 2
    assert [r.region_id for r in repo.list_rumors(s.id, region_id="rA")] == ["rA"]
    # upsert updates in place
    r1.support = 0.9
    repo.upsert_rumor(r1)
    assert repo.get_rumor(s.id, r1.id).support == 0.9
    repo.delete_rumor(s.id, r1.id)
    assert repo.get_rumor(s.id, r1.id) is None


def test_region_distortion_upsert_unique() -> None:
    repo = _repo()
    s = repo.create_session("w")
    repo.set_region_distortion(s.id, "r1", 0.3)
    repo.set_region_distortion(s.id, "r1", 0.8)  # upsert, not duplicate
    assert repo.get_region_distortion(s.id, "r1") == 0.8
    assert repo.get_region_distortion(s.id, "missing") is None
    repo.set_region_distortion(s.id, "r2", 0.5)
    assert len(repo.list_region_distortions(s.id)) == 2


def test_timeline_ordering_by_turn_then_created_at() -> None:
    repo = _repo()
    s = repo.create_session("w")
    # append out of order; expect (turn, created_at) ordering
    repo.append_timeline(TimelineEntry(session_id=s.id, turn=1, kind=TimelineKind.ADVANCE_TURN))
    repo.append_timeline(TimelineEntry(session_id=s.id, turn=0, kind=TimelineKind.GENERATE))
    repo.append_timeline(TimelineEntry(session_id=s.id, turn=0, kind=TimelineKind.ADJUST_SUPPORT))
    ordered = repo.list_timeline(s.id)
    assert [e.turn for e in ordered] == [0, 0, 1]
    assert [e.kind for e in ordered] == [
        TimelineKind.GENERATE.value,
        TimelineKind.ADJUST_SUPPORT.value,
        TimelineKind.ADVANCE_TURN.value,
    ]
    assert all(e.created_at is not None for e in ordered)


def test_session_isolation() -> None:
    repo = _repo()
    a = repo.create_session("w")
    b = repo.create_session("w")
    repo.upsert_rumor(
        SessionRumor(session_id=a.id, region_id="r", distorted_from_id="k", provenance=_prov())
    )
    repo.set_region_distortion(a.id, "r", 0.4)
    repo.append_timeline(TimelineEntry(session_id=a.id, turn=0, kind=TimelineKind.GENERATE))
    repo.create_event(_event(a.id))
    assert repo.list_rumors(b.id) == []
    assert repo.list_region_distortions(b.id) == []
    assert repo.list_timeline(b.id) == []
    assert repo.list_events(b.id) == []


def _event(session_id: str, *, region_id: str = "rA", turn: int = 0) -> SessionEvent:
    return SessionEvent(
        session_id=session_id,
        region_id=region_id,
        category=EventCategory.WAR,
        magnitude=0.6,
        created_turn=turn,
        provenance=Provenance(source=SourceKind.SESSION_EVENT),
    )


def test_event_crud_and_status_filter() -> None:
    repo = _repo()
    s = repo.create_session("w")
    e1 = repo.create_event(_event(s.id, turn=0))
    e2 = repo.create_event(_event(s.id, region_id="rB", turn=1))
    assert {e.id for e in repo.list_events(s.id)} == {e1.id, e2.id}
    assert [e.id for e in repo.list_events(s.id)] == [e1.id, e2.id]  # created_turn order
    assert repo.get_event(s.id, e1.id).region_id == "rA"
    # update: status transition + resolved_turn + contributions
    e1.status = EventStatus.RESOLVED
    e1.resolved_turn = 2
    e1.contributions = {"rA": 0.2}
    repo.update_event(e1)
    got = repo.get_event(s.id, e1.id)
    assert got.status == EventStatus.RESOLVED.value and got.resolved_turn == 2
    assert got.contributions == {"rA": 0.2}
    assert [e.id for e in repo.list_events(s.id, status="active")] == [e2.id]
    repo.delete_event(s.id, e2.id)
    assert repo.get_event(s.id, e2.id) is None
