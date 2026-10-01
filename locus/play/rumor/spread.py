"""Deed-rumor spread planning — pure (U6 BLM §4.2; BR-U6-16..20; TP-U6-1/2).

A deed rumor moves **one hop per turn** from a region it already sits in to a passable
neighbour it has not reached. The reach weight is the approved BR-U6-17 definition:
``w(X) = best_path_weights(origin)[X]`` over passable connections read both ways (like
movement), and the recorded weight of a hop is ``w(X) × edge(X, Y)`` — never above
``best_path_weights(origin)[Y]``. Canonical rumors never spread: hearsay already carries
canonical knowledge between regions.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence

from locus.knowledge.propagation import best_path_weights
from locus.play.models import SessionRumor, SpreadTarget
from locus.play.player.movement import is_passable
from locus.shared.config.tuning import PlayTuning
from locus.shared.models import ConnectionEdge, WorldSnapshot
from locus.shared.models.util import clamp01


def is_session_origin(rumor: SessionRumor) -> bool:
    """Only rumors born from a player's deed spread (BR-U6-16)."""
    return rumor.origin_kind == "deed"


def passable_both_ways(snapshot: WorldSnapshot) -> list[ConnectionEdge]:
    """The connections a rumor may travel: passable, in both directions (movement reads
    connections as undirected; knowledge's ``best_path_weights`` follows direction)."""
    edges = [c for c in snapshot.topo.connections if is_passable(c)]
    reverse = [
        c.model_copy(
            update={"source_region_id": c.target_region_id, "target_region_id": c.source_region_id}
        )
        for c in edges
    ]
    return edges + reverse


def neighbour_map(edges: Sequence[ConnectionEdge]) -> dict[str, dict[str, float]]:
    """Every region's strongest connection to each neighbour, built once; a parallel
    road and river count once at the stronger weight, a self loop not at all (the one
    rule for the engine and the planner's own fallback, U7 review C3)."""
    out: dict[str, dict[str, float]] = {}
    for c in edges:
        if c.target_region_id != c.source_region_id:
            near = out.setdefault(c.source_region_id, {})
            near[c.target_region_id] = max(near.get(c.target_region_id, 0.0), c.weight)
    return out


def plan_spread(
    snapshot: WorldSnapshot,
    rumor: SessionRumor,
    *,
    origin_region_id: str,
    reached: Collection[str],
    tuning: PlayTuning,
    edges: Sequence[ConnectionEdge] | None = None,
    reach: Mapping[str, float] | None = None,
    neighbours: Mapping[str, Mapping[str, float]] | None = None,
) -> list[SpreadTarget]:
    """The hops ``rumor`` may take this turn, strongest first (ties by region id).

    ``reached`` is every region this rumor's version (its appraisal) has ever reached,
    inactive or pruned ones included (BR-U6-19). ``edges`` lets a caller compute the
    passable graph once per turn; ``reach`` (``best_path_weights`` from the origin) and
    ``neighbours`` (``neighbour_map(edges)``) let it reuse them across parents (U6
    review C4). Each must have been computed from the same ``edges``.
    """
    if not is_session_origin(rumor):
        return []
    graph = list(edges) if edges is not None else passable_both_ways(snapshot)
    if reach is None:
        reach = best_path_weights(origin_region_id, graph)
    here = rumor.region_id
    w_here = reach.get(here, 0.0)
    if w_here <= 0.0:
        return []
    # Below this a rumor would be pruned by the next turn's decay: spend no LLM call on it.
    floor = tuning.prune_floor + tuning.support_decay
    out: list[SpreadTarget] = []
    near = (neighbours if neighbours is not None else neighbour_map(graph)).get(here, {})
    for target, edge_w in near.items():
        if target in reached or target not in snapshot.regions_by_id:
            continue
        weight = w_here * edge_w
        if weight < tuning.spread_min_weight:
            continue
        support = clamp01(rumor.support * (0.5 + 0.5 * edge_w))
        if support < floor:
            continue
        out.append(
            SpreadTarget(
                region_id=target,
                from_region_id=here,
                weight=clamp01(weight),
                degree=clamp01(max(rumor.distortion_degree, 1.0 - weight)),
                support=support,
            )
        )
    return sorted(out, key=lambda t: (-t.weight, t.region_id))
