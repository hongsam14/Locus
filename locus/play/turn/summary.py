"""Pure turn-summary helpers for the player perspective (U4; BLM §4.5, BR-U4-23/24).

``merge_changes`` folds several turns' per-region changes into one list;
``scope_changes`` keeps the player's region and its direct neighbours (all
regions for a player-less GM session, FD R-02); ``narrate`` renders one
deterministic sentence per region (no LLM).
"""

from __future__ import annotations

from locus.play.models import RegionTurnChange, TurnResult
from locus.play.player.movement import neighbours
from locus.shared.models import WorldSnapshot

_LISTS = ("promoted", "demoted", "pruned", "events_applied", "events_resolved", "rumors_added")


def merge_changes(results: list[TurnResult]) -> list[RegionTurnChange]:
    """Per-region union over turns (ids de-duplicated, first-appearance order)."""
    merged: dict[str, RegionTurnChange] = {}
    order: list[str] = []
    for res in results:
        for rc in res.region_changes:
            cur = merged.get(rc.region_id)
            if cur is None:
                cur = RegionTurnChange(region_id=rc.region_id, region_name=rc.region_name)
                merged[rc.region_id] = cur
                order.append(rc.region_id)
            if not cur.region_name and rc.region_name:
                cur.region_name = rc.region_name
            for name in _LISTS:
                have: list[str] = getattr(cur, name)
                for rid in getattr(rc, name):
                    if rid not in have:
                        have.append(rid)
    return [merged[r] for r in order]


def scope_changes(
    changes: list[RegionTurnChange], snapshot: WorldSnapshot, player_region_id: str | None
) -> list[RegionTurnChange]:
    """Player perspective (Q5=A): current region + direct neighbours, passable or
    not. ``None`` (GM session without a player) keeps everything (BR-U4-23)."""
    if player_region_id is None:
        return list(changes)
    keep = {player_region_id} | neighbours(snapshot, player_region_id)
    return [rc for rc in changes if rc.region_id in keep]


def narrate(changes: list[RegionTurnChange]) -> list[str]:
    """One sentence per region, deterministic (BR-U4-24)."""
    out: list[str] = []
    for rc in changes:
        parts: list[str] = []
        if rc.rumors_added:
            parts.append(
                f"{len(rc.rumors_added)} new rumor{'s' if len(rc.rumors_added) != 1 else ''}"
            )
        if rc.promoted:
            parts.append(f"{len(rc.promoted)} promoted")
        if rc.demoted:
            parts.append(f"{len(rc.demoted)} demoted")
        if rc.pruned:
            parts.append(f"{len(rc.pruned)} faded")
        if rc.events_applied:
            parts.append(
                "event applied"
                if len(rc.events_applied) == 1
                else f"{len(rc.events_applied)} events applied"
            )
        if rc.events_resolved:
            parts.append(
                "event resolved"
                if len(rc.events_resolved) == 1
                else f"{len(rc.events_resolved)} events resolved"
            )
        name = rc.region_name or rc.region_id
        out.append(f"{name}: {', '.join(parts) if parts else 'quiet'}")
    return out
