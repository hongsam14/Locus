"""Shared building blocks for the game-session application services.

The per-turn orchestration was originally one large ``GameMasterService``; it is
now split into focused, single-responsibility services (event / rumor /
distortion / turn) that are composed by the coordinator. They share three
concerns — a session-open guard, a canonical-region guard, and timeline
recording — collected here so each service stays small and the guards behave
identically everywhere.
"""

from __future__ import annotations

from ..query.loader import WorldLoader
from .models import (
    GameSession,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from .repository import SessionRepository


class SessionClosedError(RuntimeError):
    """Raised when a write action targets a CLOSED session (BR-S2-9)."""


def clamp(value: float) -> float:
    """Clamp a degree/support value to the [0, 1] domain (BR-S1-10)."""
    return max(0.0, min(1.0, value))


def require_region(loader: WorldLoader, world_id: str, region_id: str) -> None:
    """Validate a region exists in the canonical topology (read-only; BR-P1-2)."""
    _kg, topo = loader.load(world_id)
    if region_id not in {r.id for r in topo.regions}:
        raise LookupError(f"region not found: {region_id}")


class SessionAppService:
    """Base for session application services: a repository plus the two guards
    (session-open / session-exists) and timeline recording every service needs.
    """

    def __init__(self, repo: SessionRepository) -> None:
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
        self._repo.append_timeline(
            TimelineEntry(
                session_id=session.id,
                turn=session.turn if turn is None else turn,
                kind=kind,
                summary=summary,
                payload=payload,
            )
        )
