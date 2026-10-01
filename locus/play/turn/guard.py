"""TurnGuard — one running turn per session (U4; Q3=A, BR-U4-13, FR-E3).

Process-local (the API runs one worker, see operations.md). ``acquire`` never
waits: a second caller gets ``TurnInProgressError`` (409) at once. GM writes
that touch session state call ``assert_idle`` so a turn's computed values never
overwrite a concurrent GM edit (FD R-06).

U7 review #2: a turn excludes everything, but GM writes only exclude turns — they
share the session with each other (``hold`` counts holders), so a GM's bulk generate
over five regions runs five writes at once as designed (U7 frontend §2.2) instead of
four of them answering 409.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from locus.play.errors import TurnInProgressError


class TurnGuard:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running: dict[str, str] = {}  # session_id -> run_id (a turn)
        self._gm: dict[str, int] = {}  # session_id -> GM writes in progress

    def acquire(self, session_id: str, run_id: str) -> None:
        """A turn: refused while another turn or any GM write holds the session."""
        with self._lock:
            current = self._running.get(session_id)
            if current is None and self._gm.get(session_id, 0):
                current = "gm"
            if current is not None:
                raise TurnInProgressError(f"turn in progress: {session_id} (run {current})")
            self._running[session_id] = run_id

    def release(self, session_id: str) -> None:
        with self._lock:
            self._running.pop(session_id, None)

    def is_running(self, session_id: str) -> bool:
        """A turn or a GM write holds the session (the player's actions wait)."""
        with self._lock:
            return session_id in self._running or self._gm.get(session_id, 0) > 0

    def running_run_id(self, session_id: str) -> str | None:
        with self._lock:
            if session_id in self._running:
                return self._running[session_id]
            return "gm" if self._gm.get(session_id, 0) else None

    def assert_idle(self, session_id: str) -> None:
        """Raise ``TurnInProgressError`` when a turn run holds this session.

        A point-in-time check. Anything that then writes for a while (an LLM call) must
        use :meth:`hold` instead, or a turn starting in the gap produces a lost update
        (code review U4-2 #7).
        """
        with self._lock:
            current = self._running.get(session_id)
        if current is not None:
            raise TurnInProgressError(f"turn in progress: {session_id} (run {current})")

    @contextmanager
    def hold(self, session_id: str, *, label: str = "gm") -> Iterator[str]:
        """Hold the session for the whole block, like a turn run does.

        GM writes take seconds (LLM), so the turn/GM exclusion rule (FD R-06) only
        holds if the write keeps the session for its whole duration: with a mere check,
        a turn could start mid-write and its promotion be deleted by the write's stale
        view (code review U4-2 #7). Never waits: a busy session raises at once (409).
        """
        token = f"{label}:{uuid4().hex[:8]}"
        with self._lock:
            current = self._running.get(session_id)
            if current is not None:  # only a turn excludes a GM write (U7 review #2)
                raise TurnInProgressError(f"turn in progress: {session_id} (run {current})")
            self._gm[session_id] = self._gm.get(session_id, 0) + 1
        try:
            yield token
        finally:
            with self._lock:
                left = self._gm.get(session_id, 0) - 1
                if left > 0:
                    self._gm[session_id] = left
                else:
                    self._gm.pop(session_id, None)
