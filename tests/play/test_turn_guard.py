"""TurnGuard — U4 TP-U4-6 concurrency + executor behaviour (Step 4.6); V5 the lease,
closing and short-write states (FD domain-entities § 1, BR-V5-01..04, 14..16, 22..25)."""

from __future__ import annotations

import threading
import time

import pytest

from locus.play.base import SessionClosedError
from locus.play.errors import GmBusyError, TurnInProgressError
from locus.play.turn.executor import SyncTurnExecutor, ThreadTurnExecutor
from locus.play.turn.guard import TurnGuard


def test_tp_u4_6_exactly_one_of_n_concurrent_acquires_wins() -> None:
    guard = TurnGuard()
    start = threading.Barrier(8)
    outcomes: list[bool] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        start.wait()
        try:
            guard.acquire("s", f"run{i}")
            ok = True
        except TurnInProgressError:
            ok = False
        with lock:
            outcomes.append(ok)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert outcomes.count(True) == 1 and len(outcomes) == 8
    assert guard.turn_running("s") and not guard.gm_busy("s")
    with pytest.raises(TurnInProgressError):
        with guard.closing("s"):  # a close is refused mid-turn (BR-U4-5)
            pass
    guard.release("s")
    assert not guard.turn_running("s")
    with guard.closing("s"):  # idle now
        pass


def test_guard_is_per_session() -> None:
    guard = TurnGuard()
    guard.acquire("a", "r1")
    guard.acquire("b", "r2")  # another session is not blocked
    with pytest.raises(TurnInProgressError):
        guard.acquire("a", "r3")
    guard.release("a")
    guard.release("missing")  # idempotent


def test_sync_executor_runs_inline() -> None:
    seen: list[int] = []
    ex = SyncTurnExecutor()
    ex.submit(seen.append, 1)
    assert seen == [1]
    ex.shutdown(1.0)


def test_thread_executor_runs_serially_and_shuts_down() -> None:
    ex = ThreadTurnExecutor(name="turn-test")
    order: list[int] = []
    done = threading.Event()

    def slow(i: int) -> None:
        time.sleep(0.01)
        order.append(i)
        if i == 3:
            done.set()

    for i in range(1, 4):
        ex.submit(slow, i)
    assert done.wait(timeout=5)
    assert order == [1, 2, 3]  # FIFO on one worker
    ex.shutdown(timeout=2.0)
    with pytest.raises(RuntimeError):
        ex.submit(slow, 4)  # closed
    ex.shutdown(timeout=0.1)  # idempotent


def test_thread_executor_survives_a_raising_task() -> None:
    ex = ThreadTurnExecutor()
    ran = threading.Event()

    def boom() -> None:
        raise RuntimeError("x")

    ex.submit(boom)
    ex.submit(ran.set)
    assert ran.wait(timeout=5)
    ex.shutdown(timeout=2.0)


def test_u7_review_2_gm_writes_share_the_session_and_only_turns_exclude() -> None:
    """Five GM writes at once (a bulk generate) all hold; a turn waits for none of them
    to start but is refused while any is running; a GM write is refused during a turn."""
    guard = TurnGuard()
    holds = [guard.hold("s") for _ in range(5)]
    for h in holds:
        h.__enter__()
    assert guard.gm_busy("s") and not guard.turn_running("s")  # V5 BR-V5-22
    with pytest.raises(GmBusyError):
        guard.acquire("s", "run-1")
    for h in holds[:4]:
        h.__exit__(None, None, None)
    assert guard.gm_busy("s")  # a count: the last lease clears it
    with pytest.raises(GmBusyError):  # one GM write is still in progress
        guard.acquire("s", "run-1")
    holds[4].__exit__(None, None, None)
    assert not guard.gm_busy("s")
    guard.acquire("s", "run-1")
    try:
        with pytest.raises(TurnInProgressError):
            with guard.hold("s"):
                pass
    finally:
        guard.release("s")
    assert not guard.turn_running("s")


# --- V5 ----------------------------------------------------------------------- #
def _no_internals(err: BaseException, *needles: str) -> None:
    """V5 FR-C5: a 409 sentence names no session id, run id or lease token."""
    text = str(err)
    for needle in needles:
        assert needle not in text
    assert "gm:" not in text and "editor:" not in text


