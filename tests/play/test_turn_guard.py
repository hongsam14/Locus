"""U4 TurnGuard — TP-U4-6 concurrency + executor behaviour (Step 4.6)."""

from __future__ import annotations

import threading
import time

import pytest

from locus.play.errors import TurnInProgressError
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
    assert guard.is_running("s") and guard.running_run_id("s") is not None
    with pytest.raises(TurnInProgressError):
        guard.assert_idle("s")
    guard.release("s")
    assert not guard.is_running("s")
    guard.assert_idle("s")  # idle now


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
