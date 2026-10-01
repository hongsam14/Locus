"""Pure movement rules (U4, FD business-logic-model §2; BR-U4-6..10).

Everything here is a pure function over the canonical snapshot: passability,
turn cost of a connection, the move options from a region, its neighbours, and
the authoritative validation of a player action. Property-tested (TP-U4-1/2).
"""

from __future__ import annotations

import math

from locus.play.errors import InvalidActionError
from locus.play.models import EndTalkAction, MoveAction, MoveOption, Player, PlayerAction
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import NPC, ConnectionEdge, ConnectionKind, WorldSnapshot


def is_passable(edge: ConnectionEdge) -> bool:
    """``blocked`` connections and zero-weight connections cannot be crossed (BR-U4-7)."""
    return str(edge.kind) != ConnectionKind.BLOCKED.value and edge.weight > 0.0


def move_cost(edge: ConnectionEdge, tuning: PlayTuning) -> int:
    """Turns a move over ``edge`` costs: ``clamp(ceil(1 / weight), 1, max_move_cost)``
    (BR-U4-8; Q1=A). 0 when the edge is not passable."""
    if not is_passable(edge):
        return 0
    cap = max(1, tuning.max_move_cost)
    if edge.weight * cap <= 1.0:  # 1 / weight >= cap (also guards subnormal weights, PBT catch)
        return cap
    return max(1, math.ceil(1.0 / edge.weight))


def _other_end(edge: ConnectionEdge, region_id: str) -> str | None:
    """The far end of ``edge`` seen from ``region_id``, or None if it does not touch it.

    Connections are read as **undirected**: only ``TopologyBuilder`` happens to emit
    both directions, and nothing on the import path enforces symmetry, so a
    hand-authored World File produced one-way doors that stranded the player and
    silently dropped the neighbour's turn notifications (code review U4-2 #12).
    """
    if edge.source_region_id == region_id:
        return edge.target_region_id
    if edge.target_region_id == region_id:
        return edge.source_region_id
    return None


def npcs_here(snapshot: WorldSnapshot, region_id: str) -> list[NPC]:
    """The NPCs living in ``region_id`` (one rule for every caller, U5 review C4)."""
    return list(snapshot.npcs_by_region.get(region_id, []))


def find_npc(snapshot: WorldSnapshot, npc_id: str) -> NPC | None:
    """The NPC anywhere in this world, or None. Callers keep their own status codes:
    dialogue answers 404 for an unknown NPC, an action answers 400 (BR-U5-28)."""
    return next((n for n in snapshot.npcs if n.id == npc_id), None)


def neighbours(snapshot: WorldSnapshot, region_id: str) -> set[str]:
    """Regions directly connected to ``region_id`` (passable or not; Q5 scope)."""
    out: set[str] = set()
    for c in snapshot.topo.connections:
        other = _other_end(c, region_id)
        if other is not None and other != region_id and other in snapshot.regions_by_id:
            out.add(other)
    return out


def move_options(
    snapshot: WorldSnapshot, from_region_id: str, tuning: PlayTuning
) -> list[MoveOption]:
    """One option per neighbour; with several connections to the same neighbour the
    passable one with the lowest cost wins (BR-U4-9). Sorted: passable first, then
    cost, then name."""
    options: dict[str, MoveOption] = {}
    for c in snapshot.topo.connections:
        other = _other_end(c, from_region_id)
        if other is None or other == from_region_id:
            continue
        target = snapshot.regions_by_id.get(other)
        if target is None:
            continue  # dangling connection: not offered
        passable = is_passable(c)
        opt = MoveOption(
            region_id=other,
            region_name=target.name,
            kind=str(c.kind),
            weight=c.weight,
            cost_turns=move_cost(c, tuning),
            passable=passable,
            reason=None if passable else "blocked pass",
        )
        prev = options.get(opt.region_id)
        if prev is None or (
            opt.passable and (not prev.passable or opt.cost_turns < prev.cost_turns)
        ):
            options[opt.region_id] = opt
    return sorted(options.values(), key=lambda o: (not o.passable, o.cost_turns, o.region_name))


def validate_action(
    snapshot: WorldSnapshot, player: Player, action: PlayerAction, tuning: PlayTuning
) -> MoveOption | None:
    """Authoritative check of ``action`` against the player's *current* position
    (called under the turn guard, FD R-10). Returns the chosen ``MoveOption`` for a
    move, ``None`` otherwise. Raises ``InvalidActionError`` (400)."""
    if player.region_id not in snapshot.regions_by_id:
        raise LookupError(f"player region no longer exists: {player.region_id}")
    if isinstance(action, MoveAction):
        for opt in move_options(snapshot, player.region_id, tuning):
            if opt.region_id == action.to_region_id:
                if not opt.passable:
                    raise InvalidActionError(f"blocked pass: {action.to_region_id}")
                return opt
        raise InvalidActionError(f"not connected: {action.to_region_id}")
    if isinstance(action, EndTalkAction):
        here = {n.id for n in npcs_here(snapshot, player.region_id)}
        if action.npc_id not in here:
            raise InvalidActionError(f"npc not here: {action.npc_id}")
    return None


def action_cost(action: PlayerAction | None, option: MoveOption | None) -> int:
    """Turns an action spends: a move costs its option's turns; wait / end_talk /
    GM manual turn (``None``) cost one (BR-U4-11)."""
    if isinstance(action, MoveAction) and option is not None:
        return max(1, option.cost_turns)
    return 1
