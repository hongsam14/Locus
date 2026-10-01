"""AugmentationService — the Q&A loop over one kept run (U7 FR-F; U3 BLM §4.3, B2).

The screen keeps one run: an answer returns the run with its next questions and what
changed; changes are undone latest first; an ignored issue can be asked again. State
moves by the table of BLM §4.3 (〔Step 1.3 정정〕 rows for unignore): ignore counts as an
answer, undo and unignore do not. Requests on one run take turns under its lock.
"""

from __future__ import annotations

from locus.world.augmentation.detectors import select
from locus.world.augmentation.engine import AugmentationEngine
from locus.world.augmentation.run_store import InMemoryRunStore, RunState, RunStore
from locus.world.augmentation.types import (
    AnswerAction,
    AnswerResult,
    AugmentationAnswer,
    AugmentationRun,
    ChangeAlreadyRevertedError,
    QuestionTarget,
    RevertOrderError,
    RunFinishedError,
    RunStatus,
)

MAX_ANSWERS = 30  # answers per run (BR-U3-28; was 5 rounds)
LLM_BUDGET = 60  # LLM calls per run (NFR R-03: first detection 25 + ~1 per answer x 30)


class AugmentationService:
    def __init__(
        self,
        engine: AugmentationEngine,
        store: RunStore | None = None,
        *,
        max_answers: int = MAX_ANSWERS,
        llm_budget: int = LLM_BUDGET,
    ) -> None:
        self._engine = engine
        self._store = store or InMemoryRunStore()
        self._max_answers = max_answers
        self._budget = llm_budget

    def start_run(self, world_id: str) -> AugmentationRun:
        state = RunState(run=AugmentationRun(world_id=world_id))
        self._refresh(state)  # an unknown world raises LookupError (404)
        self._store.save(state)
        return state.run

    def get_run(self, run_id: str) -> AugmentationRun | None:
        state = self._store.get(run_id)
        return state.run if state else None

    def answer(self, run_id: str, answer: AugmentationAnswer) -> AnswerResult:
        state = self._state(run_id)
        with state.lock:
            run = state.run
            if run.status != RunStatus.OPEN:
                raise RunFinishedError("this run is finished; start a new one")
            question = next((q for q in run.open_questions if q.id == answer.question_id), None)
            if question is None:
                raise LookupError(f"question not found in this run: {answer.question_id}")
            issue = next((i for i in run.issues if i.id == question.issue_id), None)
            if issue is None:
                raise LookupError(f"issue not found in this run: {question.issue_id}")
            change = self._engine.apply(run.world_id, issue, question, answer)
            if AnswerAction(answer.action) == AnswerAction.IGNORE:
                run.ignored_keys.append(issue.key)
            run.answers += 1
            changed: list[QuestionTarget] = []
            if change is not None:
                run.history.append(change)
                changed = [question.target] if question.target else []
                titles = {  # the stored title, the server's fallback included (U3 review C2)
                    n.id: str(n.properties.get("title") or n.id) for n in change.nodes_after
                }
                changed += [
                    QuestionTarget(kind="knowledge", id=nid, name=titles.get(nid, nid))
                    for nid in change.added_ids
                ]
            self._refresh_or_clear(state)
            return AnswerResult(change=change, run=run, changed=changed)

    def revert(self, run_id: str, change_id: str) -> AugmentationRun:
        """Undo one change. 404 unknown -> 409 already undone -> 409 not the latest ->
        409 edited outside the run (〔Step 1.3 정정〕, FD 검토 R-08)."""
        state = self._state(run_id)
        with state.lock:
            run = state.run
            change = next((c for c in run.history if c.id == change_id), None)
            if change is None:
                raise LookupError(f"change not found: {change_id}")
            if change.reverted:
                raise ChangeAlreadyRevertedError("this change was already reverted")
            latest = next(c for c in reversed(run.history) if not c.reverted)
            if latest.id != change.id:
                raise RevertOrderError("revert the later changes first")
            self._engine.revert(run.world_id, change)
            change.reverted = True
            self._refresh_or_clear(state)
            return run

    def unignore(self, run_id: str, issue_key: str) -> AugmentationRun:
        state = self._state(run_id)
        with state.lock:
            run = state.run
            if run.status == RunStatus.STOPPED:
                raise RunFinishedError("this run is finished; start a new one")
            if issue_key not in run.ignored_keys:
                raise LookupError(f"not an ignored issue: {issue_key}")
            run.ignored_keys.remove(issue_key)
            self._refresh(state)
            return run

    # ------------------------------------------------------------------ #
    def _state(self, run_id: str) -> RunState:
        state = self._store.get(run_id)
        if state is None:
            raise LookupError(f"augmentation run not found: {run_id}")
        return state

    def _refresh_or_clear(self, state: RunState) -> None:
        """Detect again after a write; when that fails, drop the questions so the same
        answer cannot be applied twice — the screen reads the run again (U3 review S15)."""
        try:
            self._refresh(state)
        except Exception:
            state.run.open_questions = []
            state.run.issues = []
            raise

    def _refresh(self, state: RunState) -> None:
        """Detect again and set the questions and the status (BLM §4.3)."""
        run = state.run

        def take() -> bool:
            if run.llm_calls >= self._budget:
                run.llm_budget_exhausted = True
                return False
            run.llm_calls += 1
            return True

        found, snapshot = self._engine.detect(run.world_id, state, take)
        run.issues = select(found, run.ignored_keys)
        if not run.issues:
            run.status, run.open_questions = RunStatus.CONVERGED, []
        elif run.answers >= self._max_answers:
            run.status, run.open_questions = RunStatus.STOPPED, []
        else:
            run.status = RunStatus.OPEN
            run.open_questions = self._engine.questions(run.issues, snapshot, state, take)
