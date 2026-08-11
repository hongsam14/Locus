"""PostgresSessionRepository tests — run the real adapter against in-memory SQLite.

The adapter uses dialect-portable types (JSON/JSONB variant, CURRENT_TIMESTAMP),
so the same code path is exercised offline. Live PostgreSQL is operator-run
(Build & Test). Verifies row<->model mapping, ordering, idempotent close and
session isolation (the same contract as the in-memory adapter).
"""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402

from locus.models import Provenance, SourceKind  # noqa: E402
from locus.session import SessionRepository  # noqa: E402
from locus.session.models import (  # noqa: E402
    EventCategory,
    EventLifecycle,
    EventStatus,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.storage.postgres_session_repo import PostgresSessionRepository  # noqa: E402


@pytest.fixture()
def repo() -> PostgresSessionRepository:
    engine = create_engine("sqlite://", future=True)
    r = PostgresSessionRepository(engine=engine)
    r.ensure_schema()
    return r


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_satisfies_protocol(repo: PostgresSessionRepository) -> None:
    assert isinstance(repo, SessionRepository)
    assert repo.health_check() is True


def test_ensure_schema_idempotent(repo: PostgresSessionRepository) -> None:
    repo.ensure_schema()  # second call must not raise
    repo.ensure_schema()


def test_session_lifecycle_and_history(repo: PostgresSessionRepository) -> None:
    a = repo.create_session("w1")
    repo.create_session("w1")
    repo.create_session("w2")
    assert a.status == SessionStatus.OPEN.value and a.turn == 0 and a.created_at is not None
    assert len(repo.list_sessions("w1")) == 2
    assert len(repo.list_sessions("w2")) == 1
    assert repo.get_session(a.id).world_id == "w1"
    assert repo.get_session("missing") is None


def test_close_idempotent_and_bump(repo: PostgresSessionRepository) -> None:
    s = repo.create_session("w")
    closed = repo.close_session(s.id)
    assert closed.status == SessionStatus.CLOSED.value and closed.closed_at is not None
    first = closed.closed_at
    assert repo.close_session(s.id).closed_at == first
    assert repo.bump_turn(s.id) == 1
    assert repo.bump_turn(s.id) == 2
    with pytest.raises(KeyError):
        repo.bump_turn("missing")


def test_rumor_roundtrip_and_upsert(repo: PostgresSessionRepository) -> None:
    s = repo.create_session("w")
    r = SessionRumor(
        session_id=s.id,
        region_id="rA",
        distorted_from_id="k1",
        statement="rumor text",
        distortion_degree=0.5,
        support=0.4,
        confidence=0.5,
        provenance=_prov(),
    )
    repo.upsert_rumor(r)
    got = repo.get_rumor(s.id, r.id)
    assert got == r
    r.support = 0.95
    r.promoted = True
    repo.upsert_rumor(r)
    assert repo.get_rumor(s.id, r.id).support == 0.95
    assert repo.get_rumor(s.id, r.id).promoted is True
    repo.delete_rumor(s.id, r.id)
    assert repo.get_rumor(s.id, r.id) is None


def test_batch_upsert_and_soft_flag(repo: PostgresSessionRepository) -> None:
    """U-H1: batch upsert_rumors + active soft-flag round-trip via the real
    adapter (SQLite). Pruned rumors are hidden unless include_pruned (FR-H5 / BR-H1-6)."""
    s = repo.create_session("w")
    live = SessionRumor(session_id=s.id, region_id="rA", distorted_from_id="k", provenance=_prov())
    dead = SessionRumor(
        session_id=s.id, region_id="rA", distorted_from_id="k", active=False, provenance=_prov()
    )
    saved = repo.upsert_rumors([live, dead])
    assert len(saved) == 2
    assert [r.id for r in repo.list_rumors(s.id)] == [live.id]  # active-only default
    both = {r.id for r in repo.list_rumors(s.id, include_pruned=True)}
    assert both == {live.id, dead.id}
    assert repo.get_rumor(s.id, dead.id).active is False  # column round-trips


def test_region_distortion_upsert(repo: PostgresSessionRepository) -> None:
    s = repo.create_session("w")
    repo.set_region_distortion(s.id, "r1", 0.3)
    repo.set_region_distortion(s.id, "r1", 0.8)
    assert repo.get_region_distortion(s.id, "r1") == 0.8
    assert repo.get_region_distortion(s.id, "x") is None
    repo.set_region_distortion(s.id, "r2", 0.5)
    assert len(repo.list_region_distortions(s.id)) == 2


def test_timeline_ordering(repo: PostgresSessionRepository) -> None:
    s = repo.create_session("w")
    repo.append_timeline(TimelineEntry(session_id=s.id, turn=1, kind=TimelineKind.ADVANCE_TURN))
    repo.append_timeline(
        TimelineEntry(session_id=s.id, turn=0, kind=TimelineKind.GENERATE, payload={"ids": ["a"]})
    )
    ordered = repo.list_timeline(s.id)
    assert [e.turn for e in ordered] == [0, 1]
    assert ordered[0].payload == {"ids": ["a"]}
    assert all(e.created_at is not None for e in ordered)


def test_session_isolation(repo: PostgresSessionRepository) -> None:
    a = repo.create_session("w")
    b = repo.create_session("w")
    repo.upsert_rumor(
        SessionRumor(session_id=a.id, region_id="r", distorted_from_id="k", provenance=_prov())
    )
    assert repo.list_rumors(b.id) == []


def test_event_roundtrip_update_and_filter(repo: PostgresSessionRepository) -> None:
    s = repo.create_session("w")
    e = SessionEvent(
        session_id=s.id,
        region_id="rA",
        category=EventCategory.WAR,
        description="border skirmish",
        magnitude=0.7,
        lifecycle=EventLifecycle.PERSISTENT,
        status=EventStatus.ACTIVE,
        created_turn=0,
        provenance=Provenance(source=SourceKind.SESSION_EVENT, generated_by="gm:event"),
    )
    repo.create_event(e)
    assert repo.get_event(s.id, e.id) == e
    # update: resolve + contributions (JSONB roundtrip)
    e.status = EventStatus.RESOLVED
    e.resolved_turn = 3
    e.contributions = {"rA": 0.23, "rB": 0.1}
    repo.update_event(e)
    got = repo.get_event(s.id, e.id)
    assert got.status == EventStatus.RESOLVED.value and got.resolved_turn == 3
    assert got.contributions == {"rA": 0.23, "rB": 0.1}
    # status filter + ordering
    repo.create_event(
        SessionEvent(
            session_id=s.id,
            region_id="rB",
            category=EventCategory.FESTIVAL,
            magnitude=0.2,
            created_turn=1,
            provenance=Provenance(source=SourceKind.SESSION_EVENT),
        )
    )
    assert [ev.region_id for ev in repo.list_events(s.id, status="active")] == ["rB"]
    assert [ev.created_turn for ev in repo.list_events(s.id)] == [0, 1]
    repo.delete_event(s.id, e.id)
    assert repo.get_event(s.id, e.id) is None