def test_v5_turn_refusals_say_which_and_carry_no_internals() -> None:
    guard = TurnGuard()
    guard.acquire("sess-1", "run-xyz")
    with pytest.raises(TurnInProgressError) as turn:
        guard.acquire("sess-1", "run-2")
    assert type(turn.value) is TurnInProgressError
    _no_internals(turn.value, "sess-1", "run-xyz", "run-2")
    with pytest.raises(TurnInProgressError) as lease:
        with guard.hold("sess-1"):
            pass
    _no_internals(lease.value, "sess-1", "run-xyz")
    guard.release("sess-1")
    with guard.hold("sess-1", label="editor"):
        with pytest.raises(GmBusyError) as busy:
            guard.acquire("sess-1", "run-3")
    _no_internals(busy.value, "sess-1", "run-3")
    with guard.closing("sess-1"):
        with pytest.raises(SessionClosedError) as closing:
            guard.acquire("sess-1", "run-4")
    _no_internals(closing.value, "sess-1", "run-4")


def test_v5_closing_keeps_turns_out_but_not_leases_and_is_counted() -> None:
    """BR-V5-14/16: a close keeps new turns out, lets a GM lease in (its save will find
    the session closed), and of two overlapping closes the first to end lifts nothing."""
    guard = TurnGuard()
    first = guard.closing("s")
    second = guard.closing("s")
    first.__enter__()
    second.__enter__()
    with guard.hold("s"):  # a lease is not refused by a close
        assert guard.gm_busy("s")
    first.__exit__(None, None, None)
    with pytest.raises(SessionClosedError):  # the other close still holds
        guard.acquire("s", "run-1")
    second.__exit__(None, None, None)
    guard.acquire("s", "run-1")
    guard.release("s")
    with pytest.raises(RuntimeError):  # released even when the body raises
        with guard.closing("s"):
            raise RuntimeError("boom")
    guard.acquire("s", "run-2")
    guard.release("s")


def test_v5_a_lease_does_not_wait_for_a_close_and_a_close_does_not_wait_for_a_lease() -> None:
    guard = TurnGuard()
    with guard.hold("s"):
        with guard.closing("s"):  # leases are not waited for (BR-V5-15)
            with guard.short_write("s", timeout_s=0.1):
                pass


def test_v5_short_write_runs_one_section_at_a_time_per_session() -> None:
    """BR-V5-01: a second writer waits for the first section, then reads what it wrote."""
    guard = TurnGuard()
    inside = threading.Event()
    release = threading.Event()
    order: list[str] = []

    def first() -> None:
        with guard.short_write("s", timeout_s=5):
            order.append("first-in")
            inside.set()
            release.wait(5)
            order.append("first-out")

    def second() -> None:
        inside.wait(5)
        with guard.short_write("s", timeout_s=5):
            order.append("second-in")

    a = threading.Thread(target=first)
    b = threading.Thread(target=second)
    a.start()
    b.start()
    assert inside.wait(5)
    time.sleep(0.05)  # the second is now waiting on the section
    assert order == ["first-in"]
    release.set()
    a.join(5)
    b.join(5)
    assert order == ["first-in", "first-out", "second-in"]


def test_v5_short_write_gives_up_after_the_wait_with_gm_busy() -> None:
    """BR-V5-03: past ``timeout_s`` the write is refused (409 gm_busy), nothing waits on."""
    guard = TurnGuard()
    inside = threading.Event()
    release = threading.Event()

    def holder() -> None:
        with guard.short_write("s", timeout_s=5):
            inside.set()
            release.wait(5)

    t = threading.Thread(target=holder)
    t.start()
    assert inside.wait(5)
    began = time.monotonic()
    try:
        with pytest.raises(GmBusyError) as err:
            with guard.short_write("s", timeout_s=0.05):
                pytest.fail("entered a held section")
        assert time.monotonic() - began < 2
        _no_internals(err.value, "s:")
        with guard.short_write("other", timeout_s=0.05):  # per session
            pass
    finally:
        release.set()
        t.join(5)
    with guard.short_write("s", timeout_s=0.05):  # free again
        pass


def test_v5_short_write_is_re_entrant_in_one_thread_and_released_on_error() -> None:
    """BR-V5-04: a seed start creates its event inside its own section."""
    guard = TurnGuard()
    with guard.short_write("s", timeout_s=0.1):
        with guard.short_write("s", timeout_s=0.1):
            pass
    with pytest.raises(RuntimeError):
        with guard.short_write("s", timeout_s=0.1):
            raise RuntimeError("boom")
    seen: list[bool] = []

    def other() -> None:
        with guard.short_write("s", timeout_s=0.5):
            seen.append(True)

    t = threading.Thread(target=other)
    t.start()
    t.join(5)
    assert seen == [True]  # the raising section let go


def test_v5_the_old_guard_methods_are_gone() -> None:
    """BR-V5-25: callers use turn_running / gm_busy / closing."""
    for name in ("is_running", "running_run_id", "assert_idle"):
        assert not hasattr(TurnGuard, name)
