"""PostgresPlayRepository tests — run the real adapter against in-memory SQLite.

The adapter uses dialect-portable types (JSON/JSONB variant, CURRENT_TIMESTAMP),
so the same code path is exercised offline. Live PostgreSQL is operator-run
(Build & Test). Verifies row<->model mapping, ordering, idempotent close and
session isolation (the same contract as the in-memory adapter).
"""

from __future__ import annotations

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy import create_engine  # noqa: E402

from locus.play import PlayRepository  # noqa: E402
from locus.play.models import (  # noqa: E402
    EventCategory,
    EventLifecycle,
    EventStatus,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.play.storage.postgres_repo import PostgresPlayRepository  # noqa: E402
from locus.shared.models import Provenance, SourceKind  # noqa: E402


@pytest.fixture()
def repo() -> PostgresPlayRepository:
    engine = create_engine("sqlite://", future=True)
    r = PostgresPlayRepository(engine=engine)
    r.ensure_schema()
    return r


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_satisfies_protocol(repo: PostgresPlayRepository) -> None:
    assert isinstance(repo, PlayRepository)
    assert repo.health_check() is True


def test_ensure_schema_idempotent(repo: PostgresPlayRepository) -> None:
    repo.ensure_schema()  # second call must not raise
    repo.ensure_schema()


def test_session_lifecycle_and_history(repo: PostgresPlayRepository) -> None:
    a = repo.create_session("w1")
    repo.create_session("w1")
    repo.create_session("w2")
    assert a.status == SessionStatus.OPEN.value and a.turn == 0 and a.created_at is not None
    assert len(repo.list_sessions("w1")) == 2
    assert len(repo.list_sessions("w2")) == 1
    assert repo.get_session(a.id).world_id == "w1"
    assert repo.get_session("missing") is None


def test_close_idempotent_and_bump(repo: PostgresPlayRepository) -> None:
    s = repo.create_session("w")
    closed = repo.close_session(s.id)
    assert closed.status == SessionStatus.CLOSED.value and closed.closed_at is not None
    first = closed.closed_at
    assert repo.close_session(s.id).closed_at == first
    assert repo.bump_turn(s.id) == 1
    assert repo.bump_turn(s.id) == 2
    with pytest.raises(KeyError):
        repo.bump_turn("missing")


def test_rumor_roundtrip_and_upsert(repo: PostgresPlayRepository) -> None:
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


def test_batch_upsert_and_soft_flag(repo: PostgresPlayRepository) -> None:
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


def test_region_distortion_upsert(repo: PostgresPlayRepository) -> None:
    s = repo.create_session("w")
    repo.set_region_distortion(s.id, "r1", 0.3)
    repo.set_region_distortion(s.id, "r1", 0.8)
    assert repo.get_region_distortion(s.id, "r1") == 0.8
    assert repo.get_region_distortion(s.id, "x") is None
    repo.set_region_distortion(s.id, "r2", 0.5)
    assert len(repo.list_region_distortions(s.id)) == 2


def test_timeline_ordering(repo: PostgresPlayRepository) -> None:
    s = repo.create_session("w")
    repo.append_timeline(TimelineEntry(session_id=s.id, turn=1, kind=TimelineKind.ADVANCE_TURN))
    repo.append_timeline(
        TimelineEntry(session_id=s.id, turn=0, kind=TimelineKind.GENERATE, payload={"ids": ["a"]})
    )
    ordered = repo.list_timeline(s.id)
    assert [e.turn for e in ordered] == [0, 1]
    assert ordered[0].payload == {"ids": ["a"]}
    assert all(e.created_at is not None for e in ordered)


def test_session_isolation(repo: PostgresPlayRepository) -> None:
    a = repo.create_session("w")
    b = repo.create_session("w")
    repo.upsert_rumor(
        SessionRumor(session_id=a.id, region_id="r", distorted_from_id="k", provenance=_prov())
    )
    assert repo.list_rumors(b.id) == []


def test_event_roundtrip_update_and_filter(repo: PostgresPlayRepository) -> None:
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
        provenance=Provenance(source=SourceKind.SIMULATION, generated_by="gm:event"),
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
            provenance=Provenance(source=SourceKind.SIMULATION),
        )
    )
    assert [ev.region_id for ev in repo.list_events(s.id, status="active")] == ["rB"]
    assert [ev.created_turn for ev in repo.list_events(s.id)] == [0, 1]
    repo.delete_event(s.id, e.id)
    assert repo.get_event(s.id, e.id) is None


