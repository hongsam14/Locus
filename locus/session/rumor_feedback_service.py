"""RumorFeedbackService — rumor→region distortion feedback (U-H1, FR-H3).

The deferred Phase 3 feedback loop: high-support rumor density in a region feeds
back into that region's distortion each turn, so strong rumors keep a region
dynamic even without events. Pure aggregation lives in
``rumor_dynamics.region_feedback`` (BR-H1-9); this service owns only the
side effect — reading/writing session ``region_distortions`` (SRP, AD-H Q4=B).
Canonical layer is never touched (NFR-H2).
"""

from __future__ import annotations

from . import rumor_dynamics
from .base import SessionAppService, clamp
from .models import DEFAULT_DISTORTION_DEGREE, GameSession, SessionRumor
from .repository import SessionRepository
from .rumor_dynamics import DEFAULT_RUMOR_DYNAMICS, RumorDynamicsParams


class RumorFeedbackService(SessionAppService):
    """Apply rumor→region distortion feedback for one turn."""

    def __init__(
        self,
        repo: SessionRepository,
        params: RumorDynamicsParams = DEFAULT_RUMOR_DYNAMICS,
    ) -> None:
        super().__init__(repo)
        self._params = params

    def apply_feedback(
        self, session: GameSession, active_rumors: list[SessionRumor]
    ) -> dict[str, float]:
        """Feed high-support rumor density back into region distortion (BR-H1-9/10).

        Computes per-region deltas from the ACTIVE rumors (pure), adds each to the
        region's current distortion (clamped), and returns the delta map — its keys
        are the regions the turn should treat as reinforced (BR-H1-2).
        """
        deltas = rumor_dynamics.region_feedback(
            active_rumors,
            weight=self._params.feedback_weight,
            high_support_threshold=self._params.high_support_threshold,
        )
        for region_id, delta in deltas.items():
            current = self._repo.get_region_distortion(session.id, region_id)
            if current is None:
                current = DEFAULT_DISTORTION_DEGREE
            self._repo.set_region_distortion(session.id, region_id, clamp(current + delta))
        return deltas
