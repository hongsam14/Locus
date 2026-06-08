"""AugmentationService — interactive Q&A loop with convergence (U7, FR-F)."""

from __future__ import annotations

from .engine import AugmentationEngine
from .session_store import InMemorySessionStore, SessionStore
from .types import AugmentationAnswer, AugmentationSession, ChangeSet, SessionStatus


class AugmentationService:
    def __init__(
        self,
        engine: AugmentationEngine,
        store: SessionStore | None = None,
        *,
        max_rounds: int = 5,
    ) -> None:
        self._engine = engine
        self._store = store or InMemorySessionStore()
        self._max_rounds = max_rounds

    def start_session(self, world_id: str) -> AugmentationSession:
        issues = self._engine.detect_issues(world_id)
        session = AugmentationSession(
            world_id=world_id,
            open_questions=self._engine.generate_questions(issues),
            status=SessionStatus.OPEN if issues else SessionStatus.CONVERGED,
        )
        self._store.save(session)
        return session

    def submit_answer(self, session_id: str, answer: AugmentationAnswer) -> ChangeSet:
        session = self._store.get(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")

        change = self._engine.apply_answer(session.world_id, answer)
        session.history.append(change)
        session.round += 1

        issues = self._engine.detect_issues(session.world_id)
        if not issues:
            session.status = SessionStatus.CONVERGED
            session.open_questions = []
        elif session.round >= self._max_rounds:
            session.status = SessionStatus.STOPPED
            session.open_questions = []
        else:
            session.open_questions = self._engine.generate_questions(issues)

        self._store.save(session)
        return change

    def revert(self, session_id: str, change_id: str) -> None:
        session = self._store.get(session_id)
        if session is None:
            raise LookupError(f"session not found: {session_id}")
        change = next((c for c in session.history if c.id == change_id), None)
        if change is None:
            raise LookupError(f"change not found: {change_id}")
        self._engine.revert(session.world_id, change)

    def get_session(self, session_id: str) -> AugmentationSession | None:
        return self._store.get(session_id)
