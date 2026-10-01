"""World state for the GM map overlay (U7, FR-D4, US-5.5).

``summarize_state`` is the pure aggregation; ``WorldStateService`` (Step 6) feeds it.
Nothing here is stored: the overlay is read whenever the GM looks (domain-entities §4).
"""

from __future__ import annotations

from collections.abc import Sequence

from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    EventStatus,
    RegionDistortion,
    RegionState,
    SessionEvent,
    SessionRumor,
)
from locus.shared.models import Region


def summarize_state(
    regions: Sequence[Region],
    distortions: Sequence[RegionDistortion],
    rumors: Sequence[SessionRumor],
    events: Sequence[SessionEvent],
) -> list[RegionState]:
    """One row per world region, in the given order (TP-U7-7). A region without a stored
    distortion row shows the default (BR-U7-18); rumors and events of regions no longer
    in the world are left out. ``rumors`` are the session's ACTIVE rumors."""
    stored = {d.region_id: d for d in distortions}
    active: dict[str, int] = {}
    promoted: dict[str, int] = {}
    deed: dict[str, int] = {}
    for r in rumors:
        if not r.active:
            continue
        active[r.region_id] = active.get(r.region_id, 0) + 1
        if r.promoted:
            promoted[r.region_id] = promoted.get(r.region_id, 0) + 1
        if r.origin_kind != "canonical":
            deed[r.region_id] = deed.get(r.region_id, 0) + 1
    running: dict[str, int] = {}
    for ev in events:
        if str(ev.status) == EventStatus.ACTIVE.value:
            running[ev.region_id] = running.get(ev.region_id, 0) + 1
    out: list[RegionState] = []
    for region in regions:
        row = stored.get(region.id)
        out.append(
            RegionState(
                region_id=region.id,
                region_name=region.name,
                distortion=row.distortion_degree if row else DEFAULT_DISTORTION_DEGREE,
                feedback_share=row.feedback_share if row else 0.0,
                active_rumors=active.get(region.id, 0),
                promoted_rumors=promoted.get(region.id, 0),
                deed_rumors=deed.get(region.id, 0),
                active_events=running.get(region.id, 0),
            )
        )
    return out
