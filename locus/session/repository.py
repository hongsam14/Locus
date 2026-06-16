"""SessionRepository port (Protocol) — session-layer persistence (NFR-R1).

Same port convention as the canonical GraphRepository/SearchRepository. Core
services depend on this Protocol; the PostgreSQL adapter and the in-memory
adapter implement it. Every operation is scoped by ``session_id`` so sessions
stay isolated (BR-S1-15).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import GameSession, RegionDistortion, SessionRumor, TimelineEntry


@runtime_checkable
class SessionRepository(Protocol):
    """Persistence for the game-session layer."""

    # --- lifecycle ---
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def health_check(self) -> bool: ...
    def ensure_schema(self) -> None: ...  # idempotent DDL (BR-S1-17)

    # --- sessions ---
    def create_session(self, world_id: str) -> GameSession: ...  # turn=0, status=OPEN
    def get_session(self, session_id: str) -> GameSession | None: ...
    def list_sessions(self, world_id: str) -> list[GameSession]: ...
    def close_session(self, session_id: str) -> GameSession: ...  # idempotent (BR-S1-4)
    def bump_turn(self, session_id: str) -> int: ...  # turn += 1, returns new turn

    # --- rumors ---
    def upsert_rumor(self, rumor: SessionRumor) -> SessionRumor: ...
    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None: ...
    def list_rumors(self, session_id: str, region_id: str | None = None) -> list[SessionRumor]: ...
    def delete_rumor(self, session_id: str, rumor_id: str) -> None: ...

    # --- region distortion ---
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None: ...
    def get_region_distortion(self, session_id: str, region_id: str) -> float | None: ...
    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]: ...

    # --- timeline ---
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry: ...
    def list_timeline(self, session_id: str) -> list[TimelineEntry]: ...  # turn, then created_at
