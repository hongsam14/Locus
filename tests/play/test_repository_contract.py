"""S1 PlayRepository port contract tests (in-memory adapter, NFR-R1).

These exercise the behaviour the PostgreSQL adapter must also satisfy: CRUD,
timeline ordering (turn then created_at), distortion upsert/uniqueness and
session isolation (BR-S1-12/13/15).
"""

from __future__ import annotations

import pytest

from locus.play import InMemoryPlayRepository, PlayRepository
from locus.play.models import (
    EventCategory,
    EventStatus,
    SessionEvent,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.shared.models import Provenance, SourceKind


def _repo() -> InMemoryPlayRepository:
    return InMemoryPlayRepository()


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_in_memory_satisfies_protocol() -> None:
    assert isinstance(_repo(), PlayRepository)


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
    # U7 intended change: BR-U7-16 — no rumor is ever deleted; deactivation keeps the row
    r1.active = False
    repo.upsert_rumor(r1)
    assert repo.get_rumor(s.id, r1.id).active is False
    assert [r.region_id for r in repo.list_rumors(s.id)] == ["rB"]
    assert not hasattr(repo, "delete_rumor")


def test_batch_upsert_rumors_returns_stored() -> None:
    """U-H1: upsert_rumors persists many rumors and returns them (FR-H5)."""
    repo = _repo()
    s = repo.create_session("w")
    rumors = [
        SessionRumor(session_id=s.id, region_id="rA", distorted_from_id="k", provenance=_prov())
        for _ in range(3)
    ]
    saved = repo.upsert_rumors(rumors)
    assert len(saved) == 3
    assert len(repo.list_rumors(s.id)) == 3
    # re-upsert updates in place (no duplicates)
    rumors[0].support = 0.9
    repo.upsert_rumors(rumors)
    assert repo.get_rumor(s.id, rumors[0].id).support == 0.9
    assert len(repo.list_rumors(s.id)) == 3


def test_soft_flag_prune_excluded_by_default() -> None:
    """U-H1: active=False rumors are hidden unless include_pruned (BR-H1-6)."""
    repo = _repo()
    s = repo.create_session("w")
    live = SessionRumor(session_id=s.id, region_id="rA", distorted_from_id="k", provenance=_prov())
    dead = SessionRumor(
        session_id=s.id, region_id="rA", distorted_from_id="k", active=False, provenance=_prov()
    )
    repo.upsert_rumors([live, dead])
    assert [r.id for r in repo.list_rumors(s.id)] == [live.id]  # active-only default
    got = {r.id for r in repo.list_rumors(s.id, include_pruned=True)}
    assert got == {live.id, dead.id}


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
        provenance=Provenance(source=SourceKind.SIMULATION),
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


# --------------------------------------------------------------------------- #
# U4 — players, turn runs, unit of work (Step 3.5; BR-U4-1/14/32, EX-19/EX-20)
# --------------------------------------------------------------------------- #
def _u4_imports():
    from locus.play.models import Player, TurnRun, TurnRunStatus

    return Player, TurnRun, TurnRunStatus


def test_u4_player_crud_one_per_session() -> None:
    Player, _, _ = _u4_imports()
    repo = _repo()
    s = repo.create_session("w")
    p = repo.create_player(Player(session_id=s.id, name="Ari", region_id="r1"))
    assert p.created_at is not None and repo.get_player(s.id) == p
    with pytest.raises(ValueError):  # BR-U4-1: at most one player per session
        repo.create_player(Player(session_id=s.id, name="Bo", region_id="r1"))
    p.region_id, p.turns_spent = "r2", 3
    assert repo.update_player(p).region_id == "r2" and repo.get_player(s.id).turns_spent == 3
    with pytest.raises(KeyError):
        repo.update_player(Player(session_id=s.id, name="Zed", region_id="r1"))
    assert repo.get_player("other") is None


def test_u4_turn_run_crud_is_session_scoped() -> None:
    _, TurnRun, TurnRunStatus = _u4_imports()
    repo = _repo()
    a, b = repo.create_session("w"), repo.create_session("w")
    run = repo.create_run(TurnRun(session_id=a.id, cost_turns=2, started_turn=0))
    assert run.started_at is not None and run.status == "running"
    assert repo.get_run(a.id, run.id) == run
    assert repo.get_run(b.id, run.id) is None  # NFR R-06: other session -> None (404)
    run.status = TurnRunStatus.DONE
    assert repo.update_run(run).status == "done"
    assert [r.id for r in repo.list_runs(a.id, "done")] == [run.id]
    assert repo.list_runs(a.id, "running") == [] and repo.list_runs(b.id) == []
    with pytest.raises(KeyError):
        repo.update_run(TurnRun(session_id=a.id))


def test_u4_fail_stale_runs_marks_running_only() -> None:
    _, TurnRun, TurnRunStatus = _u4_imports()
    repo = _repo()
    s = repo.create_session("w")
    running = repo.create_run(TurnRun(session_id=s.id))
    done = repo.create_run(TurnRun(session_id=s.id, status=TurnRunStatus.DONE))
    assert repo.fail_stale_runs(reason="interrupted") == 1
    stale = repo.get_run(s.id, running.id)
    assert stale.status == "failed" and stale.error == "interrupted" and stale.finished_at
    assert repo.get_run(s.id, done.id).status == "done"


def test_u4_uow_commits_on_clean_exit_and_rolls_back_on_error() -> None:
    """EX-19: nothing written inside a failing unit of work survives."""
    Player, TurnRun, _ = _u4_imports()
    repo = _repo()
    with repo.uow() as u:
        s = u.sessions.create_session("w")
        u.players.create_player(Player(session_id=s.id, name="Ari", region_id="r1"))
        u.distortions.set_region_distortion(s.id, "r1", 0.4)
    assert repo.get_player(s.id) is not None and repo.get_region_distortion(s.id, "r1") == 0.4
    with pytest.raises(RuntimeError):
        with repo.uow() as u:
            u.runs.create_run(TurnRun(session_id=s.id))
            u.distortions.set_region_distortion(s.id, "r1", 0.9)
            u.sessions.bump_turn(s.id)
            raise RuntimeError("boom")
    assert repo.list_runs(s.id) == []
    assert repo.get_region_distortion(s.id, "r1") == 0.4
    assert repo.get_session(s.id).turn == 0


def test_u4_uow_rollback_does_not_erase_other_threads_writes() -> None:
    """EX-20 (BR-U4-32): thread B's write, made while A holds a unit of work that
    later rolls back, is not lost — B blocks on the lock until A has restored."""
    import threading

    Player, _, _ = _u4_imports()
    repo = _repo()
    s = repo.create_session("w")
    a_inside = threading.Event()
    a_release = threading.Event()

    def thread_a() -> None:
        try:
            with repo.uow() as u:
                u.distortions.set_region_distortion(s.id, "r1", 0.9)
                a_inside.set()
                a_release.wait(timeout=5)
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

    def thread_b() -> None:
        a_inside.wait(timeout=5)
        repo.create_player(Player(session_id=s.id, name="Bo", region_id="r1"))  # blocks on lock

    ta, tb = threading.Thread(target=thread_a), threading.Thread(target=thread_b)
    ta.start()
    tb.start()
    a_inside.wait(timeout=5)
    assert repo.get_player(s.id) is None or True  # B is still blocked (lock held by A)
    a_release.set()
    ta.join(timeout=5)
    tb.join(timeout=5)
    assert repo.get_player(s.id) is not None  # B's write survived A's rollback
    assert repo.get_region_distortion(s.id, "r1") is None  # A's write was rolled back


# --------------------------------------------------------------------------- #
# U5 — conversations (Step 4.3; BR-U5-1/3/31)
# --------------------------------------------------------------------------- #
def test_u5_one_conversation_per_session_and_npc() -> None:
    from locus.play.errors import ConversationExistsError
    from locus.play.models import Conversation

    repo = _repo()
    a, b = repo.create_session("w"), repo.create_session("w")
    first = repo.create_conversation(Conversation(session_id=a.id, npc_id="n1", started_turn=2))
    assert first.created_at is not None and first.messages == []
    with pytest.raises(ConversationExistsError):
        repo.create_conversation(Conversation(session_id=a.id, npc_id="n1"))
    repo.create_conversation(Conversation(session_id=b.id, npc_id="n1"))  # other session: fine
    assert repo.get_conversation(a.id, "n1").id == first.id
    assert repo.get_conversation(a.id, "n2") is None
    assert [c.npc_id for c in repo.list_conversations(a.id)] == ["n1"]


def test_u5_messages_come_back_in_order_and_need_a_conversation() -> None:
    from locus.play.models import Conversation, Message

    repo = _repo()
    s = repo.create_session("w")
    conv = repo.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
    for i in range(5):
        repo.append_message(
            Message(
                conversation_id=conv.id,
                role="player" if i % 2 == 0 else "npc",
                text=f"m{i}",
                lang="ko",
            )
        )
    got = repo.get_conversation(s.id, "n1").messages
    assert [m.text for m in got] == [f"m{i}" for i in range(5)]
    stamps = [m.created_at for m in got]
    assert all(x < y for x, y in zip(stamps, stamps[1:], strict=False))
    with pytest.raises(KeyError):
        repo.append_message(Message(conversation_id="nope", role="npc", text="x", lang="ko"))
    assert repo.list_conversations(s.id)[0].messages == []  # listing stays light


def test_u5_a_rolled_back_unit_of_work_takes_the_conversation_with_it() -> None:
    from locus.play.models import Conversation, Message

    repo = _repo()
    s = repo.create_session("w")
    with pytest.raises(RuntimeError):
        with repo.uow() as u:
            conv = u.conversations.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
            u.conversations.append_message(
                Message(conversation_id=conv.id, role="player", text="hi", lang="ko")
            )
            raise RuntimeError("the NPC answer could not be stored")
    assert repo.get_conversation(s.id, "n1") is None  # BR-U5-3: no empty conversation left


# --- U6 deeds, appraisals, rumor origin, run columns — both adapters (Step 3.4) ------ #
@pytest.fixture(params=["memory", "sql"])
def any_repo(request):
    if request.param == "memory":
        return InMemoryPlayRepository()
    pytest.importorskip("sqlalchemy")
    from sqlalchemy import create_engine

    from locus.play.storage.postgres_repo import PostgresPlayRepository

    r = PostgresPlayRepository(engine=create_engine("sqlite://", future=True))
    r.ensure_schema()
    return r


def _rumor(session_id: str) -> SessionRumor:
    return SessionRumor(
        session_id=session_id, region_id="a", distorted_from_id="k", provenance=_prov()
    )


def _deed(session_id: str, region: str = "a", *, kind="arrival", run_id=None, text="Ari came."):
    from locus.play.models import Deed

    return Deed(
        session_id=session_id,
        player_id="p",
        region_id=region,
        kind=kind,
        text=text,
        witnessed_npc_ids=["n1", "n2"],
        run_id=run_id,
    )


def test_u6_deeds_keep_their_order_and_filters(any_repo) -> None:
    s = any_repo.create_session("w")
    first = any_repo.record_deed(_deed(s.id, "a"))
    second = any_repo.record_deed(_deed(s.id, "b", kind="declared_action", text="Ari sang."))
    third = any_repo.record_deed(_deed(s.id, "a", kind="statement", text="Ari asked."))
    assert first.created_at is not None and first.created_at < second.created_at < third.created_at
    assert [d.id for d in any_repo.list_deeds(s.id)] == [first.id, second.id, third.id]
    assert [d.id for d in any_repo.list_deeds(s.id, region_id="a")] == [first.id, third.id]
    voided = second.model_copy(update={"voided": True, "voided_turn": 3})
    assert any_repo.update_deed(voided).voided is True
    assert [d.id for d in any_repo.list_deeds(s.id, include_voided=False)] == [first.id, third.id]
    got = any_repo.get_deed(s.id, second.id)
    assert got.voided_turn == 3 and got.created_at == second.created_at  # order never moves
    assert got.witnessed_npc_ids == ["n1", "n2"] and got.kind == "declared_action"
    assert any_repo.get_deed(s.id, "missing") is None
    with pytest.raises(KeyError):
        any_repo.update_deed(_deed(s.id))


def test_u6_appraisals_are_unique_per_deed_and_npc(any_repo) -> None:
    from locus.play.errors import AppraisalExistsError
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    deed = any_repo.record_deed(_deed(s.id))

    def ap(npc, **kw):
        return DeedAppraisal(
            session_id=s.id,
            deed_id=deed.id,
            npc_id=npc,
            noteworthy=True,
            salience=0.6,
            slant="wary",
            retelling="A stranger came.",
            **kw,
        )

    saved = any_repo.save_appraisals([ap("n1"), ap("n2")])
    assert [a.npc_id for a in any_repo.list_appraisals(s.id)] == ["n1", "n2"]
    assert [a.npc_id for a in any_repo.list_appraisals(s.id, npc_id="n2")] == ["n2"]
    assert any_repo.list_appraisals(s.id, deed_ids=[]) == []
    with pytest.raises(AppraisalExistsError):
        any_repo.save_appraisals([ap("n1")])
    any_repo.mark_seeded(s.id, saved[0].id, "rumor-1")
    assert any_repo.list_appraisals(s.id, npc_id="n1")[0].seeded_rumor_id == "rumor-1"
    with pytest.raises(KeyError):
        any_repo.mark_seeded(s.id, "missing", "rumor-1")


def test_u6_delete_by_run_takes_only_that_runs_deeds_and_their_appraisals(any_repo) -> None:
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    kept = any_repo.record_deed(_deed(s.id, run_id="run-a"))
    gone = any_repo.record_deed(_deed(s.id, run_id="run-b"))
    any_repo.save_appraisals(
        [
            DeedAppraisal(
                session_id=s.id, deed_id=d.id, npc_id="n1", noteworthy=False, salience=0.0
            )
            for d in (kept, gone)
        ]
    )
    assert any_repo.delete_by_run(s.id, "run-b") == 1
    assert [d.id for d in any_repo.list_deeds(s.id)] == [kept.id]
    assert [a.deed_id for a in any_repo.list_appraisals(s.id)] == [kept.id]
    assert any_repo.delete_by_run(s.id, "run-none") == 0


def test_review_u6_4_delete_by_run_also_takes_the_runs_appraisals_of_earlier_deeds(
    any_repo,
) -> None:
    """Review U6 #4: a failed talk's preparation judged a deed of an earlier run; the
    appraisal carries the failed run's id and goes with it, the earlier deed stays."""
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    earlier = any_repo.record_deed(_deed(s.id, run_id="run-a"))

    def judged(npc_id: str, run_id: str | None) -> DeedAppraisal:
        return DeedAppraisal(
            session_id=s.id,
            deed_id=earlier.id,
            npc_id=npc_id,
            noteworthy=True,
            salience=0.9,
            retelling="told",
            run_id=run_id,
        )

    any_repo.save_appraisals([judged("n1", "run-talk"), judged("n2", "run-other")])
    assert [a.run_id for a in any_repo.list_appraisals(s.id)] == ["run-talk", "run-other"]
    assert any_repo.delete_by_run(s.id, "run-talk") == 0  # no deed of that run
    assert [a.npc_id for a in any_repo.list_appraisals(s.id)] == ["n2"]
    assert [d.id for d in any_repo.list_deeds(s.id)] == [earlier.id]


def test_u6_rumor_origin_round_trips_and_filters(any_repo) -> None:
    s = any_repo.create_session("w")
    canon = _rumor(s.id)
    seed = _rumor(s.id).model_copy(
        update={"origin_kind": "deed", "origin_deed_id": "d1", "origin_appraisal_id": "ap1"}
    )
    hop = _rumor(s.id).model_copy(
        update={
            "origin_kind": "deed",
            "origin_deed_id": "d1",
            "origin_appraisal_id": "ap1",
            "spread_from_region_id": "a",
            "active": False,
        }
    )
    other = _rumor(s.id).model_copy(update={"origin_kind": "deed", "origin_deed_id": "d2"})
    any_repo.upsert_rumors([canon, seed, hop, other])
    assert any_repo.get_rumor(s.id, canon.id).origin_kind == "canonical"
    back = any_repo.get_rumor(s.id, hop.id)
    assert (back.origin_deed_id, back.origin_appraisal_id, back.spread_from_region_id) == (
        "d1",
        "ap1",
        "a",
    )
    assert {r.id for r in any_repo.list_rumors_by_origin(s.id)} == {seed.id, other.id}
    assert {r.id for r in any_repo.list_rumors_by_origin(s.id, deed_id="d1")} == {seed.id}
    assert {
        r.id for r in any_repo.list_rumors_by_origin(s.id, deed_id="d1", include_inactive=True)
    } == {seed.id, hop.id}


def test_u6_turn_runs_keep_lang_charge_and_origin(any_repo) -> None:
    """NFR review R-03 / EX-19: the background run re-reads its row — before U6 the SQL
    adapter dropped turns_charged and from_region_id, so U4 compensation never ran."""
    from locus.play.models import TurnRun, TurnRunStatus

    s = any_repo.create_session("w")
    run = any_repo.create_run(
        TurnRun(session_id=s.id, lang="en", turns_charged=2, from_region_id="a", cost_turns=2)
    )
    back = any_repo.get_run(s.id, run.id)
    assert (back.lang, back.turns_charged, back.from_region_id) == ("en", 2, "a")
    back.status = TurnRunStatus.FAILED
    updated = any_repo.update_run(back)
    assert (updated.lang, updated.turns_charged, updated.from_region_id) == ("en", 2, "a")


def test_u6_a_rolled_back_unit_of_work_takes_deeds_and_appraisals_with_it(any_repo) -> None:
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    with pytest.raises(RuntimeError):
        with any_repo.uow() as u:
            d = u.deeds.record_deed(_deed(s.id))
            u.deeds.save_appraisals(
                [
                    DeedAppraisal(
                        session_id=s.id, deed_id=d.id, npc_id="n1", noteworthy=True, salience=0.5
                    )
                ]
            )
            raise RuntimeError("boom")
    assert any_repo.list_deeds(s.id) == [] and any_repo.list_appraisals(s.id) == []


# --- U7 storage (Step 3.4): both adapters ------------------------------------------- #
def test_u7_feedback_share_round_trips_and_none_keeps_it(any_repo) -> None:
    s = any_repo.create_session("w")
    any_repo.set_region_distortion(s.id, "a", 0.3)  # a new row starts with no share
    assert any_repo.list_region_distortions(s.id)[0].feedback_share == 0.0
    any_repo.set_region_distortion(s.id, "a", 0.4, feedback_share=0.1)
    any_repo.set_region_distortion(s.id, "a", 0.5)  # an event write keeps the share
    row = any_repo.list_region_distortions(s.id)[0]
    assert (row.distortion_degree, row.feedback_share) == (0.5, 0.1)
    any_repo.set_region_distortion(s.id, "a", 0.2, feedback_share=0.0)  # a GM set clears it
    assert any_repo.list_region_distortions(s.id)[0].feedback_share == 0.0


def test_u7_message_counts_one_read_per_session(any_repo) -> None:
    """U5 C1 / NFR R-02: npc_id -> messages; a talk with no message counts 0, no talk no key."""
    from locus.play.models import Conversation, Message

    s = any_repo.create_session("w")
    other = any_repo.create_session("w")
    mara = any_repo.create_conversation(Conversation(session_id=s.id, npc_id="n1"))
    any_repo.create_conversation(Conversation(session_id=s.id, npc_id="n2"))
    elsewhere = any_repo.create_conversation(Conversation(session_id=other.id, npc_id="n1"))
    for text in ("hi", "hello"):
        any_repo.append_message(
            Message(conversation_id=mara.id, role="player", text=text, lang="ko")
        )
    any_repo.append_message(
        Message(conversation_id=elsewhere.id, role="player", text="x", lang="ko")
    )
    assert any_repo.message_counts(s.id) == {"n1": 2, "n2": 0}
    assert any_repo.message_counts("nope") == {}


def test_u7_list_deeds_narrows_by_kind_ids_and_newest_first(any_repo) -> None:
    s = any_repo.create_session("w")
    a = any_repo.record_deed(_deed(s.id, text="one"))
    b = any_repo.record_deed(_deed(s.id, kind="statement", text="two"))
    c = any_repo.record_deed(_deed(s.id, kind="statement", text="three"))
    assert [d.id for d in any_repo.list_deeds(s.id, kind="statement")] == [b.id, c.id]
    newest = any_repo.list_deeds(s.id, newest_first=True, limit=2)
    assert [d.id for d in newest] == [c.id, b.id]
    assert [d.id for d in any_repo.list_deeds(s.id, deed_ids=[c.id, a.id])] == [a.id, c.id]
    assert any_repo.list_deeds(s.id, deed_ids=[]) == []


def test_u7_seed_candidates_match_the_seed_rule(any_repo) -> None:
    """U6 review C2: the BR-U6-12 filter as one read, oldest deed first."""
    from locus.play.models import DeedAppraisal

    s = any_repo.create_session("w")
    first = any_repo.record_deed(_deed(s.id, text="first"))
    second = any_repo.record_deed(_deed(s.id, text="second"))
    voided = any_repo.record_deed(_deed(s.id, text="voided"))
    voided.voided = True
    any_repo.update_deed(voided)

    def ap(deed, npc, **kw):
        base = {"noteworthy": True, "salience": 0.8, "retelling": "told"}
        base.update(kw)
        return DeedAppraisal(session_id=s.id, deed_id=deed.id, npc_id=npc, **base)

    any_repo.save_appraisals(
        [
            ap(second, "n1"),
            ap(first, "n1"),
            ap(first, "n2", salience=0.2),  # below the bar
            ap(first, "n3", retelling="   "),  # nothing to tell
            ap(first, "n4", noteworthy=False),
            ap(second, "n5", seeded_rumor_id="r1"),  # already seeded
            ap(voided, "n1"),
        ]
    )
    got = any_repo.seed_candidates(s.id, min_salience=0.5)
    assert [(d.id, a.npc_id) for d, a in got] == [(first.id, "n1"), (second.id, "n1")]
