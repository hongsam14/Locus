"""Shared building blocks for the game-session application services.

The per-turn orchestration was originally one large ``GameMasterService``; it is
now split into focused, single-responsibility services (event / rumor /
distortion / turn) that are composed by the coordinator. They share three
concerns — a session-open guard, a canonical-region guard, and timeline
recording — collected here so each service stays small and the guards behave
identically everywhere.
"""

from __future__ import annotations

from collections.abc import Mapping

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
from locus.shared.models import Region, WorldSnapshot


class SessionClosedError(RuntimeError):
    """Raised when a write action targets a CLOSED session (BR-S2-9)."""


def require_region(snapshots: SnapshotSource, world_id: str, region_id: str) -> Region:
    """The region, which must exist in the canonical topology (read-only; BR-P1-2)."""
    region = snapshots.get(world_id).regions_by_id.get(region_id)
    if region is None:
        raise LookupError(f"region not found: {region_id}")
    return region


# --- region names on timeline lines (FR-D3; one rule, U7 review C4) --------------- #
def names_of(snapshot: WorldSnapshot) -> dict[str, str]:
    """region id -> name, built once per call site."""
    return {r.id: r.name for r in snapshot.topo.regions}


def region_name(names: Mapping[str, str], region_id: str) -> str:
    """The region's name; its id when the world no longer has it (FR-D3)."""
    return names.get(region_id, region_id)


def where(names: Mapping[str, str], region_id: str) -> dict[str, str]:
    """The ``region_id`` / ``region_name`` pair a region line's payload carries."""
    return {"region_id": region_id, "region_name": region_name(names, region_id)}


class SnapshotNames:
    """For services holding ``self._snapshots``: one way to name a region."""

    _snapshots: SnapshotSource

    def _region_name(self, session: GameSession, region_id: str) -> str:
        return region_name(names_of(self._snapshots.get(session.world_id)), region_id)


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
