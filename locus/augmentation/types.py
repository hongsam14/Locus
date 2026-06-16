"""U7 Augmentation domain types (Pydantic)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..models import new_id
from ..models.enums import StrEnum


class IssueType(StrEnum):
    GAP = "gap"
    DANGLING = "dangling"
    WIKI_CONFLICT = "wiki_conflict"
    LOW_CONFIDENCE = "low_confidence"
    ORPHAN = "orphan"  # entity with no LOCATED_IN / RELATED_TO / ABOUT edge (FR-IM4.3)


class AnswerAction(StrEnum):
    CONFIRM = "confirm"
    REMOVE = "remove"
    ADD = "add"
    EDIT = "edit"
    IGNORE = "ignore"


class SessionStatus(StrEnum):
    OPEN = "open"
    CONVERGED = "converged"
    STOPPED = "stopped"


class _Aug(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Issue(_Aug):
    id: str = Field(default_factory=new_id)
    type: IssueType
    description: str
    target_ids: list[str] = Field(default_factory=list)
    region_id: str | None = None
    severity: float = Field(default=0.5, ge=0.0, le=1.0)


class AugmentationQuestion(_Aug):
    id: str = Field(default_factory=new_id)
    issue_id: str
    text: str
    options: list[str] = Field(default_factory=list)
    kind: str = "choose"  # confirm | choose | free


class AugmentationAnswer(_Aug):
    question_id: str
    action: AnswerAction
    target_id: str | None = None
    statement: str | None = None
    title: str | None = None  # optional one-line title for added knowledge (FR-IM3.1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    region_id: str | None = None


class NodeSnapshot(_Aug):
    id: str
    label: str
    properties: dict = Field(default_factory=dict)


class ChangeSet(_Aug):
    id: str = Field(default_factory=new_id)
    description: str = ""
    added_ids: list[str] = Field(default_factory=list)
    removed: list[NodeSnapshot] = Field(default_factory=list)
    updated: list[NodeSnapshot] = Field(default_factory=list)  # before-state


class AugmentationSession(_Aug):
    id: str = Field(default_factory=new_id)
    world_id: str
    round: int = 0
    status: SessionStatus = SessionStatus.OPEN
    open_questions: list[AugmentationQuestion] = Field(default_factory=list)
    history: list[ChangeSet] = Field(default_factory=list)
