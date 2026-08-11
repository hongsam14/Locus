"""DistortionService — per-region distortion strength (FR-R2.5).

Owns the manual read/write of a session's per-region distortion. The dynamic,
event-driven evolution of these values happens in TurnAdvancer; this service is
the direct GameMaster set/inspect boundary.
"""

from __future__ import annotations

from .base import SessionAppService, clamp
from .models import RegionDistortion, TimelineKind


class DistortionService(SessionAppService):
    """Set and list per-region distortion degrees."""

    def list_distortions(self, session_id: str) -> list[RegionDistortion]:
        """Read-only list of per-region distortion (allowed on closed sessions)."""
        self._require_session(session_id)
        return self._repo.list_region_distortions(session_id)

    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        session = self._require_open(session_id)
        degree = clamp(degree)
        self._repo.set_region_distortion(session_id, region_id, degree)
        self._timeline(
            session,
            TimelineKind.SET_DISTORTION,
            f"distortion of {region_id} -> {degree:.2f}",
            {"region_id": region_id, "degree": degree},
        )
