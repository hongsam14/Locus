"""U7 Augmentation — interactive knowledge-augmentation Q&A (FR-F)."""

from .engine import AugmentationEngine
from .service import AugmentationService
from .session_store import InMemorySessionStore, SessionStore
from .types import (
    AnswerAction,
    AugmentationAnswer,
    AugmentationQuestion,
    AugmentationSession,
    ChangeSet,
    Issue,
    IssueType,
)

__all__ = [
    "AugmentationEngine",
    "AugmentationService",
    "InMemorySessionStore",
    "SessionStore",
    "AnswerAction",
    "AugmentationAnswer",
    "AugmentationQuestion",
    "AugmentationSession",
    "ChangeSet",
    "Issue",
    "IssueType",
]
