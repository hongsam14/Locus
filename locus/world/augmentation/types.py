"""Augmentation Q&A types (U7 FR-F; U3 Q3=A, domain-entities §4 〔Step 1.3 정정〕).

A question names its target (B1) and offers a fixed set of actions per issue type (B4);
an answer is applied to the question's target, never to an id the screen sends. A run
keeps its issues, what was ignored, and the history of changes it made so a change can
be undone, latest first (BR-U3-26..28).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from locus.shared.models import new_id
from locus.shared.models.enums import StrEnum
from locus.world.refs import ConnectionKey


class IssueType(StrEnum):
    GAP = "gap"  # a region with no direct knowledge
    DANGLING = "dangling"  # an id property pointing at no node (Q3=A)
    WIKI_CONFLICT = "wiki_conflict"
    LOW_CONFIDENCE = "low_confidence"
    ORPHAN = "orphan"  # entity with no LOCATED_IN / RELATED_TO / ABOUT edge (FR-IM4.3)
    UNSCOPED = "unscoped"  # knowledge neither global nor scoped (Q3=A)


class AnswerAction(StrEnum):
    CONFIRM = "confirm"
    REMOVE = "remove"
    ADD = "add"
    EDIT = "edit"
    IGNORE = "ignore"


class RunStatus(StrEnum):
    OPEN = "open"
    CONVERGED = "converged"
    STOPPED = "stopped"


TargetKind = Literal["knowledge", "entity", "region", "connection"]  # no NPC issue (U3 C4)
Input = Literal["statement", "title", "confidence", "region", "ref"]  # what an answer carries
RefKind = Literal["region", "entity", "prior"]


class _Aug(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Issue(_Aug):
    id: str = Field(default_factory=new_id)
    type: IssueType
    description: str
    target_kind: TargetKind
    target_ids: list[str] = Field(default_factory=list)
    region_id: str | None = None
    field: str | None = None  # dangling: the broken property
    broken_id: str | None = None  # dangling: the missing id (one issue per id in a list)
    # a connection target as the detector found it: read instead of splitting "a|b|kind",
    # which breaks on a region id with "|" in it (U8 review #8, U3 review C2)
    connection: ConnectionKey | None = None
    severity: float = Field(default=0.5, ge=0.0, le=1.0)

    @property
    def key(self) -> str:
        """The same issue across detections (FD 검토 01 R-03, 02 R-11)."""
        return ":".join(
            [
                str(self.type),
                self.target_kind,
                "|".join(self.target_ids),
                self.field or "",
                self.broken_id or "",
            ]
        )


class QuestionTarget(_Aug):
    kind: TargetKind
    id: str  # a connection is "a|b|kind"
    name: str  # what the designer reads (B1)
    region_id: str | None = None
    region_name: str | None = None
    field: str | None = None
    broken_id: str | None = None
    connection: ConnectionKey | None = None  # a connection target as a key (U3 review C2)


class AugmentationQuestion(_Aug):
    """U3 review C2: the question carries its issue ``type``, which inputs each action
    needs and, for a dangling reference, what kind of node the new reference is — the
    screen reads them instead of re-deriving the server's rules."""

    id: str = Field(default_factory=new_id)
    issue_id: str
    issue_key: str
    type: IssueType | None = None
    text: str
    target: QuestionTarget | None = None
    actions: list[AnswerAction] = Field(default_factory=list)  # fixed per issue type
    needs: dict[str, list[Input]] = Field(default_factory=dict)  # action -> inputs
    ref_kind: RefKind | None = None


class AugmentationAnswer(_Aug):
    question_id: str
    action: AnswerAction
    target_id: str | None = None  # ignored: the server answers the question's target (B1)
    statement: str | None = None
    title: str | None = None  # optional one-line title for added knowledge (FR-IM3.1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    region_id: str | None = None
    ref_id: str | None = None  # dangling/edit: the new reference (region, entity or prior id)


class NodeSnapshot(_Aug):
    id: str
    label: str
    properties: dict = Field(default_factory=dict)


class EdgeSnapshot(_Aug):
    type: str
    source_id: str
    target_id: str
    properties: dict = Field(default_factory=dict)


class ChangeSet(_Aug):
    id: str = Field(default_factory=new_id)
    description: str = ""
    added_ids: list[str] = Field(default_factory=list)
    nodes_before: list[NodeSnapshot] = Field(default_factory=list)  # changed/removed, before
    nodes_after: list[NodeSnapshot] = Field(default_factory=list)  # changed/added, right after
    edges_added: list[EdgeSnapshot] = Field(default_factory=list)
    edges_removed: list[EdgeSnapshot] = Field(default_factory=list)
    reverted: bool = False
    revert_started: bool = False  # set once a revert passed its checks (U3 review S03)


class AugmentationRun(_Aug):
    id: str = Field(default_factory=new_id)
    world_id: str
    status: RunStatus = RunStatus.OPEN
    answers: int = 0  # answers received, ignore included (was ``round``)
    open_questions: list[AugmentationQuestion] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    ignored_keys: list[str] = Field(default_factory=list)
    history: list[ChangeSet] = Field(default_factory=list)
    llm_calls: int = 0
    llm_budget_exhausted: bool = False


class AnswerResult(_Aug):
    change: ChangeSet | None = None  # None for ignore (not in the history)
    run: AugmentationRun
    changed: list[QuestionTarget] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Refusals (409, domain-entities §6 〔Step 1.3 정정〕)
# --------------------------------------------------------------------------- #
class AugmentationConflict(RuntimeError):
    """A run refuses the request in its current state."""


class ChangeAlreadyRevertedError(AugmentationConflict):
    pass


class RevertOrderError(AugmentationConflict):
    """Only the latest change not yet reverted can be reverted."""


class RevertConflictError(AugmentationConflict):
    """The target was edited outside the run after this change."""


class RunFinishedError(AugmentationConflict):
    """An answer to a converged/stopped run, or an unignore on a stopped run."""
