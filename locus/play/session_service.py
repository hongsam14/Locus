"""SessionService — GameSession lifecycle (FD §4; U4 BLM §1).

Thin layer over PlayRepository. Starting a session (1) validates the world
exists through the canonical snapshot (``SnapshotSource``; LookupError ->
``WorldNotFoundError``, 404) and (2) seeds a default RegionDistortion row for
every region (FD-S1 Q1=B, BR-S1-3) — in **one unit of work** (RE C4, BR-U4-2).
Canonical access is read-only (NFR-R2).

``start(world_id, PlayerCreate)`` is the player-mode entry (US-3.1): it also
creates the solo player and the ``SESSION_STARTED`` timeline entry. The older
``start_session(world_id)`` keeps creating player-less GM sessions (BR-U4-30);
since U7 it records its start as well (BR-U7-11, FR-E4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from locus.knowledge.cache import SnapshotSource
from locus.play.errors import InvalidActionError
from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    Player,
    PlayerCreate,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.play.ports import PlayRepository
from locus.play.turn.guard import TurnGuard
from locus.shared.models import WorldSnapshot

if TYPE_CHECKING:  # wired by assemble_play
    from locus.play.deeds.service import DeedService


class WorldNotFoundError(LookupError):
    """Raised when starting a session for a world with no canonical data."""


class SessionService:
    def __init__(
        self,
        repo: PlayRepository,
        snapshots: SnapshotSource,
        guard: TurnGuard | None = None,
        *,
        deeds: DeedService | None = None,
    ) -> None:
        self._repo = repo
        self._snapshots = snapshots
        self._guard = guard if guard is not None else TurnGuard()
        self._deeds = deeds  # U6: the start region's arrival is the first deed (BR-U6-1)

    def start_session(self, world_id: str) -> GameSession:
        """GM session without a player (pre-U4 contract). U7 (BR-U7-11, FR-E4): its
        start is recorded too — ``player: null`` and no region."""
        snapshot = self._snapshot(world_id)
        with self._repo.uow() as u:
            session = u.sessions.create_session(world_id)
            for region in snapshot.topo.regions:  # BR-S1-3
                u.distortions.set_region_distortion(
                    session.id, region.id, DEFAULT_DISTORTION_DEGREE
                )
            u.timeline.append_timeline(
                TimelineEntry(
                    session_id=session.id,
                    turn=session.turn,
                    kind=TimelineKind.SESSION_STARTED,
                    summary="GM session started",
                    payload={"player": None},
                )
            )
        return session

    def start(self, world_id: str, player: PlayerCreate) -> tuple[GameSession, Player]:
        """Player-mode session start (US-3.1, BR-U4-1/2): session + player + default
        distortions + ``SESSION_STARTED`` in one unit of work."""
        snapshot = self._snapshot(world_id)
        region = snapshot.regions_by_id.get(player.start_region_id)
        if region is None:
            raise InvalidActionError(f"start region not in world: {player.start_region_id}")
        with self._repo.uow() as u:
            session = u.sessions.create_session(world_id)
            created = u.players.create_player(
                Player(session_id=session.id, name=player.name, region_id=region.id)
            )
            for r in snapshot.topo.regions:
                u.distortions.set_region_distortion(session.id, r.id, DEFAULT_DISTORTION_DEGREE)
            arrival = (
                self._deeds.arrival(u, session, created, region, snapshot)
                if self._deeds is not None
                else None
            )
            u.timeline.append_timeline(
                TimelineEntry(
                    session_id=session.id,
                    turn=session.turn,
                    kind=TimelineKind.SESSION_STARTED,
                    summary=f"{created.name} arrives in {region.name}",
                    payload={
                        "player_id": created.id,
                        "player_name": created.name,
                        "region_id": region.id,
                        "region_name": region.name,
                        "deed_id": arrival.id if arrival is not None else None,
                    },
                )
            )
        return session, created

    def close_session(self, session_id: str) -> GameSession:
        current = self._require(session_id)
        self._guard.assert_idle(session_id)  # BR-U4-5: not while a turn run is in progress
        with self._repo.uow() as u:
            closed = u.sessions.close_session(session_id)
            if current.status != SessionStatus.CLOSED.value:  # write the entry once
                u.timeline.append_timeline(
                    TimelineEntry(
                        session_id=session_id,
                        turn=closed.turn,
                        kind=TimelineKind.SESSION_CLOSED,
                        summary="session closed",
                        payload={},
                    )
                )
        return closed

    def get_session(self, session_id: str) -> GameSession:
        return self._require(session_id)

    def list_sessions(self, world_id: str) -> list[GameSession]:
        return self._repo.list_sessions(world_id)

    def open_sessions(self, world_id: str) -> list[GameSession]:
        """The world's open sessions — the one filter every caller uses (U3 review C7)."""
        return [
            s
            for s in self._repo.list_sessions(world_id)
            if SessionStatus(s.status) is SessionStatus.OPEN
        ]

    def open_player_regions(self, world_id: str) -> dict[str, list[str]]:
        """region id -> the open sessions whose player stands there (U3 Q2=A): the
        regions the world editor may not delete (BR-U3-16)."""
        out: dict[str, list[str]] = {}
        for session in self.open_sessions(world_id):
            player = self._repo.get_player(session.id)
            if player is not None:
                out.setdefault(player.region_id, []).append(session.id)
        return out

    def get_timeline(self, session_id: str) -> list[TimelineEntry]:
        self._require(session_id)
        return self._repo.list_timeline(session_id)

    # -- internals -----------------------------------------------------------
    def _snapshot(self, world_id: str) -> WorldSnapshot:
        try:
            snapshot = self._snapshots.get(world_id)
        except LookupError as exc:
            raise WorldNotFoundError(f"world not found or empty: {world_id}") from exc
        if not snapshot.topo.regions:
            raise WorldNotFoundError(f"world not found or empty: {world_id}")
        return snapshot

    def _require(self, session_id: str) -> GameSession:
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        return session
