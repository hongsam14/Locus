"""RumorFeedbackService — rumor→region distortion feedback (U-H1, FR-H3).

The deferred Phase 3 feedback loop: high-support rumor density in a region feeds
back into that region's distortion each turn, so strong rumors keep a region
dynamic even without events. Pure aggregation lives in
``rumor_dynamics.region_feedback`` (BR-H1-9); this service owns only the
side effect — reading/writing session ``region_distortions`` (SRP, AD-H Q4=B).
Canonical layer is never touched (NFR-H2).
"""

from __future__ import annotations

from locus.play.models import DEFAULT_DISTORTION_DEGREE, GameSession, SessionRumor
from locus.play.ports import DistortionStore
from locus.play.rumor import dynamics as rumor_dynamics
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS
from locus.shared.config.tuning import PlayTuning
from locus.shared.models.util import clamp01


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
    ) -> dict[str, float]:
        """Feed high-support rumor density back into region distortion (BR-H1-9/10).

        Computes per-region deltas from the ACTIVE rumors (pure), adds each to the
        region's current distortion (clamped), and returns the delta map — its keys
        are the regions the turn should treat as reinforced (BR-H1-2).

        ``store`` (U4, BR-U4-14): inside a turn's unit of work the caller passes the
        UoW's ``DistortionStore`` so the write joins that transaction; the default
        keeps the repository (manual / legacy paths).
        """
        target = store if store is not None else self._repo
        deltas = rumor_dynamics.region_feedback(
            active_rumors,
            weight=self._params.feedback_weight,
            high_support_threshold=self._params.high_support_threshold,
        )
        for region_id, delta in deltas.items():
            current = target.get_region_distortion(session.id, region_id)
            if current is None:
                current = DEFAULT_DISTORTION_DEGREE
            target.set_region_distortion(session.id, region_id, clamp01(current + delta))
        return deltas