# --------------------------------------------------------------------------- #
# U4 — players, turn runs, unit of work on the SQL adapter (Step 3.5; EX-19)
# --------------------------------------------------------------------------- #
def test_u4_sql_player_and_run_round_trip(repo: PostgresPlayRepository) -> None:
    from locus.play.models import (
        ActionResult,
        MoveAction,
        Player,
        TurnResult,
        TurnRun,
        TurnRunStatus,
    )

    s = repo.create_session("w")
    p = repo.create_player(Player(session_id=s.id, name="Ari", region_id="r1"))
    assert repo.get_player(s.id).name == "Ari" and p.created_at is not None
    with pytest.raises(ValueError):
        repo.create_player(Player(session_id=s.id, name="Bo", region_id="r1"))
    p.region_id = "r2"
    assert repo.update_player(p).region_id == "r2"
    run = repo.create_run(
        TurnRun(session_id=s.id, action=MoveAction(to_region_id="r2"), cost_turns=2)
    )
    assert run.started_at is not None and run.action.to_region_id == "r2"
    run.status = TurnRunStatus.DONE
    run.result = ActionResult(session=s, player=p, turns=[TurnResult(session_id=s.id, turn=1)])
    saved = repo.update_run(run)
    assert saved.status == "done" and saved.result.turns[0].turn == 1
    assert repo.get_run("other", run.id) is None
    assert [r.id for r in repo.list_runs(s.id, "done")] == [run.id]
    assert repo.fail_stale_runs(reason="interrupted") == 0


def test_u4_sql_uow_rolls_back_everything(repo: PostgresPlayRepository) -> None:
    """EX-19 on SQLite: events, distortions, rumors and runs inside a failing
    unit of work are all discarded (BR-U4-14)."""
    from locus.play.models import SessionRumor, TurnRun

    s = repo.create_session("w")
    repo.set_region_distortion(s.id, "r1", 0.3)
    with pytest.raises(RuntimeError):
        with repo.uow() as u:
            u.distortions.set_region_distortion(s.id, "r1", 0.8)
            u.rumors.upsert_rumors(
                [
                    SessionRumor(
                        session_id=s.id, region_id="r1", distorted_from_id="k", provenance=_prov()
                    )
                ]
            )
            u.runs.create_run(TurnRun(session_id=s.id))
            u.sessions.bump_turn(s.id)
            raise RuntimeError("boom")
    assert repo.get_region_distortion(s.id, "r1") == 0.3
    assert repo.list_rumors(s.id) == [] and repo.list_runs(s.id) == []
    assert repo.get_session(s.id).turn == 0
    with repo.uow() as u:  # clean exit commits
        u.sessions.bump_turn(s.id)
    assert repo.get_session(s.id).turn == 1


def test_u4_timeline_keeps_append_order_within_one_transaction(
    repo: PostgresPlayRepository,
) -> None:
    """Code review U4 #1: a whole turn is written in one transaction, where the DB's
    CURRENT_TIMESTAMP is constant — entries must still come back in append order."""
    from locus.play.models import TimelineKind

    s = repo.create_session("w")
    kinds = [
        TimelineKind.EVENT_APPLIED,
        TimelineKind.PRUNE,
        TimelineKind.PROMOTE,
        TimelineKind.ADVANCE_TURN,
    ]
    with repo.uow() as u:
        for kind in kinds:
            u.timeline.append_timeline(
                TimelineEntry(session_id=s.id, turn=0, kind=kind, summary=str(kind), payload={})
            )
    got = repo.list_timeline(s.id)
    assert [e.kind for e in got] == [k.value for k in kinds]
    stamps = [e.created_at for e in got]
    assert all(a < b for a, b in zip(stamps, stamps[1:], strict=False))  # strictly increasing


# --------------------------------------------------------------------------- #
# U5 — conversations on the SQL adapter (Step 4.3). The PostgreSQL transaction abort
# on a unique violation is operator-run: SQLite cannot reproduce it (plan review R-15).
# --------------------------------------------------------------------------- #
def test_u5_sql_conversation_round_trip_and_uniqueness(repo: PostgresPlayRepository) -> None:
    from locus.play.errors import ConversationExistsError
    from locus.play.models import Conversation, Message

    s = repo.create_session("w")
    conv = repo.create_conversation(Conversation(session_id=s.id, npc_id="n1", started_turn=3))
    assert conv.started_turn == 3 and conv.created_at is not None
    with pytest.raises(ConversationExistsError):
        repo.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
    for i in range(3):
        repo.append_message(
            Message(conversation_id=conv.id, role="npc", text=f"m{i}", lang="en", turn=3)
        )
    got = repo.get_conversation(s.id, "n1")
    assert [m.text for m in got.messages] == ["m0", "m1", "m2"]
    assert all(m.lang == "en" and m.turn == 3 for m in got.messages)
    with pytest.raises(KeyError):
        repo.append_message(Message(conversation_id="nope", role="npc", text="x", lang="en"))
    assert [c.id for c in repo.list_conversations(s.id)] == [conv.id]


