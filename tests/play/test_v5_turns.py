"""V5 — turns: runs a restart cut are compensated (TP-V5-5, BR-V5-18/19, code plan § 1.1
R-01) and an event whose region left the world ends (TP-V5-6, BR-V5-20/21)."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from locus.play import InMemoryPlayRepository
from locus.play.models import (
    EventCategory,
    EventLifecycle,
    EventStatus,
    MoveAction,
    Player,
    SessionEvent,
    TimelineKind,
)
from locus.play.turn.advancer import RUN_UNCOMPENSATED
from locus.play.wiring import PlayContainer
from locus.shared.models import Provenance, SourceKind
from tests.play.helpers import compose_play
from tests.play.strategies import WORLD, build_snapshot, edge
from tests.play.test_player_mode import CountingGenerator, _play_world
from tests.shared.snapshots import StaticSnapshots


class _HeldExecutor:
    """Takes the run and never runs it: the process stopped before the turns ran."""

    def __init__(self) -> None:
        self.jobs: list[tuple[Any, ...]] = []

    def submit(self, fn, *args) -> None:
        self.jobs.append((fn, *args))

    def shutdown(self, timeout: float) -> None:
        return None


def _container(repo=None) -> tuple[Any, PlayContainer]:
    repo = repo or InMemoryPlayRepository()
    gm = compose_play(
        repo, CountingGenerator(), StaticSnapshots(_play_world()), executor=_HeldExecutor()
    )
    return repo, gm


def _cut_move(repo, gm: PlayContainer, *, advanced: int = 0) -> tuple[str, str]:
    """A player moved a → b (2 turns) whose run a restart cut after ``advanced`` turns."""
    session = repo.create_session("w")
    for rid in ("a", "b", "c"):
        repo.set_region_distortion(session.id, rid, 0.3)
    repo.create_player(Player(session_id=session.id, name="Ari", region_id="a"))
    run = gm.turns.begin(session.id, MoveAction(to_region_id="b"))
    for _ in range(advanced):
        repo.bump_turn(session.id)  # a turn of the run that did commit
    gm.guard.release(session.id)  # a new process: the guard starts empty
    return session.id, run.id


def _failed_lines(repo, sid: str) -> list:
    return [e for e in repo.list_timeline(sid) if e.kind == TimelineKind.TURN_RUN_FAILED.value]


# --- TP-V5-5 (RE-P03) ------------------------------------------------------------ #
def test_tp_v5_5_cut_runs_are_compensated_like_failed_ones() -> None:
    repo, gm = _container()
    still, still_run = _cut_move(repo, gm, advanced=0)
    half, half_run = _cut_move(repo, gm, advanced=1)
    moved = repo.get_player(still)
    assert moved.region_id == "b" and moved.turns_spent == 2
    assert repo.list_deeds(still)  # the arrival in b was recorded at the start

    assert sorted(gm.turns.recover_interrupted()) == sorted([still_run, half_run])

    # (a) no turn ran: back in a, the charge refunded, the arrival undone
    player = repo.get_player(still)
    assert player.region_id == "a" and player.turns_spent == 0
    assert repo.list_deeds(still) == []
    (line,) = _failed_lines(repo, still)
    assert line.payload["error_type"] == "Interrupted"
    assert line.payload["turns_advanced"] == 0 and line.payload["turns_refunded"] == 2
    assert line.payload["restored_region_id"] == "a"
    # (b) one of two turns ran: charged one, still in b
    player = repo.get_player(half)
    assert player.region_id == "b" and player.turns_spent == 1
    (line,) = _failed_lines(repo, half)
    assert line.payload["turns_advanced"] == 1 and line.payload["turns_refunded"] == 1
    for sid, rid in ((still, still_run), (half, half_run)):
        run = repo.get_run(sid, rid)
        assert run.status == "failed" and run.error == "interrupted" and run.finished_at
    assert repo.list_running_runs() == []
    assert gm.turns.recover_interrupted() == []  # nothing is compensated twice


def test_tp_v5_5_a_run_whose_compensation_fails_is_marked_and_the_others_go_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    repo, gm = _container()
    bad, bad_run = _cut_move(repo, gm)
    good, good_run = _cut_move(repo, gm)
    real = gm.turns._compensate

    def compensate(run, **kw):
        if run.id == bad_run:
            raise RuntimeError("player row locked")
        return real(run, **kw)

    gm.turns._compensate = compensate  # type: ignore[method-assign]
    with caplog.at_level(logging.ERROR, logger="locus.play.turn.advancer"):
        assert gm.turns.recover_interrupted() == [good_run]
    assert any(bad_run in r.getMessage() and bad in r.getMessage() for r in caplog.records)
    run = repo.get_run(bad, bad_run)
    assert run.status == "failed" and run.error == RUN_UNCOMPENSATED
    assert repo.get_player(bad).region_id == "b"  # left for an operator to check
    assert repo.get_player(good).region_id == "a"  # the other one was compensated
    gm.turns._compensate = real  # type: ignore[method-assign]
    assert gm.turns.recover_interrupted() == []  # the marked run is not touched again


def test_tp_v5_5_when_even_the_mark_fails_the_run_stays_for_the_next_start() -> None:
    repo, gm = _container()
    sid, rid = _cut_move(repo, gm)
    real = repo.update_run

    def down(run):
        raise ConnectionError("storage down")

    repo.update_run = down  # every write of the run fails
    assert gm.turns.recover_interrupted() == []
    del repo.update_run  # storage is back
    assert repo.update_run == real
    assert repo.get_run(sid, rid).status == "running"
    assert gm.turns.recover_interrupted() == [rid]  # the next start compensates it
    assert repo.get_player(sid).region_id == "a"


def test_tp_v5_5_the_api_start_compensates_before_any_request() -> None:
    repo, gm = _container()
    sid, rid = _cut_move(repo, gm)
    with TestClient(create_app(play=gm)) as client:  # lifespan start
        run = client.get(f"/api/play/sessions/{sid}/turn-runs/{rid}").json()
    assert run["status"] == "failed" and run["error"] == "interrupted"
    assert repo.get_player(sid).region_id == "a"


# --- TP-V5-6 (RE-P04, Q1=A) -------------------------------------------------------- #
def _two_region_world(*regions: str):
    edges = [edge("x", "y"), edge("y", "x")] if {"x", "y"} <= set(regions) else []
    return build_snapshot(list(regions), edges)


def _war(sid: str, region: str, contributions: dict[str, float] | None = None) -> SessionEvent:
    return SessionEvent(
        session_id=sid,
        region_id=region,
        category=EventCategory.WAR,
        magnitude=0.6,
        lifecycle=EventLifecycle.PERSISTENT,  # the model's default is one_shot
        status=EventStatus.ACTIVE,
        created_turn=0,
        contributions=contributions or {},
        provenance=Provenance(source=SourceKind.SIMULATION, generated_by="gm:event"),
    )


def _resolved_lines(repo, sid: str) -> list:
    return [e for e in repo.list_timeline(sid) if e.kind == TimelineKind.EVENT_RESOLVED.value]


def test_tp_v5_6_an_event_whose_region_is_gone_ends_on_the_next_turn() -> None:
    repo = InMemoryPlayRepository()
    snapshots = StaticSnapshots(_two_region_world("x", "y"))
    gm = compose_play(repo, CountingGenerator(), snapshots, executor=_HeldExecutor())
    sid = repo.create_session(WORLD).id
    repo.set_region_distortion(sid, "x", 0.3)
    repo.set_region_distortion(sid, "y", 0.3)
    event = repo.create_event(_war(sid, "x"))
    gm.turns.advance(sid)  # it builds up on x and on its neighbour y
    built = repo.get_event(sid, event.id).contributions
    assert built.get("x", 0) > 0 and built.get("y", 0) > 0
    x_before = repo.get_region_distortion(sid, "x")

    snapshots.snapshot = _two_region_world("y")  # the editor deleted x
    result = gm.turns.advance(sid).turns[-1]
    assert result.resolved_event_ids == [event.id] and result.applied_event_ids == []
    ended = repo.get_event(sid, event.id)
    assert EventStatus(ended.status) is EventStatus.RESOLVED and ended.resolved_turn == 2
    assert repo.get_region_distortion(sid, "y") == pytest.approx(0.3)  # y restored
    assert repo.get_region_distortion(sid, "x") == x_before  # x's row not written
    (line,) = _resolved_lines(repo, sid)
    assert line.payload["reason"] == "region_removed"
    assert line.payload["restored"] == {"y": built["y"]} and line.payload["region_id"] == "x"
    assert all(c.region_id != "x" for c in result.region_changes)  # no player-facing line

    gm.turns.advance(sid)
    assert len(_resolved_lines(repo, sid)) == 1  # not resolved again


def test_tp_v5_6_a_gm_resolve_makes_no_row_for_a_region_the_world_lost() -> None:
    repo = InMemoryPlayRepository()
    gm = compose_play(
        repo, CountingGenerator(), StaticSnapshots(_two_region_world("y")), executor=_HeldExecutor()
    )
    sid = repo.create_session(WORLD).id
    repo.set_region_distortion(sid, "y", 0.45)
    event = repo.create_event(_war(sid, "x", {"x": 0.2, "y": 0.15}))
    gm.events.resolve_event(sid, event.id)
    assert repo.get_region_distortion(sid, "y") == pytest.approx(0.3)
    assert repo.get_region_distortion(sid, "x") is None  # BR-V5-21: no row made
    (line,) = _resolved_lines(repo, sid)
    assert line.payload["restored"] == {"y": 0.15} and "reason" not in line.payload
