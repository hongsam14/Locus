"""Carry a world's NPCs and event seeds across a rebuild (V7, FR-C9, RE-W18, Q3=A). Pure.

A build makes regions, connections and knowledge from the sources; NPCs and event seeds
are added in the editor, so a rebuild from the same sources would lose them. Each one
goes to the new region with the same (normalized name, level) as its old region. When
that key is not unique — in the new world, or already in the old one — the parents'
keys must match too (code review #11). What cannot be placed is not carried and is
reported, one warning each; it is in the pre-replace backup. What the load already
dropped (its region gone, or the node unreadable) is reported too, and is in no backup:
the backup is exported through the same load (code review #2).
Ids stay, so their translations stay too (V3 keeps the translations of ids still there).
"""

from __future__ import annotations

import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from locus.knowledge.loader import NPC_HOME_DANGLING, NPC_LABEL, SEED_LABEL, SEED_REGION_DANGLING
from locus.shared.models import NPC, BuildWarning, EventSeed, Region, WorldSnapshot

STAGE = "carry-over"

RegionKey = tuple[str, str]

_GONE = "its region is not in the old world"
_UNREAD = "it could not be read from the old world"


@dataclass(frozen=True)
class CarryOver:
    npcs: list[NPC] = field(default_factory=list)  # home_region_id now a new region's id
    seeds: list[EventSeed] = field(default_factory=list)  # region_id now a new region's id
    warnings: list[BuildWarning] = field(default_factory=list)  # one per item left behind


def region_key(name: str, level: str) -> RegionKey:
    """(name, level) as a match sees it: NFKC, case-folded, whitespace collapsed."""
    text = unicodedata.normalize("NFKC", name).casefold()
    return " ".join(text.split()), str(level)


def carry_over(old: WorldSnapshot, new_regions: list[Region], world_id: str) -> CarryOver:
    new_by_id = {r.id: r for r in new_regions}
    new_by_key: dict[RegionKey, list[Region]] = {}
    for r in new_regions:
        new_by_key.setdefault(region_key(r.name, r.level), []).append(r)
    old_by_id = old.regions_by_id
    old_count = Counter(region_key(r.name, r.level) for r in old.topo.regions)

    def parent_key(region: Region, by_id: dict[str, Region]) -> RegionKey | None:
        parent = by_id.get(region.parent_id) if region.parent_id else None
        return region_key(parent.name, parent.level) if parent is not None else None

    def place(region_id: str) -> tuple[Region | None, str]:
        """The new region for an old region id, or why there is none."""
        r = old_by_id.get(region_id)
        if r is None:
            return None, f"its region {region_id} is not in the old world"
        key = region_key(r.name, r.level)
        where = f"{r.name} ({r.level})"
        found = new_by_key.get(key, [])
        if not found:
            return None, f"no region named {where} in the new world"
        if len(found) == 1 and old_count[key] == 1:
            return found[0], ""
        want = parent_key(r, old_by_id)
        matched = [c for c in found if parent_key(c, new_by_id) == want]
        if len(matched) == 1:
            return matched[0], ""
        if len(matched) > 1 or len(found) > 1:
            return None, f"{len(matched) or len(found)} regions named {where}"
        return None, f"no region named {where} under its old parent in the new world"

    out = CarryOver()
    for npc in old.npcs:
        home, why = place(npc.home_region_id)
        if home is None:
            out.warnings.append(_left(f"NPC {npc.name}", npc.id, why))
        else:
            out.npcs.append(
                npc.model_copy(update={"home_region_id": home.id, "world_id": world_id})
            )
    for seed in old.event_seeds:
        region, why = place(seed.region_id)
        if region is None:
            out.warnings.append(_left(f"Event seed {seed.title}", seed.id, why))
        else:
            out.seeds.append(seed.model_copy(update={"region_id": region.id, "world_id": world_id}))
    for w in old.load_warnings:  # dropped by the load: not in ``old``, lost all the same
        if w.stage != "load" or not w.item_id:
            continue
        for label, what, gone in (
            (SEED_LABEL, "Event seed", SEED_REGION_DANGLING),
            (NPC_LABEL, "NPC", NPC_HOME_DANGLING),
        ):
            if w.message.startswith(label):
                why = _GONE if w.message.startswith(gone) else _UNREAD
                out.warnings.append(_left(f"{what} {w.item_id}", w.item_id, why))
                break
    return out


def _left(what: str, item_id: str, why: str) -> BuildWarning:
    return BuildWarning(stage=STAGE, item_id=item_id, message=f"{what} was not carried over: {why}")