def test_u5_sql_unique_violation_maps_only_that_constraint(repo: PostgresPlayRepository) -> None:
    """The race window: two inserts for the same pair. Only this violation becomes
    ConversationExistsError; the pre-read is bypassed to reach the insert."""
    from locus.play.errors import ConversationExistsError
    from locus.play.models import Conversation
    from locus.play.storage import postgres_repo as pg

    s = repo.create_session("w")
    repo.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
    original = pg._PgStores._conversation_row
    calls = {"n": 0}

    def blind_first_read(self, session_id, npc_id):
        calls["n"] += 1
        return None if calls["n"] == 1 else original(self, session_id, npc_id)

    pg._PgStores._conversation_row = blind_first_read  # type: ignore[method-assign]
    try:
        with pytest.raises(ConversationExistsError):
            repo.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
    finally:
        pg._PgStores._conversation_row = original  # type: ignore[method-assign]


def test_u5_sql_rollback_discards_the_conversation(repo: PostgresPlayRepository) -> None:
    from locus.play.models import Conversation, Message

    s = repo.create_session("w")
    with pytest.raises(RuntimeError):
        with repo.uow() as u:
            conv = u.conversations.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
            u.conversations.append_message(
                Message(conversation_id=conv.id, role="player", text="hi", lang="ko")
            )
            raise RuntimeError("boom")
    assert repo.get_conversation(s.id, "n1") is None


def test_review_u6_4_a_u6_appraisal_table_gains_run_id_and_its_index() -> None:
    """Review U6 #4: `deed_appraisals.run_id` reaches a database made before the fix."""
    from sqlalchemy import inspect, text

    engine = create_engine("sqlite://", future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE deed_appraisals (id VARCHAR PRIMARY KEY, session_id VARCHAR NOT NULL,"
                " deed_id VARCHAR NOT NULL, npc_id VARCHAR NOT NULL, noteworthy BOOLEAN NOT NULL,"
                " salience FLOAT NOT NULL, slant TEXT NOT NULL, retelling TEXT NOT NULL,"
                " turn INTEGER NOT NULL, seeded_rumor_id VARCHAR, created_at DATETIME NOT NULL)"
            )
        )
    repo = PostgresPlayRepository(engine=engine)
    repo.ensure_schema()
    repo.ensure_schema()  # idempotent
    insp = inspect(engine)
    assert "run_id" in {c["name"] for c in insp.get_columns("deed_appraisals")}
    assert "ix_deed_appraisals_run_id" in {i["name"] for i in insp.get_indexes("deed_appraisals")}


def test_u6_ex15_an_old_schema_gains_the_new_columns_and_keeps_its_rows() -> None:
    """EX-15 / BR-U6-34: ensure_play_schema adds the missing columns on SQLite too (the
    inspector path), old rumors read back as canonical, and a second call is a no-op."""
    from sqlalchemy import inspect, text

    engine = create_engine("sqlite://", future=True)
    with engine.begin() as conn:  # the shape of a pre-U6 database
        conn.execute(
            text(
                "CREATE TABLE session_rumors (id VARCHAR PRIMARY KEY, session_id VARCHAR NOT NULL,"
                " region_id VARCHAR NOT NULL, distorted_from_id VARCHAR NOT NULL,"
                " distorted_from_kind VARCHAR NOT NULL, statement TEXT NOT NULL,"
                " distortion_degree FLOAT NOT NULL, support FLOAT NOT NULL, confidence FLOAT NOT NULL,"
                " promoted BOOLEAN NOT NULL, provenance JSON NOT NULL)"
            )
        )
        conn.execute(
            text(
                "CREATE TABLE turn_runs (id VARCHAR PRIMARY KEY, session_id VARCHAR NOT NULL,"
                " status VARCHAR NOT NULL, action JSON, cost_turns INTEGER NOT NULL,"
                " started_turn INTEGER NOT NULL, started_at DATETIME, finished_at DATETIME,"
                " result JSON, error TEXT)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO session_rumors VALUES ('r1','s1','a','k','knowledge','old',0.3,0.2,0.7,0,"
                '\'{"source": "simulation"}\')'
            )
        )
    repo = PostgresPlayRepository(engine=engine)
    repo.ensure_schema()
    repo.ensure_schema()  # idempotent
    cols = {c["name"] for c in inspect(engine).get_columns("session_rumors")}
    assert {
        "active",
        "origin_kind",
        "origin_deed_id",
        "origin_appraisal_id",
        "spread_from_region_id",
    } <= cols
    assert {"lang", "turns_charged", "from_region_id"} <= {
        c["name"] for c in inspect(engine).get_columns("turn_runs")
    }
    assert "ix_session_rumors_origin_deed_id" in {
        i["name"] for i in inspect(engine).get_indexes("session_rumors")
    }
    old = repo.get_rumor("s1", "r1")
    assert old.origin_kind == "canonical" and old.active is True
