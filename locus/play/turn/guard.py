"""TurnGuard — one running turn per session (U4; Q3=A, BR-U4-13, FR-E3).

Process-local (the API runs one worker, see operations.md). ``acquire`` never
waits: a second caller gets ``TurnInProgressError`` (409) at once. GM writes
that touch session state call ``assert_idle`` so a turn's computed values never
overwrite a concurrent GM edit (FD R-06).
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
        self._running: dict[str, str] = {}  # session_id -> run_id

    def acquire(self, session_id: str, run_id: str) -> None:
        with self._lock:
            current = self._running.get(session_id)
            if current is not None:
                raise TurnInProgressError(f"turn in progress: {session_id} (run {current})")
            self._running[session_id] = run_id

    def release(self, session_id: str) -> None:
        with self._lock:
            self._running.pop(session_id, None)

    def is_running(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._running

    def running_run_id(self, session_id: str) -> str | None:
        with self._lock:
            return self._running.get(session_id)

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
        self.acquire(session_id, token)
        try:
            yield token
        finally:
            self.release(session_id)
