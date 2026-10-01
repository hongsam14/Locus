"""DistortionService — per-region distortion strength (FR-R2.5).

Owns the manual read/write of a session's per-region distortion. The dynamic,
event-driven evolution of these values happens in TurnAdvancer; this service is
the direct GameMaster set/inspect boundary.

U7: it reads the world (FD review R-01) — the list has one row per current world
region (a region added after the session started shows the default, BR-U7-18), a set
on a region the world does not have is 404 (BR-U7-6), and a set clears the feedback
share, the GM's value being the region's new base (BR-U7-5).
"""

from __future__ import annotations

from locus.knowledge.cache import SnapshotSource
from locus.play.base import SessionAppService, require_region
from locus.play.models import DEFAULT_DISTORTION_DEGREE, RegionDistortion, TimelineKind
from locus.play.ports import PlayRepository
from locus.shared.models.util import clamp01


class DistortionService(SessionAppService):
    """Set and list per-region distortion degrees."""

    def __init__(self, repo: PlayRepository, snapshots: SnapshotSource) -> None:
        super().__init__(repo)
        self._snapshots = snapshots

    def list_distortions(self, session_id: str) -> list[RegionDistortion]:
        """One row per current world region, the stored one or the default; nothing is
        written (BR-U4-4). Rows of regions the world no longer has are left out (they stay
        stored). Read-only, so closed sessions are allowed."""
        session = self._require_session(session_id)
        stored = {rd.region_id: rd for rd in self._repo.list_region_distortions(session_id)}
        return [
            stored.get(region.id)
            or RegionDistortion(
                session_id=session_id,
                region_id=region.id,
                distortion_degree=DEFAULT_DISTORTION_DEGREE,
            )
            for region in self._snapshots.get(session.world_id).topo.regions
        ]

    def set_region_distortion(self, session_id: str, region_id: str, degree: float) -> None:
        """The GM's value is the region's new base: the feedback share is cleared and
        what was cleared is recorded (U7 BR-U7-5). 404 for a region not in the world."""
        session = self._require_open(session_id)
        require_region(self._snapshots, session.world_id, region_id)
        name = self._snapshots.get(session.world_id).regions_by_id[region_id].name
        degree = clamp01(degree)
        cleared = next(
            (
                row.feedback_share
                for row in self._repo.list_region_distortions(session_id)
                if row.region_id == region_id
            ),
            0.0,
        )
        self._repo.set_region_distortion(session_id, region_id, degree, feedback_share=0.0)
        self._timeline(
            session,
            TimelineKind.SET_DISTORTION,
            f"distortion of {name} -> {degree:.2f}",
            {
                "region_id": region_id,
                "region_name": name,
                "degree": degree,
                "feedback_share_cleared": cleared,
            },
        )
