"""SessionService — GameSession lifecycle (FD §4).

Thin layer over SessionRepository. On ``start_session`` it (1) validates the
world exists in the canonical graph (FD-S1 Q2=A, BR-S1-2) and (2) seeds a
default RegionDistortion row for every region (FD-S1 Q1=B, BR-S1-3). Canonical
access is read-only (NFR-R2).
"""

from __future__ import annotations

from ..storage.base import GraphRepository
from .models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    TimelineEntry,
)
from .repository import SessionRepository


class WorldNotFoundError(LookupError):
    """Raised when starting a session for a world with no canonical data."""


class SessionService:
    def __init__(self, repo: SessionRepository, graph_repo: GraphRepository) -> None:
        self._repo = repo
        self._graph = graph_repo

    def start_session(self, world_id: str) -> GameSession:
        # 1) validate world exists (has at least one Region) — read-only (BR-S1-2)
        regions = self._graph.find_nodes(world_id, "Region")
        if not regions:
            raise WorldNotFoundError(f"world not found or empty: {world_id}")
        # 2) create the session (turn=0, status=OPEN)
        session = self._repo.create_session(world_id)
        # 3) seed a default distortion row for every region (BR-S1-3)
        for node in regions:
            self._repo.set_region_distortion(session.id, node.id, DEFAULT_DISTORTION_DEGREE)
        return session

    def close_session(self, session_id: str) -> GameSession:
        self._require(session_id)
        return self._repo.close_session(session_id)

    def get_session(self, session_id: str) -> GameSession:
        return self._require(session_id)

    def list_sessions(self, world_id: str) -> list[GameSession]:
        return self._repo.list_sessions(world_id)

    def get_timeline(self, session_id: str) -> list[TimelineEntry]:
        self._require(session_id)
        return self._repo.list_timeline(session_id)

    def _require(self, session_id: str) -> GameSession:
        session = self._repo.get_session(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        return session
