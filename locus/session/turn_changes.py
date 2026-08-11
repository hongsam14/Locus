"""Pure per-region turn-change shaping (X1, C6 / P-F4).

``shape_region_changes`` groups a turn's flat id lists into one ``RegionTurnChange``
per affected region (FR-UX2.6). Pure and side-effect-free so it is trivially
property-tested (nfr-light PBT). Regions with no change are omitted (BR-X1-21).

Note: rumor→region *feedback* moves distortion but is not a distinct field on
``RegionTurnChange`` (the model carries rumor/event state changes only); a region
whose sole change this turn is feedback produces no notification, by design of
the six-list model (BR-X1-19/21).
"""

from __future__ import annotations

from .models import RegionTurnChange


def shape_region_changes(
    *,
    promoted: list[str],
    demoted: list[str],
    pruned: list[str],
    applied_events: list[str],
    resolved_events: list[str],
    added_by_region: dict[str, list[str]],
    rumor_region: dict[str, str],
    event_region: dict[str, str],
) -> list[RegionTurnChange]:
    """Group flat turn deltas into per-region change summaries.

    ``rumor_region`` maps rumor id -> region id; ``event_region`` maps event id ->
    region id. Ids without a known region are skipped (defensive). Order of
    regions follows first appearance for stable output.
    """
    buckets: dict[str, RegionTurnChange] = {}
    order: list[str] = []

    def bucket(region_id: str) -> RegionTurnChange:
        rc = buckets.get(region_id)
        if rc is None:
            rc = RegionTurnChange(region_id=region_id)
            buckets[region_id] = rc
            order.append(region_id)
        return rc

    for rid in promoted:
        region = rumor_region.get(rid)
        if region is not None:
            bucket(region).promoted.append(rid)
    for rid in demoted:
        region = rumor_region.get(rid)
        if region is not None:
            bucket(region).demoted.append(rid)
    for rid in pruned:
        region = rumor_region.get(rid)
        if region is not None:
            bucket(region).pruned.append(rid)
    for eid in applied_events:
        region = event_region.get(eid)
        if region is not None:
            bucket(region).events_applied.append(eid)
    for eid in resolved_events:
        region = event_region.get(eid)
        if region is not None:
            bucket(region).events_resolved.append(eid)
    for region_id, ids in added_by_region.items():
        if ids:
            bucket(region_id).rumors_added.extend(ids)

    # BR-X1-21: only regions that actually changed (all lists non-empty guard is
    # implicit — a bucket exists only if something was appended).
    return [buckets[r] for r in order]
