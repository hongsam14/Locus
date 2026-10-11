"""Consensus computation (U5, FR-D) — hybrid: static direct + query-time propagation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from locus.knowledge.propagation import best_path_weights
from locus.shared.config.tuning import KnowledgeTuning
from locus.shared.models import (
    ConnectionEdge,
    ConsensusView,
    Knowledge,
    KnowledgeGraph,
    KnowledgeView,
    Region,
    RegionTopology,
    ScopeLink,
    ScopeType,
    WorldSnapshot,
)


@dataclass(frozen=True)
class ConsensusParams:
    propagate_min: float = 0.5
    hearsay_min: float = 0.15

    @classmethod
    def from_tuning(cls, tuning: "KnowledgeTuning") -> "ConsensusParams":
        return cls(propagate_min=tuning.propagate_min, hearsay_min=tuning.hearsay_min)


DEFAULT_PARAMS = ConsensusParams()


def _ancestors(region_id: str, by_id: dict[str, Region]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    cur = by_id.get(region_id)
    while cur is not None and cur.parent_id and cur.parent_id not in seen:
        seen.add(cur.parent_id)
        out.append(cur.parent_id)
        cur = by_id.get(cur.parent_id)
    return out


def _view(
    k: Knowledge,
    scope_type: ScopeType,
    confidence: float,
    region_id: str | None,
    *,
    is_hearsay: bool = False,
    path_decay: float | None = None,
) -> KnowledgeView:
    return KnowledgeView(
        knowledge_id=k.id,
        statement=k.statement,
        title=k.title,  # RE A8 / BR-U2-19
        scope_type=scope_type.value,
        is_hearsay=is_hearsay,
        confidence=confidence,
        path_decay=path_decay,
        source=k.provenance.source,
        region_id=region_id,
    )


def best_origins(
    pw: dict[str, float],
    region_direct: dict[str, list[tuple[str, float]]],
    exclude: str,
) -> dict[str, tuple[str, float]]:
    """knowledge id -> (origin region, its path weight): the origin each knowledge is
    reached from most strongly; a tie goes to the smaller region id. Regions ``pw`` does
    not reach, and ``exclude`` (the region itself), are never origins. Independent of
    the order of either input (V7, BR-V7-01, PBT-V7-1/2)."""
    best: dict[str, tuple[str, float]] = {}
    for rid, weight in pw.items():
        if rid == exclude:
            continue
        for kid, _conf in region_direct.get(rid, []):
            cur = best.get(kid)
            if cur is None or _stronger(rid, weight, cur):
                best[kid] = (rid, weight)
    return best


def _stronger(rid: str, weight: float, cur: tuple[str, float]) -> bool:
    # Exact: ``best_path_weights`` gives the same bits whatever the connection order
    # (each path is multiplied from the start), and the band is judged on this same
    # weight. A rounded compare let a weaker origin win a "tie" (V7 code review #1).
    return weight > cur[1] or (weight == cur[1] and rid < cur[0])


def _confident_first(views: list[KnowledgeView]) -> list[KnowledgeView]:
    """Q1 = A: the most certain first, then by knowledge id (BR-V7-04). The NPC scope's
    ``pick_facts`` orders by the same exact confidence."""
    return sorted(views, key=lambda v: (-v.confidence, v.knowledge_id))


def compute_consensus(
    region_id: str,
    *,
    snapshot: WorldSnapshot | None = None,
    regions: list[Region] | None = None,
    connections: list[ConnectionEdge] | None = None,
    scopes: list[ScopeLink] | None = None,
    knowledge_by_id: dict[str, Knowledge] | None = None,
    params: ConsensusParams = DEFAULT_PARAMS,
) -> ConsensusView:
    """Pure consensus computation for one region (BR-U5-*).

    Pass a ``snapshot`` (U2 K5) or the four collections explicitly.
    """
    if snapshot is not None:
        regions = snapshot.topo.regions
        connections = snapshot.topo.connections
        scopes = snapshot.kg.scopes
        knowledge_by_id = {k.id: k for k in snapshot.kg.knowledge}
    regions = regions or []
    connections = connections or []
    scopes = scopes or []
    knowledge_by_id = knowledge_by_id or {}
    by_id = {r.id: r for r in regions}
    world_id = by_id[region_id].world_id if region_id in by_id else ""

    # region -> [(knowledge_id, confidence)] for DIRECT scopes; one (region, knowledge)
    # scoped twice keeps its highest confidence, whatever order the scopes come in (R-07)
    strongest: dict[str, dict[str, float]] = defaultdict(dict)
    for s in scopes:
        if str(s.scope_type) == ScopeType.DIRECT.value and not s.is_rumor:
            held = strongest[s.region_id]
            held[s.knowledge_id] = max(s.confidence, held.get(s.knowledge_id, s.confidence))
    region_direct: dict[str, list[tuple[str, float]]] = {
        rid: sorted(held.items()) for rid, held in strongest.items()
    }

    assigned: set[str] = set()
    view = ConsensusView(world_id=world_id, region_id=region_id)

    # 1. direct
    for kid, conf in region_direct.get(region_id, []):
        k = knowledge_by_id.get(kid)
        if k and kid not in assigned:
            assigned.add(kid)
            view.direct.append(_view(k, ScopeType.DIRECT, conf, region_id))

    # 2. inherited (ancestors' direct)
    for anc in _ancestors(region_id, by_id):
        for kid, conf in region_direct.get(anc, []):
            k = knowledge_by_id.get(kid)
            if k and kid not in assigned:
                assigned.add(kid)
                view.inherited.append(_view(k, ScopeType.INHERITED, conf, anc))

    # 3. global
    for kid, k in knowledge_by_id.items():
        if k.is_global and kid not in assigned:
            assigned.add(kid)
            view.global_knowledge.append(_view(k, ScopeType.GLOBAL, k.confidence, None))

    # 4. propagation (max-product reachability): each knowledge from its strongest
    # origin, counted once (V7, BR-V7-01/03)
    pw = best_path_weights(region_id, connections)
    origins = best_origins(pw, region_direct, exclude=region_id)
    for kid in sorted(origins):
        rid, weight = origins[kid]
        k = knowledge_by_id.get(kid)
        if k is None or kid in assigned:
            continue
        eff = k.confidence * weight
        if weight >= params.propagate_min:
            assigned.add(kid)
            view.propagated.append(_view(k, ScopeType.PROPAGATED, eff, rid))
        elif weight >= params.hearsay_min:
            assigned.add(kid)
            v = _view(
                k,
                ScopeType.HEARSAY,
                eff,
                rid,
                is_hearsay=True,
                path_decay=round(1.0 - weight, 6),
            )
            view.hearsay.append(v)
        else:
            view.unknown_count += 1

    # 5. each list confident first; the order between the lists stays (Q1 = A)
    view.direct = _confident_first(view.direct)
    view.inherited = _confident_first(view.inherited)
    view.global_knowledge = _confident_first(view.global_knowledge)
    view.propagated = _confident_first(view.propagated)
    view.hearsay = _confident_first(view.hearsay)
    return view


class ConsensusEngine:
    """Resolve consensus over an in-memory KnowledgeGraph + RegionTopology."""

    def __init__(
        self,
        knowledge_graph: KnowledgeGraph,
        topology: RegionTopology,
        params: ConsensusParams = DEFAULT_PARAMS,
    ) -> None:
        self._kg = knowledge_graph
        self._topo = topology
        self._params = params
        self._knowledge_by_id = {k.id: k for k in knowledge_graph.knowledge}

    @classmethod
    def from_snapshot(
        cls, snapshot: WorldSnapshot, params: ConsensusParams = DEFAULT_PARAMS
    ) -> "ConsensusEngine":
        return cls(snapshot.kg, snapshot.topo, params)

    def resolve(self, region_id: str) -> ConsensusView:
        return compute_consensus(
            region_id,
            regions=self._topo.regions,
            connections=self._topo.connections,
            scopes=self._kg.scopes,
            knowledge_by_id=self._knowledge_by_id,
            params=self._params,
        )
