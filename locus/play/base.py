"""Shared building blocks for the game-session application services.

The per-turn orchestration was originally one large ``GameMasterService``; it is
now split into focused, single-responsibility services (event / rumor /
distortion / turn) that are composed by the coordinator. They share three
concerns — a session-open guard, a canonical-region guard, and timeline
recording — collected here so each service stays small and the guards behave
identically everywhere.
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.play.errors import InvalidActionError
from locus.play.models import (
    GameSession,
    Player,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.play.ports import PlayRepository


class SessionClosedError(RuntimeError):
    """Raised when a write action targets a CLOSED session (BR-S2-9)."""


def require_region(snapshots: SnapshotSource, world_id: str, region_id: str) -> None:
    """Validate a region exists in the canonical topology (read-only; BR-P1-2)."""
    if region_id not in snapshots.get(world_id).regions_by_id:
        raise LookupError(f"region not found: {region_id}")


class SessionAppService:
    """Base for session application services: a repository plus the two guards
    (session-open / session-exists) and timeline recording every service needs.
    """

    def __init__(self, repo: PlayRepository) -> None:
        self._repo = repo

    def _require_session(self, session_id: str) -> GameSession:
        """Return the session or raise ``LookupError`` (reads: closed allowed)."""
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        return session

    def _require_open(self, session_id: str) -> GameSession:
        """Return the session, raising if it is missing or CLOSED (writes)."""
        session = self._require_session(session_id)
        if session.status == SessionStatus.CLOSED.value:
            raise SessionClosedError(f"session is closed: {session_id}")
        return session

    def _require_player(self, session_id: str) -> Player:
        """The session's player, or ``InvalidActionError`` (400) for a GM session
        without one — the one copy every player-facing service uses (U5 review C4)."""
        player = self._repo.get_player(session_id)
        if player is None:
            raise InvalidActionError(f"session has no player: {session_id}")
        return player

    def _timeline(
        self,
        session: GameSession,
        kind: TimelineKind,
        summary: str,
        payload: dict,
        *,
        turn: int | None = None,
    ) -> None:
        """Append exactly one TimelineEntry for a GameMaster change (FR-R4.2)."""
        self._repo.append_timeline(self._entry(session, kind, summary, payload, turn=turn))

    @staticmethod
    def _entry(
        session: GameSession,
        kind: TimelineKind,
        summary: str,
        payload: dict,
        *,
        turn: int | None = None,
    ) -> TimelineEntry:
        """Build the entry without writing it — for services that append inside a
        unit of work (``u.timeline.append_timeline(...)``, BR-U4-14)."""
        return TimelineEntry(
            session_id=session.id,
            turn=session.turn if turn is None else turn,
            kind=kind,
            summary=summary,
            payload=payload,
        )
