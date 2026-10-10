"""Carry a world's NPCs and event seeds across a rebuild (V7, FR-C9, RE-W18, Q3=A). Pure.

A build makes regions, connections and knowledge from the sources; NPCs and event seeds
are added in the editor, so a rebuild from the same sources would lose them. Each one
goes to the new region with the same (normalized name, level) as its old region; two
such regions are told apart once by their parents' keys. What cannot be placed is not
carried and is reported, one warning each (it stays in the pre-replace backup).
Ids stay, so their translations stay too (V3 keeps the translations of ids still there).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from locus.knowledge.loader import NPC_HOME_DANGLING, SEED_REGION_DANGLING
from locus.shared.models import NPC, BuildWarning, EventSeed, Region, WorldSnapshot

STAGE = "carry-over"

RegionKey = tuple[str, str]


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

    def parent_key(region: Region, by_id: dict[str, Region]) -> RegionKey | None:
        parent = by_id.get(region.parent_id) if region.parent_id else None
        return region_key(parent.name, parent.level) if parent is not None else None

    def place(region_id: str) -> tuple[Region | None, str]:
        """The new region for an old region id, or why there is none."""
        r = old_by_id.get(region_id)
        if r is None:
            return None, f"its region {region_id} is not in the old world"
        where = f"{r.name} ({r.level})"
        found = new_by_key.get(region_key(r.name, r.level), [])
        if len(found) > 1:  # once more by the parents' keys
            want = parent_key(r, old_by_id)
            found = [c for c in found if parent_key(c, new_by_id) == want] or found
            if len(found) > 1:
                return None, f"{len(found)} regions named {where}"
        if not found:
            return None, f"no region named {where} in the new world"
        return found[0], ""

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
    # The loader already dropped NPCs and seeds whose region was gone (FD review R-10):
    # they are not in ``old``, but they are lost with the replace all the same.
    for w in old.load_warnings:
        if w.stage != "load" or not w.item_id:
            continue
        if w.message.startswith(NPC_HOME_DANGLING):
            out.warnings.append(_left(f"NPC {w.item_id}", w.item_id, _GONE))
        elif w.message.startswith(SEED_REGION_DANGLING):
            out.warnings.append(_left(f"Event seed {w.item_id}", w.item_id, _GONE))
    return out


_GONE = "its region is not in the old world"


def _left(what: str, item_id: str, why: str) -> BuildWarning:
    return BuildWarning(stage=STAGE, item_id=item_id, message=f"{what} was not carried over: {why}")
