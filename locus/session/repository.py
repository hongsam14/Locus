"""SessionRepository port (Protocol) — session-layer persistence (NFR-R1).

Same port convention as the canonical GraphRepository/SearchRepository. Core
services depend on this Protocol; the PostgreSQL adapter and the in-memory
adapter implement it. Every operation is scoped by ``session_id`` so sessions
stay isolated (BR-S1-15).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import (
    GameSession,
    RegionDistortion,
    SessionEvent,
    SessionRumor,
    TimelineEntry,
    Translation,
)


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
    def upsert_rumors(
        self, rumors: list[SessionRumor]
    ) -> list[SessionRumor]: ...  # batch, one transaction (FR-H5)
    def get_rumor(self, session_id: str, rumor_id: str) -> SessionRumor | None: ...
    def list_rumors(
        self, session_id: str, region_id: str | None = None, *, include_pruned: bool = False
    ) -> list[SessionRumor]: ...  # active-only by default (BR-H1-6)
    def delete_rumor(self, session_id: str, rumor_id: str) -> None: ...

    # --- region distortion ---
    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None: ...
    def get_region_distortion(self, session_id: str, region_id: str) -> float | None: ...
    def list_region_distortions(self, session_id: str) -> list[RegionDistortion]: ...

    # --- timeline ---
    def append_timeline(self, entry: TimelineEntry) -> TimelineEntry: ...
    def list_timeline(self, session_id: str) -> list[TimelineEntry]: ...  # turn, then created_at

    # --- events (Phase 2) ---
    def create_event(self, event: SessionEvent) -> SessionEvent: ...
    def get_event(self, session_id: str, event_id: str) -> SessionEvent | None: ...
    def list_events(
        self, session_id: str, status: str | None = None
    ) -> list[SessionEvent]: ...  # created_turn, then id
    def update_event(
        self, event: SessionEvent
    ) -> SessionEvent: ...  # status/resolved_turn/contributions
    def delete_event(self, session_id: str, event_id: str) -> None: ...

    # --- translations (X1 localization cache) ---
    def get_translation(
        self, source_kind: str, source_id: str, source_field: str, target_lang: str
    ) -> Translation | None: ...
    def get_translations_many(
        self, keys: list[tuple[str, str, str]], target_lang: str
    ) -> dict[
        tuple[str, str], Translation
    ]: ...  # keys: (kind, id, field) -> {(id, field): Translation}
    def upsert_translation(self, translation: Translation) -> Translation: ...
    def upsert_translations(
        self, translations: list[Translation]
    ) -> list[Translation]: ...  # batch, one transaction (review #8)
