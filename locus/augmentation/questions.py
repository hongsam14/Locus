"""Question generation from issues (U7, FD7-Q3=A): template + optional LLM."""

from __future__ import annotations

from pydantic import BaseModel, Field

from .types import AugmentationQuestion, Issue, IssueType


class _QuestionDraft(BaseModel):
    text: str
    options: list[str] = Field(default_factory=list)


_TEMPLATES = {
    IssueType.GAP: (
        "This region has no knowledge yet. What does a local know about it?",
        ["add", "ignore"],
    ),
    IssueType.DANGLING: (
        "A relation points to a missing entity. Fix or remove it?",
        ["edit", "remove", "ignore"],
    ),
    IssueType.LOW_CONFIDENCE: (
        "Is this low-confidence item correct?",
        ["confirm", "edit", "remove", "ignore"],
    ),
    IssueType.WIKI_CONFLICT: (
        "This may contradict real-world common sense. Keep or fix?",
        ["confirm", "edit", "ignore"],
    ),
}


class QuestionGenerator:
    def __init__(self, llm=None) -> None:
        self._llm = llm

    def generate(self, issue: Issue) -> AugmentationQuestion:
        template_text, options = _TEMPLATES.get(
            IssueType(issue.type), ("Please review this item.", ["confirm", "ignore"])
        )
        text = template_text
        if self._llm is not None:
            try:
                draft = self._llm.structured(
                    f"Write a concise clarifying question for a game designer about this issue:\n"
                    f"{issue.description}",
                    _QuestionDraft,
                )
                text = draft.text or template_text
                if draft.options:
                    options = draft.options
            except Exception:
                pass  # template fallback
        kind = "confirm" if len(options) <= 2 else "choose"
        return AugmentationQuestion(issue_id=issue.id, text=text, options=options, kind=kind)
