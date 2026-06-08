"""AugmentationEngine — detect issues, generate questions, apply/revert (U7)."""

from __future__ import annotations

from .apply import apply_answer
from .apply import revert as _revert
from .detectors import detect_all
from .questions import QuestionGenerator
from .types import AugmentationAnswer, AugmentationQuestion, ChangeSet, Issue


class AugmentationEngine:
    def __init__(self, loader, editor, graph_repo, wiki=None, llm=None) -> None:
        self._loader = loader
        self._editor = editor
        self._graph = graph_repo
        self._wiki = wiki
        self._llm = llm
        self._qgen = QuestionGenerator(llm)

    def detect_issues(self, world_id: str) -> list[Issue]:
        kg, topo = self._loader.load(world_id)
        return detect_all(kg, topo, wiki=self._wiki, llm=self._llm)

    def generate_questions(self, issues: list[Issue]) -> list[AugmentationQuestion]:
        return [self._qgen.generate(i) for i in issues]

    def apply_answer(self, world_id: str, answer: AugmentationAnswer) -> ChangeSet:
        return apply_answer(answer, world_id=world_id, graph_repo=self._graph, editor=self._editor)

    def revert(self, world_id: str, change_set: ChangeSet) -> None:
        _revert(change_set, world_id=world_id, graph_repo=self._graph, editor=self._editor)
