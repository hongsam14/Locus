"""AugmentationEngine — detect issues, generate questions, apply/revert (U7)."""

from __future__ import annotations

from locus.world.augmentation.apply import apply_answer
from locus.world.augmentation.apply import revert as _revert
from locus.world.augmentation.detectors import detect_all
from locus.world.augmentation.questions import QuestionGenerator
from locus.world.augmentation.types import (
    AugmentationAnswer,
    AugmentationQuestion,
    ChangeSet,
    Issue,
)


class AugmentationEngine:
    def __init__(
        self,
        snapshots,
        editor,
        graph_repo,
        wiki=None,
        llm=None,
        wiki_provider=None,
        *,
        cache=None,
    ) -> None:
        self._snapshots = snapshots  # SnapshotSource (WorldCache)
        # apply.py writes to graph_repo directly (ADD scope edges, revert), so the
        # engine invalidates after every apply/revert (BR-U2-17, review R-03)
        self._cache = (
            cache if cache is not None else getattr(snapshots, "invalidate", None) and snapshots
        )
        self._editor = editor
        self._graph = graph_repo
        self._wiki = wiki
        self._wiki_provider = wiki_provider  # (world_id) -> CommonsenseWiki (single-world, BR-A9)
        self._llm = llm
        self._qgen = QuestionGenerator(llm)

    def detect_issues(self, world_id: str) -> list[Issue]:
        snapshot = self._snapshots.get(world_id)
        wiki = self._wiki_provider(world_id) if self._wiki_provider else self._wiki
        return detect_all(snapshot.kg, snapshot.topo, wiki=wiki, llm=self._llm)

    def generate_questions(self, issues: list[Issue]) -> list[AugmentationQuestion]:
        return [self._qgen.generate(i) for i in issues]

    def apply_answer(self, world_id: str, answer: AugmentationAnswer) -> ChangeSet:
        try:
            return apply_answer(
                answer, world_id=world_id, graph_repo=self._graph, editor=self._editor
            )
        finally:
            self._invalidate(world_id)

    def revert(self, world_id: str, change_set: ChangeSet) -> None:
        try:
            _revert(change_set, world_id=world_id, graph_repo=self._graph, editor=self._editor)
        finally:
            self._invalidate(world_id)

    def _invalidate(self, world_id: str) -> None:
        if self._cache is not None and hasattr(self._cache, "invalidate"):
            self._cache.invalidate(world_id)
