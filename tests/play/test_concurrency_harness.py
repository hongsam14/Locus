"""V5 Step 3.3 — the overlap harness itself: the gate gathers two threads and lets one
alone go after its wait; the failing timeline rolls a row back with its line; the
blocking fake LLM holds drafts and counts them (NFR § 2)."""

from __future__ import annotations

import threading
import time

import pytest

from locus.play import InMemoryPlayRepository, PlayRepository
from locus.play.models import TimelineEntry, TimelineKind
from locus.play.rumor.generator import RumorDraft
from tests.play.concurrency import BlockingDrafts, FailingTimeline, InterleaveGate

WAIT = 0.3


def _both(fn) -> list[float]:
    """Run ``fn`` in two threads that start together; their elapsed seconds."""
    start = threading.Barrier(2)
    took: list[float] = []
    lock = threading.Lock()

    def run() -> None:
        start.wait()
        began = time.monotonic()
        fn()
        with lock:
            took.append(time.monotonic() - began)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    return took


def test_the_gate_gathers_two_threads(threaded_repo) -> None:
    sid = threaded_repo.create_session("w").id
    with InterleaveGate(threaded_repo, "get_session", wait_s=2.0) as gate:
        took = _both(lambda: threaded_repo.get_session(sid))
    assert gate.met and gate.arrivals == 2
    assert len(took) == 2 and max(took) < 1.5  # released together, not by the timeout


def test_one_thread_alone_goes_on_after_the_wait(threaded_repo) -> None:
    sid = threaded_repo.create_session("w").id
    with InterleaveGate(threaded_repo, "get_session", wait_s=WAIT) as gate:
        began = time.monotonic()
        assert threaded_repo.get_session(sid).id == sid  # the result passes through
        alone = time.monotonic() - began
        began = time.monotonic()
        threaded_repo.get_session(sid)  # a thread pauses on its first call only
        again = time.monotonic() - began
    assert not gate.met and gate.arrivals == 1
    assert alone >= WAIT * 0.9 and again < WAIT * 0.5


def test_the_gate_sees_reads_through_a_unit_of_work(threaded_repo) -> None:
    """SQL: a read inside the unit of work pauses. Memory: never inside the block, which
    holds the repository lock (NFR R-05)."""
    sid = threaded_repo.create_session("w").id
    memory = isinstance(threaded_repo, InMemoryPlayRepository)
    with InterleaveGate(threaded_repo, "get_session", wait_s=WAIT) as gate:
        began = time.monotonic()
        with threaded_repo.uow() as u:
            assert u.sessions.get_session(sid).id == sid
        took = time.monotonic() - began
    if memory:
        assert gate.arrivals == 0 and took < WAIT * 0.5
    else:
        assert gate.arrivals == 1 and took >= WAIT * 0.9


def test_closing_the_gate_restores_the_repository(threaded_repo) -> None:
    gate = InterleaveGate(threaded_repo, "get_session", wait_s=WAIT)
    with pytest.raises(RuntimeError):  # one patch at a time
        InterleaveGate(threaded_repo, "list_sessions")
    gate.close()
    assert "get_session" not in vars(threaded_repo) and "uow" not in vars(threaded_repo)
    assert isinstance(threaded_repo, PlayRepository)
    sid = threaded_repo.create_session("w").id
    began = time.monotonic()
    threaded_repo.get_session(sid)
    assert time.monotonic() - began < WAIT * 0.5 and gate.arrivals == 0


def test_a_failing_timeline_rolls_back_the_row_written_with_it(threaded_repo) -> None:
    sid = threaded_repo.create_session("w").id
    line = TimelineEntry(session_id=sid, turn=0, kind=TimelineKind.SESSION_CLOSED, summary="x")
    with FailingTimeline(threaded_repo, kinds=[TimelineKind.SESSION_CLOSED]) as failing:
        with pytest.raises(RuntimeError, match="timeline write failed"):
            with threaded_repo.uow() as u:
                u.sessions.close_session(sid)
                u.timeline.append_timeline(line)
        with pytest.raises(RuntimeError):  # outside a unit of work too
            threaded_repo.append_timeline(line)
        other = line.model_copy(update={"kind": TimelineKind.ADVANCE_TURN})
        threaded_repo.append_timeline(other)  # another kind passes
    assert failing.raised == 2
    assert threaded_repo.get_session(sid).status == "open"  # rolled back with the line
    assert [e.kind for e in threaded_repo.list_timeline(sid)] == [TimelineKind.ADVANCE_TURN]
    assert "append_timeline" not in vars(threaded_repo)


def test_blocking_drafts_hold_until_released_and_count_the_overlap() -> None:
    llm = BlockingDrafts()
    out: list[RumorDraft] = []
    threads = [
        threading.Thread(target=lambda: out.append(llm.structured("p", RumorDraft)))
        for _ in range(3)
    ]
    for t in threads:
        t.start()
    assert llm.wait_entered(3)
    assert out == []  # all three are held
    llm.release()
    for t in threads:
        t.join(timeout=5)
    assert [d.statement for d in out] == ["twisted"] * 3
    assert llm.calls == 3 and llm.max_inside == 3 and llm.inside == 0
    lone = BlockingDrafts(blocked=False)
    lone.structured("p", RumorDraft)
    assert lone.max_inside == 1
