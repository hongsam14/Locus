"""RumorFeedbackService — rumor→region distortion feedback (U-H1, FR-H3; U7 FR-E2).

Strong, not-yet-accepted rumors in a region feed back into its distortion each turn.
U7 (FD-U7 Q2=A, Q4=A): promoted rumors no longer count, the part of the distortion
feedback put there (``feedback_share``) is capped, and it is given back once the region
has no strong rumor — so a region does not only ever climb. The maths is pure
(``rumor_dynamics.region_feedback`` / ``step_feedback``); this service reads and writes
the session ``region_distortions`` (SRP, AD-H Q4=B). The canonical layer is never touched.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from locus.play.models import GameSession, SessionRumor
from locus.play.ports import DistortionStore
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS, FeedbackState
from locus.shared.config.tuning import PlayTuning


@dataclass(frozen=True)
class FeedbackOutcome:
    """One turn's feedback: what it raised, what it gave back, where strong rumors are."""

    raised: dict[str, float] = field(default_factory=dict)
    restored: dict[str, float] = field(default_factory=dict)
    strong_regions: frozenset[str] = frozenset()


class RumorFeedbackService:
    """Apply rumor→region distortion feedback for one turn.

    Needs only the ``DistortionStore`` port (interface segregation, AD-R3)."""

    def __init__(
        self,
        repo: DistortionStore,
        params: PlayTuning = DEFAULT_RUMOR_DYNAMICS,
    ) -> None:
        self._repo = repo
        self._params = params

    def apply_feedback(
        self,
        session: GameSession,
        active_rumors: list[SessionRumor],
        *,
        store: DistortionStore | None = None,
    ) -> FeedbackOutcome:
        """Raise regions with strong rumors (capped) and give back the share of regions
        without them (BLM §1.2). Only changed rows are written.

        ``store`` (U4, BR-U4-14): inside a turn's unit of work the caller passes the
        UoW's ``DistortionStore`` so the write joins that transaction.
        """
        target = store if store is not None else self._repo
        deltas = rumor_dynamics.region_feedback(
            active_rumors,
            weight=self._params.feedback_weight,
            high_support_threshold=self._params.high_support_threshold,
        )
        states = {
            row.region_id: FeedbackState(degree=row.distortion_degree, share=row.feedback_share)
            for row in target.list_region_distortions(session.id)
        }
        for rid in deltas:
            states.setdefault(rid, rumor_dynamics.FRESH)
        steps = rumor_dynamics.step_feedback(
            states,
            deltas,
            cap=self._params.feedback_cap,
            restore=self._params.feedback_restore,
        )
        raised: dict[str, float] = {}
        restored: dict[str, float] = {}
        for rid, step in steps.items():
            before = states[rid]
            if step.degree != before.degree or step.share != before.share:
                target.set_region_distortion(
                    session.id, rid, step.degree, feedback_share=step.share
                )
            if step.raised > 0:
                raised[rid] = step.raised
            if step.restored > 0 or step.share < before.share:
                restored[rid] = step.restored
        return FeedbackOutcome(raised=raised, restored=restored, strong_regions=frozenset(deltas))
