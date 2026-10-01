"""TurnExecutor — where background turn runs execute (U4; Q4=A, FD R-14/R-08).

``ThreadTurnExecutor`` runs submitted callables one at a time on a single
**daemon** worker thread (serial across sessions; the guard prevents two runs
of one session). ``shutdown(timeout)`` stops accepting work and waits at most
``timeout`` seconds for the queue to drain; a hung LLM call cannot block process
exit because the worker is a daemon (the next startup marks its run
``interrupted``). ``SyncTurnExecutor`` runs inline (tests).
"""

from __future__ import annotations

import logging
import queue
import threading
from typing import Any, Callable, Protocol

from locus.play.errors import ExecutorShutdownError

logger = logging.getLogger(__name__)

_STOP = object()


class TurnExecutor(Protocol):
    def submit(self, fn: Callable[..., Any], *args: Any) -> None: ...
    def shutdown(self, timeout: float) -> None: ...


class SyncTurnExecutor:
    """Runs the callable immediately on the caller's thread (offline tests)."""

    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        fn(*args)

    def shutdown(self, timeout: float) -> None:  # nothing pending
        return None


class ThreadTurnExecutor:
    """Single daemon worker + FIFO queue (BR-U4-32, NFR nfr-light §2)."""

    def __init__(self, *, name: str = "turn") -> None:
        self._queue: queue.Queue[Any] = queue.Queue()
        self._closed = False
        self._lock = threading.Lock()
        self._worker = threading.Thread(target=self._loop, name=name, daemon=True)
        self._worker.start()

    def submit(self, fn: Callable[..., Any], *args: Any) -> None:
        with self._lock:
            if self._closed:
                raise ExecutorShutdownError("turn executor is shut down")
            self._queue.put((fn, args))

    def shutdown(self, timeout: float) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._queue.put(_STOP)
        self._worker.join(timeout=max(0.0, timeout))
        if self._worker.is_alive():
            logger.warning("turn executor still busy after %.1fs; leaving daemon worker", timeout)

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    def _loop(self) -> None:
        try:
            while True:
                item = self._queue.get()
                if item is _STOP:
                    return
                fn, args = item
                try:
                    fn(*args)
                except BaseException:  # noqa: BLE001 - the run records its own failure;
                    # a dead worker would strand every later run as `running` and keep the
                    # session 409 forever, so nothing may kill this loop (code review U4 #8).
                    logger.exception("turn run raised")
        finally:
            # If the loop ever leaves without a _STOP, refuse new work instead of
            # accepting runs nobody will execute.
            with self._lock:
                self._closed = True
