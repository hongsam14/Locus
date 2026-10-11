"""TurnGuard — what holds a session right now (U4; V5 FD domain-entities § 1).

Process-local (the API runs one worker, see operations.md). Per session it keeps:

- the **turn slot**: one running turn run. A turn excludes every other turn, every GM or
  editor lease and a close (BR-U4-13).
- **closing**: how many session closes are under way. They only keep new turns out; a
  count, so of two overlapping closes the first to finish does not lift the other's hold
  (V5 BR-V5-14/16).
- **leases**: GM writes and the editor's region delete in progress. Leases share the
  session with each other (U7 review #2: a bulk generate runs five writes at once) and
  exclude turns. A count: ``gm_busy`` clears only when the last one leaves.
- the **short write**: one re-entrant lock per session. Inside a lease, the read-modify-
  write part of a GM write (and a close) takes it, so those parts run one at a time and
  each reads what the one before wrote (V5 FR-C1/C2, AD Q1=A). LLM calls stay outside.

Lock order is always lease → short write → the repository's unit of work.

Error sentences carry no session id, run id or lease token (V5 FR-C5, #5(a)).
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from locus.play.base import SessionClosedError
from locus.play.errors import GmBusyError, TurnInProgressError

TURN_RUNNING = "a turn is running in this session; retry when it ends"
GM_BUSY = "the session is busy with a GM write; retry shortly"
CLOSING = "the session is closing"


class TurnGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[str, str] = {}  # session_id -> run_id (a turn)
        self._closing: dict[str, int] = {}  # session_id -> closes under way
        self._leases: dict[str, int] = {}  # session_id -> GM / editor writes in progress
        self._writes: dict[str, threading.RLock] = {}  # session_id -> its short-write lock

    # -- turns -----------------------------------------------------------------
    def acquire(self, session_id: str, run_id: str) -> None:
        """A turn: refused while a turn, a close or any lease holds the session."""
        with self._lock:
            if session_id in self._running:
                raise TurnInProgressError(TURN_RUNNING)
            if self._closing.get(session_id, 0):
                raise SessionClosedError(CLOSING)
            if self._leases.get(session_id, 0):
                raise GmBusyError(GM_BUSY)
            self._running[session_id] = run_id

    def release(self, session_id: str) -> None:
        with self._lock:
            self._running.pop(session_id, None)

    def turn_running(self, session_id: str) -> bool:
        """A turn run holds the session (only that; V5 BR-V5-22)."""
        with self._lock:
            return session_id in self._running

    def gm_busy(self, session_id: str) -> bool:
        """A GM write or the editor holds a lease on the session."""
        with self._lock:
            return self._leases.get(session_id, 0) > 0

    # -- leases ----------------------------------------------------------------
    @contextmanager
    def hold(self, session_id: str, *, label: str = "gm") -> Iterator[str]:
        """Hold a lease for the whole block, like a turn run holds the session.

        GM writes take seconds (LLM), so the turn/GM exclusion rule (FD R-06) only holds
        if the write keeps the session for its whole duration: with a mere check, a turn
        could start mid-write and its promotion be deleted by the write's stale view
        (code review U4-2 #7). Never waits: a running turn raises at once (409). A close
        under way does not refuse the lease: the write's save will see the session closed.
        """
        token = f"{label}:{uuid4().hex[:8]}"
        with self._lock:
            if session_id in self._running:  # only a turn excludes a lease (U7 review #2)
                raise TurnInProgressError(TURN_RUNNING)
            self._leases[session_id] = self._leases.get(session_id, 0) + 1
        try:
            yield token
        finally:
            with self._lock:
                left = self._leases.get(session_id, 0) - 1
                if left > 0:
                    self._leases[session_id] = left
                else:
                    self._leases.pop(session_id, None)

    # -- the short write and closing (V5) --------------------------------------
    @contextmanager
    def short_write(self, session_id: str, *, timeout_s: float) -> Iterator[None]:
        """One read-modify-write section at a time per session (V5 BR-V5-01/03/04).

        Re-entrant in the same thread (a seed start creates its event inside its own
        section). Waits at most ``timeout_s``; past it the write is refused with
        ``GmBusyError`` (409 ``gm_busy``) and nothing is written.
        """
        with self._lock:
            lock = self._writes.setdefault(session_id, threading.RLock())
        # clamped: a timeout past TIMEOUT_MAX raises OverflowError (code review 01 #5)
        if not lock.acquire(timeout=min(max(0.0, timeout_s), threading.TIMEOUT_MAX)):
            raise GmBusyError(GM_BUSY)
        try:
            yield
        finally:
            lock.release()

    def forget(self, session_id: str) -> None:
        """Drop a closed session's short-write lock (code review 01 #10). A writer still
        holding the old lock finds the session closed in its section and writes
        nothing, so a fresh lock beside it is harmless."""
        with self._lock:
            self._writes.pop(session_id, None)

    @contextmanager
    def closing(self, session_id: str) -> Iterator[None]:
        """Keep new turns out while the session closes (V5 BR-V5-14/16). Refused while a
        turn runs; leases are not waited for — the close waits only for a save section
        in progress, through ``short_write``."""
        with self._lock:
            if session_id in self._running:
                raise TurnInProgressError(TURN_RUNNING)
            self._closing[session_id] = self._closing.get(session_id, 0) + 1
        try:
            yield
        finally:
            with self._lock:
                left = self._closing.get(session_id, 0) - 1
                if left > 0:
                    self._closing[session_id] = left
                else:
                    self._closing.pop(session_id, None)
