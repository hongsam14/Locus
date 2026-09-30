"""AugmentationService — interactive Q&A loop with convergence (U7, FR-F)."""

from __future__ import annotations

from locus.world.augmentation.engine import AugmentationEngine
from locus.world.augmentation.run_store import InMemoryRunStore, RunStore
from locus.world.augmentation.types import AugmentationAnswer, AugmentationRun, ChangeSet, RunStatus


class AugmentationService:
    def __init__(
        self,
        engine: AugmentationEngine,
        store: RunStore | None = None,
        *,
        max_rounds: int = 5,
    ) -> None:
        self._engine = engine
        self._store = store or InMemoryRunStore()
        self._max_rounds = max_rounds

    def start_run(self, world_id: str) -> AugmentationRun:
        issues = self._engine.detect_issues(world_id)
        run = AugmentationRun(
            world_id=world_id,
            open_questions=self._engine.generate_questions(issues),
            status=RunStatus.OPEN if issues else RunStatus.CONVERGED,
        )
        self._store.save(run)
        return run

    def answer(self, run_id: str, answer: AugmentationAnswer) -> ChangeSet:
        run = self._store.get(run_id)
        if run is None:
            raise LookupError(f"augmentation run not found: {run_id}")

        change = self._engine.apply_answer(run.world_id, answer)
        run.history.append(change)
        run.round += 1

        issues = self._engine.detect_issues(run.world_id)
        if not issues:
            run.status = RunStatus.CONVERGED
            run.open_questions = []
        elif run.round >= self._max_rounds:
            run.status = RunStatus.STOPPED
            run.open_questions = []
        else:
            run.open_questions = self._engine.generate_questions(issues)

        self._store.save(run)
        return change

    def revert(self, run_id: str, change_id: str) -> None:
        run = self._store.get(run_id)
        if run is None:
            raise LookupError(f"augmentation run not found: {run_id}")
        change = next((c for c in run.history if c.id == change_id), None)
        if change is None:
            raise LookupError(f"change not found: {change_id}")
        self._engine.revert(run.world_id, change)

    def get_run(self, run_id: str) -> AugmentationRun | None:
        return self._store.get(run_id)
