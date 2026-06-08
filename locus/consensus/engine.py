"""Consensus computation (U5, FR-D) — hybrid: static direct + query-time propagation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from ..models import (
    ConnectionEdge,
    ConsensusView,
    Knowledge,
    KnowledgeGraph,
    KnowledgeView,
    Region,
    RegionTopology,
    ScopeLink,
    ScopeType,
)
from .propagation import best_path_weights


@dataclass(frozen=True)
class ConsensusParams:
    propagate_min: float = 0.5
    rumor_min: float = 0.15


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
    is_rumor: bool = False,
    distortion_degree: float | None = None,
) -> KnowledgeView:
    return KnowledgeView(
        knowledge_id=k.id,
        statement=k.statement,
        scope_type=scope_type.value,
        is_rumor=is_rumor,
        confidence=confidence,
        distortion_degree=distortion_degree,
        source=k.provenance.source,
        region_id=region_id,
    )


def compute_consensus(
    region_id: str,
    *,
    regions: list[Region],
    connections: list[ConnectionEdge],
    scopes: list[ScopeLink],
    knowledge_by_id: dict[str, Knowledge],
    params: ConsensusParams = DEFAULT_PARAMS,
) -> ConsensusView:
    """Pure consensus computation for one region (BR-U5-*)."""
    by_id = {r.id: r for r in regions}
    world_id = by_id[region_id].world_id if region_id in by_id else ""

    # region -> [(knowledge_id, confidence)] for DIRECT scopes
    region_direct: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for s in scopes:
        if str(s.scope_type) == ScopeType.DIRECT.value and not s.is_rumor:
            region_direct[s.region_id].append((s.knowledge_id, s.confidence))

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

    # 4. propagation (max-product reachability)
    pw = best_path_weights(region_id, connections)
    # best path weight per *knowledge* across origin regions
    for rid, weight in pw.items():
        if rid == region_id:
            continue
        for kid, _conf in region_direct.get(rid, []):
            k = knowledge_by_id.get(kid)
            if k is None or kid in assigned:
                continue
            eff = k.confidence * weight
            if weight >= params.propagate_min:
                assigned.add(kid)
                view.propagated.append(_view(k, ScopeType.PROPAGATED, eff, rid))
            elif weight >= params.rumor_min:
                assigned.add(kid)
                v = _view(
                    k,
                    ScopeType.PROPAGATED,
                    eff,
                    rid,
                    is_rumor=True,
                    distortion_degree=round(1.0 - weight, 6),
                )
                view.rumors.append(v)
            else:
                view.unknown_count += 1

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

    def resolve(self, region_id: str) -> ConsensusView:
        return compute_consensus(
            region_id,
            regions=self._topo.regions,
            connections=self._topo.connections,
            scopes=self._kg.scopes,
            knowledge_by_id=self._knowledge_by_id,
            params=self._params,
        )
