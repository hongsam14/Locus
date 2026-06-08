"""Augmentation session storage (U7, FD7-Q5=A).

In-memory for MVP; the ``SessionStore`` protocol allows swapping in a PostgreSQL
implementation later without touching the service.
"""

from __future__ import annotations

from typing import Protocol

from .types import AugmentationSession


class SessionStore(Protocol):
    def save(self, session: AugmentationSession) -> None: ...
    def get(self, session_id: str) -> AugmentationSession | None: ...
    def delete(self, session_id: str) -> None: ...


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._sessions: dict[str, AugmentationSession] = {}

    def save(self, session: AugmentationSession) -> None:
        self._sessions[session.id] = session

    def get(self, session_id: str) -> AugmentationSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
