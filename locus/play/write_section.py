"""WriteSection — the read-modify-write part of a GM write (V5 FD business-logic-model § 1).

Every GM write has the same shape: input checks, world reads and LLM drafts outside;
then, one at a time per session, the session's short write and one unit of work in which
the session is read again, the rows to change are read fresh, conditions are checked
again, the rows are written and the line for that change goes in with them (BR-V5-01,
RE-P05). Because sections of a session run in turn, a second write reads what the first
wrote, so absolute writes come out as if the two ran in order.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from locus.play.base import SessionClosedError
from locus.play.models import GameSession, SessionStatus
from locus.play.ports import PlayRepository, PlayUnitOfWork
from locus.play.turn.guard import TurnGuard
from locus.shared.config.tuning import PlayTuning


class WriteSection:
    """One session's GM save section. Built with no guard (a service constructed on its
    own, e.g. in a test) it uses a guard of its own (code plan R-03)."""

    def __init__(
        self,
        repo: PlayRepository,
        guard: TurnGuard | None = None,
        tuning: PlayTuning | None = None,
    ) -> None:
        self._repo = repo
        self.guard = guard if guard is not None else TurnGuard()
        self._wait_s = (tuning or PlayTuning()).gm_write_wait_s

    @contextmanager
    def lock(self, session_id: str) -> Iterator[None]:
        """Only the session's short write: 409 ``gm_busy`` past the wait (BR-V5-03).
        Re-entrant in one thread, so a section may call a write that opens its own
        (a seed start creates its event, BR-V5-04)."""
        with self.guard.short_write(session_id, timeout_s=self._wait_s):
            yield

    @contextmanager
    def open(self, session_id: str) -> Iterator[tuple[PlayUnitOfWork, GameSession]]:
        """The short write, then one unit of work with the session read again inside:
        missing → ``LookupError``, closed → ``SessionClosedError`` and nothing is written
        (BR-V5-02)."""
        with self.lock(session_id):
            with self._repo.uow() as u:
                session = u.sessions.get_session(session_id)
                if session is None:
                    raise LookupError(f"session not found: {session_id}")
                if session.status == SessionStatus.CLOSED.value:
                    raise SessionClosedError(f"session is closed: {session_id}")
                yield u, session
